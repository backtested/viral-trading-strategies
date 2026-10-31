#!/usr/bin/env python3
"""CASE NN: <strategy name>. Rules: see PROTOCOL.md (commit it before running this).

Usage: python cases/NN-name/strategy.py --data path/to/minute_bars
Structure (mirror cases/01-915-strategy/strategy.py): build one row per eligible stock-day -> select trades for each
declared variant -> metrics (gross bp, win rate, t, sub-periods) -> costs -> write results/.
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from backtested.data import Panel, eligible, minute_index, session_features  # noqa: E402,F401
from backtested.stats import periods, tstat  # noqa: E402,F401


def stock_days(panel: Panel, sym: str) -> pd.DataFrame:
    g = panel.load(sym)                       # g["o"][di, m] ... m = minute_index(hh, mm)
    F = session_features(g)
    F = F[eligible(F) & (F.di > 0)]
    raise NotImplementedError("compute the signal, entry and exit prices for each eligible session here")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    panel = Panel.from_dir(a.data)
    A = pd.concat([stock_days(panel, s) for s in panel.symbols], ignore_index=True)
    print(A.head())


if __name__ == "__main__":
    main()
