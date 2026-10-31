#!/usr/bin/env python3
"""CASE 01, tick-by-tick replay at the presenter's exact timing.

  Rank the gainers/losers list at 09:15:30 · read the candle's colour and enter at 09:15:40 (price vs the day's open)
  · exit at 09:30:00 · claim 1 checked at 09:29:59 · gap filter from the previous session's 15:15-15:30 price range.
Underlying only (stock option ticks aren't used).

Input: a folder of tick files, one per symbol per day:
    TICKS/2026-07-20/SYMBOL.csv   (or .csv.gz)
with columns
    ts          tick time in IST, e.g. 2026-07-20 09:15:41.250 (or 2026-07-20T09:15:41)
    ltp         last traded price
    volume      cumulative day volume (pre-open snapshots have 0 and are skipped)
    open        the day's open as published by the exchange feed
    prev_close  the previous session's close as published by the feed
Most broker websocket feeds ("full" mode) carry all five fields.

Usage:
  python cases/01-915-strategy/ticks.py --ticks path/to/ticks --out cases/01-915-strategy/out [--since 2026-07-17]
"""
from __future__ import annotations

import argparse
import glob
import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

AM0, AM1 = "09:15:00", "09:30:05"
PM0, PM1 = "15:15:00", "15:30:00"
T_RANK, T_ENTRY, T_C1, T_EXIT = "09:15:30", "09:15:40", "09:29:59", "09:30:00"


def replay_symbol_day(day: str, sym: str, ticks: pd.DataFrame) -> dict | None:
    """Snapshot one stock-day from its ticks (in arrival order). Returns None if the stock didn't trade at the open."""
    last, o, pc = {}, None, None
    pm_hi, pm_lo, seen_am = -np.inf, np.inf, False
    ts = ticks["ts"].astype(str).str.replace("T", " ", regex=False)
    for d_, t_, ltp, vol, op, pcl in zip(ts.str[:10], ts.str[11:19], ticks["ltp"], ticks["volume"], ticks["open"], ticks["prev_close"]):
        if d_ != day or not ltp or not np.isfinite(ltp):
            continue
        am, pm = AM0 <= t_ < AM1, PM0 <= t_ < PM1
        if pm:
            pm_hi, pm_lo = max(pm_hi, ltp), min(pm_lo, ltp)
            continue
        if not am or not vol or vol <= 0:
            continue
        seen_am = True
        o = op or o
        pc = pcl or pc
        for key in (T_RANK, T_ENTRY, T_C1, T_EXIT):
            if t_ <= key:
                last[key] = ltp
        if t_ >= T_EXIT and "x" not in last:
            last["x"] = ltp
    if not seen_am or not o or not pc:
        return None
    return dict(day=day, sym=sym, o=o, pc=pc, p_rank=last.get(T_RANK), p_entry=last.get(T_ENTRY), p_c1=last.get(T_C1),
                x=last.get("x", last.get(T_EXIT)), pm_hi=pm_hi if np.isfinite(pm_hi) else np.nan, pm_lo=pm_lo if np.isfinite(pm_lo) else np.nan)


def _one(path: str):
    day = os.path.basename(os.path.dirname(path))
    sym = os.path.basename(path).split(".")[0]
    try:
        df = pd.read_csv(path)
    except (EOFError, OSError, pd.errors.ParserError):
        return None                                   # truncated file: skip the stock-day
    return replay_symbol_day(day, sym, df)


def evaluate(R: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """From per-stock-day snapshots to trades and the five tick-level cells."""
    R = R.sort_values(["sym", "day"]).copy()
    R["prev_pm_hi"] = R.groupby("sym").pm_hi.shift(1)
    R["prev_pm_lo"] = R.groupby("sym").pm_lo.shift(1)
    R = R.dropna(subset=["p_rank", "p_entry", "p_c1", "x"])
    R["chg"] = R.p_rank / R.pc - 1
    R["rk_dn"] = R.groupby("day").chg.rank(method="first")
    R["rk_up"] = R.groupby("day").chg.rank(ascending=False, method="first")
    R["sgn"] = np.sign(R.p_entry - R.o)
    R["gap_ok"] = (R.o > R.prev_pm_hi) | (R.o < R.prev_pm_lo)
    R["gross"] = R.sgn * np.log(R.x / R.p_entry) * 1e4
    R["c1"] = np.sign(R.p_c1 - R.o) == R.sgn
    cells = []
    for name, sel in (
        ("canonical: top loser, red at 9:15:40, gap filter", (R.rk_dn == 1) & (R.sgn < 0) & R.gap_ok),
        ("top loser, red, no gap filter", (R.rk_dn == 1) & (R.sgn < 0)),
        ("top loser, either colour", (R.rk_dn == 1) & (R.sgn != 0)),
        ("top gainer + top loser, colour agrees", ((R.rk_dn == 1) & (R.sgn < 0)) | ((R.rk_up == 1) & (R.sgn > 0))),
        ("top-5 each side, colour agrees", ((R.rk_dn <= 5) & (R.sgn < 0)) | ((R.rk_up <= 5) & (R.sgn > 0))),
    ):
        s = R[sel]
        cells.append(dict(cell=name, sessions=R.day.nunique(), n=len(s), C1_same_colour=round(s.c1.mean(), 3),
                          gross_bp=round(s.gross.mean(), 1), median_bp=round(s.gross.median(), 1), win=round((s.gross > 0).mean(), 3),
                          t=round(s.gross.mean() / (s.gross.std(ddof=1) / np.sqrt(len(s))), 2) if len(s) > 2 else np.nan))
    trades = R[(R.rk_dn == 1) & (R.sgn < 0) & R.gap_ok]
    return pd.DataFrame(cells), trades


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ticks", required=True)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"))
    ap.add_argument("--since", default=None, help="only report trades on/after this date (YYYY-MM-DD)")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    files = sorted(glob.glob(os.path.join(a.ticks, "*", "*.csv*")))
    print(len(files), "stock-day files", flush=True)
    with ProcessPoolExecutor(a.workers) as ex:
        R = pd.DataFrame([r for r in ex.map(_one, files, chunksize=64) if r])
    cells, trades = evaluate(R)
    if a.since:
        trades = trades[trades.day >= a.since]
    pd.set_option("display.width", 220)
    print(cells.to_string(index=False))
    print(f"\ncanonical trades{' since ' + a.since if a.since else ''}: {len(trades)} · won {(trades.gross > 0).sum()} · "
          f"lost {(trades.gross <= 0).sum()} · candle claim held {trades.c1.mean() * 100:.1f}% · avg {trades.gross.mean():+.1f} bp")
    cells.to_csv(os.path.join(a.out, "ticks_cells.csv"), index=False)
    trades.to_csv(os.path.join(a.out, "ticks_trades.csv"), index=False)


if __name__ == "__main__":
    main()
