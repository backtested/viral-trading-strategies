#!/usr/bin/env python3
"""CASE 01: the viral "9:15 strategy", tested on 1-minute data.

The rules (see PROTOCOL.md, written before any result):
  1. At 9:15, open the F&O top gainers/losers list and take the first name (the presenter prefers losers).
  2. Wait for the first 1-minute candle (09:15:00-09:15:59).
  3. Red candle -> buy the ATM put. Green -> buy the ATM call.
  4. Exit by 09:30 ("good night").
  5. Only trade if the stock opened outside yesterday's last 15-minute candle.

Usage:
  python cases/01-915-strategy/strategy.py --data path/to/minute_bars --out cases/01-915-strategy/out
  (folder of SYMBOL.csv / .csv.gz / .parquet files; see backtested/data.py for the format)

Outputs in --out: cells.csv (all 24 pre-registered variants), canonical_trades.csv, by_year.csv, summary.json,
path_option_rs.csv. Gross results are the underlying's move in bp (1 bp = 0.01 %) from entry to exit.
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from backtested.costs import cash_round_trip_bp, option_round_trip_charges  # noqa: E402
from backtested.data import Panel, eligible, minute_index, monthly_expiry_flags, session_features  # noqa: E402
from backtested.options import black_scholes, sigma_from_range, years_to_expiry  # noqa: E402
from backtested.stats import periods, tstat  # noqa: E402

ENTRY = minute_index(9, 16)          # 09:16:00 open = first moment the 09:15 candle's colour is known
EXIT = {"09:25": minute_index(9, 25), "09:30": minute_index(9, 30)}
LAST15 = slice(minute_index(15, 15), minute_index(15, 29) + 1)   # yesterday's last 15-minute candle
CANONICAL = ("S1", "D2", "on", "09:30")                          # the cell closest to the video


# ---------------------------------------------------------------- step 1: one row per eligible stock-day
def stock_days(args) -> pd.DataFrame:
    panel, sym = args
    g = panel.load(sym)
    F = session_features(g)
    F = F[eligible(F) & (F.di > 0)]
    di, pc = F.di.values, F.prev_close.values
    o, h, l, c = (g[k] for k in "ohlc")
    p = di - 1
    with np.errstate(all="ignore"):
        lc_hi, lc_lo = np.nanmax(h[p, LAST15], axis=1), np.nanmin(l[p, LAST15], axis=1)
        sgn = np.sign(c[di, 0] - o[di, 0])                                        # colour of the 09:15 candle
        hi_after, lo_after = np.nanmax(h[di, 1:15], axis=1), np.nanmin(l[di, 1:15], axis=1)
    return pd.DataFrame(dict(sym=sym, di=di, prev_close=pc, o0=o[di, 0], c0=c[di, 0], e=o[di, ENTRY],
                             x925=o[di, EXIT["09:25"]], x930=o[di, EXIT["09:30"]], c14=c[di, 14],
                             lc_hi=lc_hi, lc_lo=lc_lo, hi_after=hi_after, lo_after=lo_after, sgn=sgn, range20=F.range20.values))


def build(panel: Panel, workers: int = 8) -> pd.DataFrame:
    with ProcessPoolExecutor(workers) as ex:
        A = pd.concat(list(ex.map(stock_days, [(panel, s) for s in panel.symbols])), ignore_index=True)
    A = A[np.isfinite(A.c0) & np.isfinite(A.e) & (A.prev_close > 0)].copy()
    A["chg"] = A.c0 / A.prev_close - 1                                            # the gainers/losers list at 09:16
    A["rk_up"] = A.groupby("di").chg.rank(ascending=False, method="first")
    A["rk_dn"] = A.groupby("di").chg.rank(ascending=True, method="first")
    A["gap_ok"] = (A.o0 > A.lc_hi) | (A.o0 < A.lc_lo)
    A["date"] = panel.dates[A.di.values]
    A["year"] = panel.years[A.di.values]
    return A


# ---------------------------------------------------------------- step 2: the 24 pre-registered variants
def select(A, S, D, G):
    """S1 top loser only · S2 top gainer + top loser · S3 top-5 each side; D1 any colour · D2 colour agrees with the list side;
    G gap filter off/on."""
    up = A[A.rk_up <= {"S1": 0, "S2": 1, "S3": 5}[S]].assign(list_side=1)
    dn = A[A.rk_dn <= {"S1": 1, "S2": 1, "S3": 5}[S]].assign(list_side=-1)
    T = pd.concat([up, dn])
    T = T[T.sgn != 0]                                   # doji: no trade
    if D == "D2":
        T = T[T.sgn == T.list_side]
    if G == "on":
        T = T[T.gap_ok]
    return T


def metrics(T, X):
    x = T["x925" if X == "09:25" else "x930"]
    gross = T.sgn * np.log(x / T.e) * 1e4                              # bp the trade made, before costs
    gross_c0 = T.sgn * np.log(x / T.c0) * 1e4                          # sensitivity: enter at the 09:15 close instead
    c1 = np.sign(T.c14 - T.o0) == T.sgn                                # claim 1: the 15-min candle keeps the colour
    mfe = np.where(T.sgn > 0, np.log(T.hi_after / T.e), -np.log(T.lo_after / T.e)) * 1e4   # best point before exit
    return gross, gross_c0, c1, mfe


def cell_row(A, S, D, G, X, dates):
    T = select(A, S, D, G)
    g, g_c0, c1, mfe = metrics(T, X)
    ok = np.isfinite(g)
    T, g, g_c0, c1, mfe = T[ok], g[ok], g_c0[ok], c1[ok], mfe[ok]
    row = dict(cell=f"{S} {D} gap={G} exit={X}", n=len(T), per_day=round(len(T) / len(dates), 2),
               C1_same_colour=round(c1.mean(), 3), gross_bp=round(g.mean(), 2), t_trade=round(tstat(g.values), 2),
               win=round((g > 0).mean(), 3), gross_entry_c0=round(g_c0.mean(), 2), mfe_bp=round(np.nanmean(mfe), 1))
    for name, m in periods(dates):
        mm = m[T.di.values]
        row[name] = f"{g[mm].mean():+.1f}bp t{tstat(g[mm].values):+.2f} n{mm.sum()}"
    return row


# ---------------------------------------------------------------- step 3: what it means in ₹ (option model)
def option_pnl(T, expiry_idx, half_spread, ticket=10_000.0):
    """₹ P&L when ₹`ticket` of ATM premium is bought at 09:16 and sold at 09:30 (Black-Scholes, constant IV)."""
    out = []
    for r in T.itertuples():
        if not (r.di < expiry_idx[-1] and np.isfinite(r.range20) and r.range20 > 0):
            out.append(np.nan)
            continue
        sig, cp = sigma_from_range(r.range20), (1 if r.sgn > 0 else -1)
        p0 = black_scholes(r.e, r.e, years_to_expiry(expiry_idx, r.di, 1), sig, cp)
        p1 = black_scholes(r.x930, r.e, years_to_expiry(expiry_idx, r.di, 15), sig, cp)
        if p0 <= 0.05:
            out.append(np.nan)
            continue
        qty = ticket / p0
        buy, sell = p0 * (1 + half_spread), p1 * (1 - half_spread)
        out.append(qty * (sell - buy) - option_round_trip_charges(qty * buy, qty * sell))
    return np.array(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", required=True, help="folder of 1-minute bar files, one per symbol")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"))
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--half-spread-bp", type=float, default=2.0, help="stock bid-ask half-spread for the cash ₹ figure")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    panel = Panel.from_dir(a.data)
    print(f"{len(panel.symbols)} symbols, {len(panel.dates)} sessions ({panel.dates[0]} → {panel.dates[-1]})", flush=True)
    run(panel, a.out, a.workers, a.half_spread_bp)


def run(panel: Panel, out: str, workers: int = 8, half_spread_bp: float = 2.0):
    dates = panel.dates
    A = build(panel, workers)
    rows = [cell_row(A, *cell, dates) for cell in itertools.product(("S1", "S2", "S3"), ("D1", "D2"), ("off", "on"), ("09:25", "09:30"))]
    R = pd.DataFrame(rows)
    R.to_csv(os.path.join(out, "cells.csv"), index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print("\n24 pre-registered variants (gross = underlying move from the 09:16 entry, bp):")
    print(R.to_string(index=False))

    # canonical cell, in detail
    S_, D_, G_, X_ = CANONICAL
    T = select(A, S_, D_, G_)
    g, g_c0, c1, mfe = metrics(T, X_)
    ok = np.isfinite(g)
    T = T[ok].assign(gross=g[ok].values, c1=c1[ok].values, mfe=mfe[ok])
    T["first_minute_bp"] = np.log(T.c0 / T.o0) * 1e4
    expiry_idx = np.where(monthly_expiry_flags(dates))[0]
    for col, hs in (("opt_rs_spread1pct", 0.01), ("opt_rs_spread05pct", 0.005), ("opt_rs_nospread", 0.0)):
        T[col] = option_pnl(T, expiry_idx, hs)
    T["stock_net_bp"] = T.gross - cash_round_trip_bp(100_000, half_spread_bp)
    T.to_csv(os.path.join(out, "canonical_trades.csv"), index=False)

    S = dict(sessions=int(len(dates)), first_date=str(dates[0]), last_date=str(dates[-1]), trades=int(len(T)),
             signal_days_pct=round(T.di.nunique() / len(dates) * 100, 1),
             C1_red_stays_red_pct=round(T.c1.mean() * 100, 1),
             first_minute_move_bp_median=round(float(T.first_minute_bp.median()), 1),
             gross_bp_mean=round(float(T.gross.mean()), 1), gross_t=round(float(tstat(T.gross.values)), 2),
             win_pct=round(float((T.gross > 0).mean() * 100), 1), mfe_bp_mean=round(float(T.mfe.mean()), 1),
             stock_rs_per_trade_at_1L=round(float(T.stock_net_bp.mean() * 10), 0),
             stock_rs_total_at_1L=round(float(T.stock_net_bp.sum() * 10), 0), stock_half_spread_bp=half_spread_bp)
    for col in ("opt_rs_spread1pct", "opt_rs_spread05pct", "opt_rs_nospread"):
        x = T[col].dropna()
        S[f"{col}_mean"] = round(float(x.mean()), 0); S[f"{col}_total"] = round(float(x.sum()), 0)
        S[f"{col}_win_pct"] = round(float((x > 0).mean() * 100), 1)
    x = T.dropna(subset=["opt_rs_spread1pct"]).sort_values("di")
    roll = pd.Series((x.opt_rs_spread1pct < 0).astype(int).values).rolling(20).sum().dropna()
    S["claim_3_losers_in_20_pct_of_windows"] = round(float((roll <= 3).mean() * 100), 2)
    S["losers_in_20_median"] = float(roll.median()) if len(roll) else None
    x.groupby("date").opt_rs_spread1pct.sum().cumsum().to_csv(os.path.join(out, "path_option_rs.csv"))
    for name, m in periods(dates):
        mm = m[T.di.values]
        S[f"gross_{name}"] = f"{T.gross[mm].mean():+.1f} bp (t {tstat(T.gross[mm].values):+.2f}, n {int(mm.sum())})"
    by_year = T.groupby("year").agg(n=("gross", "size"), C1=("c1", "mean"), gross_bp=("gross", "mean"),
                                    win=("gross", lambda s: (s > 0).mean()), opt_rs=("opt_rs_spread1pct", "mean")).round(3)
    by_year.to_csv(os.path.join(out, "by_year.csv"))
    json.dump(S, open(os.path.join(out, "summary.json"), "w"), indent=1)
    print("\nCanonical (top loser, red, gap filter, exit 09:30):")
    print(json.dumps(S, indent=1))
    print(by_year.to_string())
    cost = cash_round_trip_bp(100_000, half_spread_bp)
    passed = all(T.gross[m[T.di.values]].mean() > cost and tstat(T.gross[m[T.di.values]].values) >= 2 for _, m in periods(dates))
    print(f"\nPASS RULE (gross > cost of {cost:.1f} bp, with t >= 2, in all three periods):", "PASS" if passed else "FAIL")
    return R, T, S


if __name__ == "__main__":
    main()
