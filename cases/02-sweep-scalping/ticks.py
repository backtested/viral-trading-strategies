#!/usr/bin/env python3
"""CASE 02, execution check: NIFTY futures tick replay with real bid/ask fills (canonical rules A1 · S1).

Signals: the same engine as strategy.py, on 1-minute bars built from the front-month NIFTY future's last traded price.
Fills are then re-priced tick by tick: entry = the first tick through the trigger, filled at the touch (a short sells
the bid, a long buys the ask); stop = the first tick through the stop, at the opposite touch; targets are limit orders
filled at the target price when the LTP trades through it; flat at the first tick at/after 15:20, at the touch.

Input: a folder with one file per session for the front-month NIFTY future:
    TICKS/2026-07-20.csv   (or .csv.gz)
with columns
    ts       tick time in IST, e.g. 2026-07-20 09:15:41.250 (or 2026-07-20T09:15:41)
    ltp      last traded price
    bid      best bid
    ask      best ask
    volume   cumulative day volume (ticks with 0 are skipped)
Consecutive files are treated as consecutive sessions (yesterday's high/low comes from the previous file), so record
every session; pass --calendar (one YYYY-MM-DD per line) to skip pairs that aren't consecutive trading days.

Usage:
  python cases/02-sweep-scalping/ticks.py --ticks path/to/nifty_fut_ticks [--out DIR] [--charges-bp 1.2]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from strategy import FIELDS, simulate  # noqa: E402

FLAT = 365


def read_day(path: str, day: str) -> pd.DataFrame | None:
    """Ticks of one session in arrival order -> columns m (minute index), sec, ltp, bid, ask."""
    df = pd.read_csv(path)
    ts = pd.to_datetime(df["ts"].astype(str).str.replace("T", " ", regex=False))
    if getattr(ts.dt, "tz", None) is not None:
        ts = ts.dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
    m = (ts.dt.hour - 9) * 60 + (ts.dt.minute - 15)
    ok = (ts.dt.strftime("%Y-%m-%d") == day) & (m >= 0) & (m <= 374) & (df["ltp"] > 0) & (df["volume"] > 0)
    t = pd.DataFrame(dict(m=m[ok], sec=(ts.dt.second + ts.dt.microsecond / 1e6)[ok], ltp=df["ltp"][ok],
                          bid=df["bid"][ok].where(df["bid"][ok] > 0), ask=df["ask"][ok].where(df["ask"][ok] > 0)))
    if t.empty:
        return None
    t = t.sort_values(["m", "sec"], kind="stable").reset_index(drop=True)
    t["bid"] = t.bid.ffill()
    t["ask"] = t.ask.ffill()
    return t


def bars(t: pd.DataFrame):
    """1-minute OHLC (375 slots) from the LTP."""
    g = t.groupby("m").ltp
    o = np.full(375, np.nan); h = o.copy(); l = o.copy(); c = o.copy()
    o[g.first().index] = g.first().values; h[g.max().index] = g.max().values
    l[g.min().index] = g.min().values; c[g.last().index] = g.last().values
    return o, h, l, c


def reprice(t: pd.DataFrame, tr, X: int):
    """Tick-level fills for one trade from the bar engine. Returns the R multiple and fill details (no charges)."""
    s = -1 if int(tr.side) < 0 else 1
    e_bar = int(tr.entry_bar)
    tt = t[t.m >= e_bar].reset_index(drop=True)
    cand = tt[(tt.m == e_bar) & ((tt.ltp <= tr.entry) if s < 0 else (tt.ltp >= tr.entry))]
    if cand.empty:
        return None
    i0 = cand.index[0]
    fill = tt.bid[i0] if s < 0 else tt.ask[i0]
    if not np.isfinite(fill):
        fill = tt.ltp[i0]
    R = abs(fill - tr.stop)
    if R <= 0:
        return None
    tgt1 = fill + s * R
    tgtX = fill + s * (10 * R if X in (1, 3) else (3 * R if X == 2 else R))
    partial, st = False, tr.stop
    for i in range(i0, len(tt)):
        p, m = tt.ltp[i], tt.m[i]
        if m >= FLAT:
            px = tt.ask[i] if s < 0 else tt.bid[i]
            px = px if np.isfinite(px) else p
            r = s * (px - fill) / R
            return dict(r=(0.75 + 0.25 * r) if partial else r, fill=fill, R=R, exit="eod")
        if (s < 0 and p >= st) or (s > 0 and p <= st):
            px = tt.ask[i] if s < 0 else tt.bid[i]
            px = px if np.isfinite(px) else p
            r = s * (px - fill) / R
            return dict(r=(0.75 + 0.25 * r) if partial else r, fill=fill, R=R, exit="breakeven" if partial else "stop")
        if X == 1 and not partial and ((s < 0 and p <= tgt1) or (s > 0 and p >= tgt1)):
            partial, st = True, fill
        if ((s < 0 and p <= tgtX) or (s > 0 and p >= tgtX)) and (X != 1 or partial):
            rr = 10.0 if X in (1, 3) else (3.0 if X == 2 else 1.0)
            return dict(r=(0.75 + 0.25 * rr) if X == 1 else rr, fill=fill, R=R, exit="target")
    r = s * (tt.ltp.iloc[-1] - fill) / R
    return dict(r=(0.75 + 0.25 * r) if partial else r, fill=fill, R=R, exit="end")


def run(days: dict, calendar: list | None = None, charges_bp: float = 1.2, risk_rs: float = 1_000.0):
    """days: {YYYY-MM-DD: tick DataFrame from read_day}. Returns (per-trade DataFrame, per-exit-scheme summary)."""
    keys, cal = sorted(days), list(calendar or [])
    rows = []
    for X in (1, 2, 3, 4):
        for d0, d1 in zip(keys[:-1], keys[1:]):
            if d1 in cal and d0 in cal and cal.index(d1) - cal.index(d0) != 1:
                continue                                       # levels need the previous *trading* session
            o, h, l, c = (np.vstack([x, y]) for x, y in zip(bars(days[d0]), bars(days[d1])))
            tr = pd.DataFrame(simulate(o, h, l, c, 1, 1, X, False), columns=FIELDS)
            for _, x in tr.iterrows():
                rp = reprice(days[d1], x, X)
                if rp is None:
                    continue
                rows.append(dict(day=d1, X=X, side=int(x.side), entry_bar=int(x.entry_bar), bar_entry=x.entry, tick_fill=rp["fill"],
                                 bar_R=x.R, tick_R=rp["R"], bar_r=x.r_mult, tick_r=rp["r"], tick_exit=rp["exit"],
                                 slip_bp=(rp["fill"] - x.entry) * (1 if x.side > 0 else -1) / x.entry * 1e4))
    D = pd.DataFrame(rows)
    out = []
    for X, g in D.groupby("X"):
        net_bp = g.tick_r * g.tick_R / g.tick_fill * 1e4 - charges_bp   # the spread is already paid in the fills
        net_rs = g.tick_r * risk_rs - risk_rs * g.tick_fill / g.tick_R * charges_bp / 1e4
        out.append(dict(X=int(X), trades=len(g), days=g.day.nunique(), first=g.day.min(), last=g.day.max(),
                        bar_R=round(g.bar_r.mean(), 3), tick_R=round(g.tick_r.mean(), 3), win=round((g.tick_r > 0).mean(), 3),
                        slip_bp_median=round(g.slip_bp.median(), 2), net_bp=round(net_bp.mean(), 2),
                        t=round(net_bp.mean() / (net_bp.std(ddof=1) / np.sqrt(len(net_bp))), 2), net_rs=round(float(net_rs.sum()))))
    return D, pd.DataFrame(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ticks", required=True)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"))
    ap.add_argument("--calendar", help="file with one trading date per line (optional)")
    ap.add_argument("--charges-bp", type=float, default=1.2, help="exchange/broker charges per round trip, bp")
    a = ap.parse_args()
    files = {os.path.basename(f).split(".")[0]: f for f in glob.glob(os.path.join(a.ticks, "*.csv*"))}
    days = {d: t for d, f in sorted(files.items()) if (t := read_day(f, d)) is not None and len(t) > 1000}
    cal = open(a.calendar).read().split() if a.calendar else None
    D, S = run(days, cal, a.charges_bp)
    os.makedirs(a.out, exist_ok=True)
    S.to_csv(os.path.join(a.out, "ticks_cells.csv"), index=False)
    print(f"{len(days)} sessions with ticks\n{S.to_string(index=False)}")
    if len(S):
        with open(os.path.join(a.out, "ticks_summary.json"), "w") as f:
            json.dump(S[S.X == 1].iloc[0].to_dict(), f, indent=1, default=str)
