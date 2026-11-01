#!/usr/bin/env python3
"""CASE 02: the viral "liquidity sweep" scalping strategy (previous-day high/low), tested on 1-minute data.

The rules (see PROTOCOL.md, written before any result):
  1. Mark yesterday's high (PDH) and low (PDL).
  2. 1-minute chart. Price crosses above PDH -> wait for a red candle -> short when a later candle breaks its low.
     Price crosses below PDL -> wait for a green candle -> long when a later candle breaks its high.
  3. Stop-loss behind that candle. Book 75% at 1R, move the stop to cost, let 25% run to 10R.
  4. Max 3 entries a day, stop after 2 full stop-losses; only fresh sweeps.

Usage:
  python cases/02-sweep-scalping/strategy.py --data path/to/minute_bars [--out DIR] [--universe index|stocks|all]
  (folder of SYMBOL.csv / .csv.gz / .parquet files; see backtested/data.py for the format)
  Files named NIFTY / NIFTY50 (or anything passed to --index) are the index; every other file is a stock.

Outputs in --out: cells.csv (all pre-registered cells, + target-first sensitivity rows "TF"), and for the canonical
NIFTY cell: summary.json, by_year.csv, path_rs.csv (₹ at a fixed ₹1,000 risk a trade).

Implementation details where the protocol is silent (decided while writing the code, before the first result):
 D1 One position at a time; while in a position no new setups are taken, but sweep extremes keep updating.
 D2 The sweep starts on the first bar whose high > PDH (short) / low < PDL (long); the sweep bar itself may be the
    setup candle if it is red (short) / green (long).
 D3 On every bar: first check whether it triggers the current setup, then, if this bar is itself a qualifying candle,
    it becomes the new setup for later bars.
 D4 Entry fill = the trigger, or the bar's open if the bar opens beyond it (gap). Entry bars 09:16..15:15 only.
 D5 Stop S1 = setup candle high (short) / low (long). S2 = the sweep extreme up to the bar before entry.
 D6 If the entry bar also trades through the stop, the trade is stopped (conservative: the order of high and low inside
    a bar is unknown). Targets are not credited on the entry bar.
 D7 Same bar touches stop and target: stop first (--target-first rows flip it).
 D8 X1: 75% at +1R, stop moves to entry, 25% to +10R, flat at the 15:20 open. A full stop-loss is −1R.
 D9 Fresh rule: after a trade on a level closes, that level re-arms only when a bar makes a new extreme beyond the
    previous sweep extreme of that level.
 D10 Per day: max 3 entries; no entries after 2 full stop-losses.
 D11 Skip entries with R < 0.10 (2 ticks) or R > 1% of the entry price.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from backtested.costs import cash_round_trip_bp  # noqa: E402
from backtested.data import Panel, eligible, session_features  # noqa: E402
from backtested.stats import periods, tstat  # noqa: E402

try:                                   # numba makes the 210-stock run take minutes instead of hours (optional)
    from numba import njit
except ImportError:                    # pragma: no cover
    def njit(*a, **k):
        return (lambda f: f) if not a or not callable(a[0]) else a[0]

FIELDS = ["di", "side", "setup_bar", "entry_bar", "entry", "stop", "R", "exit_reason", "exit_bar", "r_mult", "mfe_R", "full_sl"]
EXIT_NAMES = {1: "stop", 2: "target", 3: "eod", 4: "breakeven"}
FLAT = 365                       # 15:20 bar index
LAST_ENTRY = 360                 # 15:15 bar index
INDEX_NAMES = ("NIFTY", "NIFTY50", "NIFTY 50", "_NIFTY50")
CANONICAL = ("NIFTY", 1, 1, 1)   # universe, A, S, X
RISK_RS = 1_000.0                # ₹ risked per trade in the ₹ view (the video's "risk a fixed amount")


@njit(cache=True)
def simulate(o, h, l, c, A, S, X, target_first):
    """All sessions of one instrument (sessions x 375 grids). Returns an (n, 12) array with FIELDS."""
    nd, nm = o.shape
    out = np.full((nd * 3, 12), np.nan)
    k = 0
    tgtR = 1.0 if X == 4 else (3.0 if X == 2 else 10.0)
    for d in range(1, nd):
        pdh = -1e18; pdl = 1e18; ok = False                       # previous session's levels
        for m in range(nm):
            if h[d - 1, m] == h[d - 1, m]:
                ok = True
                if h[d - 1, m] > pdh: pdh = h[d - 1, m]
                if l[d - 1, m] < pdl: pdl = l[d - 1, m]
        if not ok: continue
        # per side: index 0 = short (PDH), 1 = long (PDL)
        active = np.zeros(2, np.bool_); ext = np.array([-1e18, 1e18]); last_ext = np.array([-1e18, 1e18])
        armed = np.ones(2, np.bool_); setup_m = np.array([-1, -1]); setup_hi = np.zeros(2); setup_lo = np.zeros(2)
        entries = 0; full_sl = 0; inpos = False
        side = 0; e_px = 0.0; st = 0.0; R = 0.0; partial = False; mfe = 0.0
        for m in range(nm):
            if o[d, m] != o[d, m]: continue
            hi = h[d, m]; lo = l[d, m]; op = o[d, m]; cl = c[d, m]
            if inpos:                                             # manage the open position
                sgn = -1.0 if side == 0 else 1.0
                fav = (e_px - lo) if side == 0 else (hi - e_px)
                if fav / R > mfe: mfe = fav / R
                if m == FLAT or m == nm - 1:
                    px = op if m == FLAT else cl
                    r = sgn * (px - e_px) / R
                    out[k - 1, 7] = 3; out[k - 1, 8] = m
                    out[k - 1, 9] = (0.75 + 0.25 * r) if partial else r
                    out[k - 1, 10] = mfe; inpos = False
                    continue
                hit_stop = (hi >= st) if side == 0 else (lo <= st)
                if X == 1 and not partial:
                    t1 = e_px - R if side == 0 else e_px + R
                    hit_t = (lo <= t1) if side == 0 else (hi >= t1)
                    if hit_stop and (not hit_t or not target_first):
                        out[k - 1, 7] = 1; out[k - 1, 8] = m; out[k - 1, 9] = -1.0; out[k - 1, 10] = mfe; out[k - 1, 11] = 1
                        full_sl += 1; inpos = False
                    elif hit_t:
                        partial = True; st = e_px
                        t10 = e_px - 10 * R if side == 0 else e_px + 10 * R
                        if (lo <= t10) if side == 0 else (hi >= t10):
                            out[k - 1, 7] = 2; out[k - 1, 8] = m; out[k - 1, 9] = 0.75 + 0.25 * 10; out[k - 1, 10] = mfe; inpos = False
                elif X == 1 and partial:
                    t10 = e_px - 10 * R if side == 0 else e_px + 10 * R
                    hit_t = (lo <= t10) if side == 0 else (hi >= t10)
                    if hit_stop and (not hit_t or not target_first):
                        out[k - 1, 7] = 4; out[k - 1, 8] = m; out[k - 1, 9] = 0.75; out[k - 1, 10] = mfe; inpos = False
                    elif hit_t:
                        out[k - 1, 7] = 2; out[k - 1, 8] = m; out[k - 1, 9] = 0.75 + 2.5; out[k - 1, 10] = mfe; inpos = False
                else:
                    tp = e_px - tgtR * R if side == 0 else e_px + tgtR * R
                    hit_t = (lo <= tp) if side == 0 else (hi >= tp)
                    if hit_stop and (not hit_t or not target_first):
                        out[k - 1, 7] = 1; out[k - 1, 8] = m; out[k - 1, 9] = -1.0; out[k - 1, 10] = mfe; out[k - 1, 11] = 1
                        full_sl += 1; inpos = False
                    elif hit_t:
                        out[k - 1, 7] = 2; out[k - 1, 8] = m; out[k - 1, 9] = tgtR; out[k - 1, 10] = mfe; inpos = False
                if not inpos:
                    last_ext[side] = ext[side]; armed[side] = False; active[side] = False; setup_m[side] = -1
            # sweep tracking on both sides; re-arm a level only after a new extreme (fresh rule, D9)
            eb0 = ext[0]; eb1 = ext[1]                            # sweep extremes before this bar (stop S2)
            for s in range(2):
                beyond = (hi > pdh) if s == 0 else (lo < pdl)
                if not beyond: continue
                x = hi if s == 0 else lo
                if not armed[s]:
                    if (s == 0 and x > last_ext[s]) or (s == 1 and x < last_ext[s]):
                        armed[s] = True; active[s] = False; ext[s] = x
                    else:
                        continue
                if not active[s]:
                    active[s] = True; ext[s] = x; setup_m[s] = -1
                else:
                    if (s == 0 and x > ext[s]) or (s == 1 and x < ext[s]): ext[s] = x
            if inpos: continue
            if entries >= 3 or full_sl >= 2: continue
            # entries: does this bar trigger a setup formed on an earlier bar? (D3, D4)
            for s in range(2):
                if not active[s] or setup_m[s] < 0 or m < 1 or m > LAST_ENTRY: continue
                trig = setup_lo[s] if s == 0 else setup_hi[s]
                fired = (lo < trig) if s == 0 else (hi > trig)
                if not fired: continue
                px = trig
                if s == 0 and op < trig: px = op
                if s == 1 and op > trig: px = op
                if S == 1:
                    stp = setup_hi[s] if s == 0 else setup_lo[s]
                else:
                    stp = eb0 if s == 0 else eb1
                Rr = (stp - px) if s == 0 else (px - stp)
                if Rr < 0.1 or Rr > 0.01 * px:                    # D11
                    setup_m[s] = -1
                    continue
                entries += 1
                side = s; e_px = px; st = stp; R = Rr; partial = False
                fav = (e_px - lo) if s == 0 else (hi - e_px)
                mfe = max(0.0, fav / R)
                out[k, 0] = d; out[k, 1] = -1 if s == 0 else 1; out[k, 2] = setup_m[s]; out[k, 3] = m; out[k, 4] = px
                out[k, 5] = stp; out[k, 6] = Rr; out[k, 11] = 0
                k += 1
                inpos = True
                if (s == 0 and hi >= stp) or (s == 1 and lo <= stp):  # D6: the entry bar also went through the stop
                    out[k - 1, 7] = 1; out[k - 1, 8] = m; out[k - 1, 9] = -1.0; out[k - 1, 10] = mfe; out[k - 1, 11] = 1
                    full_sl += 1; inpos = False
                    last_ext[s] = ext[s]; armed[s] = False; active[s] = False; setup_m[s] = -1
                break
            if inpos: continue
            for s in range(2):                                    # this bar as the new setup candle
                if not active[s]: continue
                q = (cl < op) if s == 0 else (cl > op)
                if not q: continue
                if A == 2 and not ((hi > pdh) if s == 0 else (lo < pdl)): continue
                setup_m[s] = m; setup_hi[s] = hi; setup_lo[s] = lo
    return out[:k]


# ---------------------------------------------------------------- one symbol, one cell
def default_cost_bp(sym: str, is_index: bool, index_cost_bp: float, half_spread_bp: float) -> float:
    """Round-trip cost in bp. Index: futures charges + slippage (2.2 bp, PROTOCOL.md). Stocks: cash intraday charges at
    ₹1 lakh + the bid-ask spread (one number you choose; our private per-stock spreads aren't published)."""
    return index_cost_bp if is_index else cash_round_trip_bp(100_000, half_spread_bp=half_spread_bp)


def run_symbol(args) -> pd.DataFrame:
    panel, sym, is_index, A, S, X, tf, cost_bp = args
    g = panel.load(sym)
    T = pd.DataFrame(simulate(*(np.ascontiguousarray(g[k], dtype=np.float64) for k in "ohlc"), A, S, X, tf), columns=FIELDS)
    T["sym"] = sym
    if not is_index:                                              # stocks: liquid stock-days only (as in case 01)
        F = session_features(g)
        T = T[T.di.astype(int).isin(F.di[eligible(F)].values)]
    T["cost_bp"] = cost_bp
    return T


def summarize(T: pd.DataFrame, label: str, dates: np.ndarray) -> dict:
    T = T.copy()
    T["gross_bp"] = T.r_mult * T.R / T.entry * 1e4
    T["net_bp"] = T.gross_bp - T.cost_bp
    row = dict(cell=label, n=len(T), per_day=round(len(T) / len(dates), 2), win=round((T.r_mult > 0).mean(), 3),
               mean_R=round(T.r_mult.mean(), 3), gross_bp=round(T.gross_bp.mean(), 2), net_bp=round(T.net_bp.mean(), 2),
               t_net=round(tstat(T.net_bp), 2), mfe3=round((T.mfe_R >= 3).mean(), 3), mfe10=round((T.mfe_R >= 10).mean(), 3),
               full_sl=round(T.full_sl.mean(), 3), med_R_bp=round((T.R / T.entry * 1e4).median(), 1))
    for name, m in periods(dates):
        sel = m[T.di.astype(int).values]
        x = T.net_bp[sel]
        row[name] = f"{x.mean():+.2f}bp t{tstat(x):+.2f} n{sel.sum()}"
    row["passes"] = bool(all(float(row[n].split("bp")[0]) > 0 and float(row[n].split(" t")[1].split()[0]) >= 2 for n, _ in periods(dates)))
    return row


# ---------------------------------------------------------------- the ₹ view of the canonical cell
def rupees(T: pd.DataFrame, dates: np.ndarray, out: str) -> dict:
    """Fixed ₹1,000 risk a trade: position = ₹1,000 / R points x price; cost = cost_bp of that position."""
    T = T.sort_values(["di", "entry_bar"]).copy()
    T["date"] = dates[T.di.astype(int).values]
    T["gross_rs"] = T.r_mult * RISK_RS
    T["notional_rs"] = RISK_RS * T.entry / T.R
    T["cost_rs"] = T.notional_rs * T.cost_bp / 1e4
    T["net_rs"] = T.gross_rs - T.cost_rs
    by_year = T.groupby(T.date.str[:4]).agg(trades=("net_rs", "size"), gross_rs=("gross_rs", "sum"), cost_rs=("cost_rs", "sum"),
                                           net_rs=("net_rs", "sum")).round(0)
    by_year.index.name = "year"
    by_year.to_csv(os.path.join(out, "by_year.csv"))
    pd.DataFrame(dict(date=T.date, gross_rs=T.gross_rs.cumsum().round(0), net_rs=T.net_rs.cumsum().round(0))).to_csv(
        os.path.join(out, "path_rs.csv"), index=False)
    S = dict(cell="NIFTY A1 S1 X1", trades=len(T), first=T.date.iloc[0], last=T.date.iloc[-1], win=round(float((T.r_mult > 0).mean()), 3),
             gross_rs=round(float(T.gross_rs.sum())), cost_rs=round(float(T.cost_rs.sum())), net_rs=round(float(T.net_rs.sum())),
             median_R_points=round(float(T.R.median()), 2), median_notional_rs=round(float(T.notional_rs.median())),
             median_cost_rs=round(float(T.cost_rs.median())), reached_3R=round(float((T.mfe_R >= 3).mean()), 3),
             reached_10R=round(float((T.mfe_R >= 10).mean()), 3),
             exits={EXIT_NAMES[int(k)]: round(float(v), 3) for k, v in T.exit_reason.value_counts(normalize=True).items()})
    with open(os.path.join(out, "summary.json"), "w") as f:
        json.dump(S, f, indent=1, ensure_ascii=False)
    return S


# ---------------------------------------------------------------- everything
def run(panel: Panel, out: str, universe: str = "all", index_names=INDEX_NAMES, workers: int = 8, cost_fn=None,
        index_cost_bp: float = 2.2, half_spread_bp: float = 2.0):
    os.makedirs(out, exist_ok=True)
    idx = [s for s in panel.symbols if s in index_names]
    stk = [s for s in panel.symbols if s not in index_names]
    cost_fn = cost_fn or (lambda s, is_idx: default_cost_bp(s, is_idx, index_cost_bp, half_spread_bp))
    groups = []
    if universe in ("index", "all") and idx: groups.append(("NIFTY", idx[:1], True))
    if universe in ("stocks", "all") and stk: groups.append(("STOCKS", stk, False))
    costs = {s: cost_fn(s, is_idx) for _, syms, is_idx in groups for s in syms}
    rows, canonical = [], None
    for uname, syms, is_idx in groups:
        for A in (1, 2):
            for S in (1, 2):
                for X in (1, 2, 3, 4):
                    for tf in (False, True):
                        jobs = [(panel, s, is_idx, A, S, X, tf, costs[s]) for s in syms]
                        if len(jobs) > 1 and workers > 1:
                            with ProcessPoolExecutor(workers) as ex:
                                T = pd.concat(list(ex.map(run_symbol, jobs)), ignore_index=True)
                        else:
                            T = pd.concat([run_symbol(j) for j in jobs], ignore_index=True)
                        label = f"{uname} A{A} S{S} X{X}" + (" TF" if tf else "")
                        row = summarize(T, label, panel.dates)
                        rows.append(row)
                        if (uname, A, S, X) == CANONICAL and not tf:
                            canonical = T
                        print(f"{label:<22} n={row['n']:>7} win={row['win']:.3f} meanR={row['mean_R']:+.3f} net={row['net_bp']:+.2f}bp "
                              f"t={row['t_net']:+.2f} 10R={row['mfe10']:.3f} | {row['2016-21']} | {row['2022-24H1']} | {row['2024H2-26']}", flush=True)
    R = pd.DataFrame(rows)
    R.to_csv(os.path.join(out, "cells.csv"), index=False)
    S = rupees(canonical, panel.dates, out) if canonical is not None else None
    return R, canonical, S


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", required=True, help="folder of SYMBOL.csv / .csv.gz / .parquet 1-minute files")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"))
    ap.add_argument("--universe", choices=("index", "stocks", "all"), default="all")
    ap.add_argument("--index", default=",".join(INDEX_NAMES), help="comma-separated file names to treat as the index")
    ap.add_argument("--index-cost-bp", type=float, default=2.2, help="index futures round trip (charges + slippage), bp")
    ap.add_argument("--half-spread-bp", type=float, default=2.0, help="stocks: half of the bid-ask spread, bp")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    R, _, S = run(Panel.from_dir(a.data), a.out, a.universe, tuple(a.index.split(",")), a.workers,
                  index_cost_bp=a.index_cost_bp, half_spread_bp=a.half_spread_bp)
    print(f"\n{(~R.passes).sum()} of {len(R)} cells fail the pass rule (after costs, > 0 with t >= 2 in all three periods)")
    if S:
        print(f"Canonical NIFTY cell at ₹1,000 risk a trade: {S['trades']:,} trades, before costs ₹{S['gross_rs']:,}, "
              f"costs ₹{S['cost_rs']:,}, net ₹{S['net_rs']:,}")
    print(f"outputs in {a.out}")
