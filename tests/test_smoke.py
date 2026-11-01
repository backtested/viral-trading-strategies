#!/usr/bin/env python3
"""Smoke test: synthetic data -> case 01 end to end, plus the tick replay on a hand-made stock-day.
Run: python tests/test_smoke.py   (or pytest)"""
import os
import subprocess
import sys
import tempfile

import numpy as np
import pandas as pd

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "cases", "01-915-strategy"))
CASE02 = os.path.join(ROOT, "cases", "02-sweep-scalping")


def test_case01_runs_on_synthetic_data():
    import strategy
    from backtested.data import Panel
    with tempfile.TemporaryDirectory() as tmp:
        data, out = os.path.join(tmp, "data"), os.path.join(tmp, "out")
        subprocess.run([sys.executable, os.path.join(ROOT, "examples", "make_sample_data.py"), data, "--symbols", "12", "--sessions", "80"], check=True)
        os.makedirs(out)
        R, T, S = strategy.run(Panel.from_dir(data), out, workers=2)
        assert len(R) == 24 and S["trades"] > 0
        for f in ("cells.csv", "canonical_trades.csv", "by_year.csv", "summary.json", "path_option_rs.csv"):
            assert os.path.exists(os.path.join(out, f)), f


def test_tick_replay_snapshot():
    import ticks
    rows = [("2026-07-20 09:15:00", 100.0, 0, 0, 0),          # pre-open snapshot (volume 0) is skipped
            ("2026-07-20 09:15:01", 99.0, 10, 100.0, 104.0),
            ("2026-07-20 09:15:30", 97.0, 20, 100.0, 104.0),
            ("2026-07-20 09:15:40", 96.5, 30, 100.0, 104.0),
            ("2026-07-20 09:29:59", 98.0, 40, 100.0, 104.0),
            ("2026-07-20 09:30:00", 98.2, 50, 100.0, 104.0)]
    df = pd.DataFrame(rows, columns=["ts", "ltp", "volume", "open", "prev_close"])
    r = ticks.replay_symbol_day("2026-07-20", "TEST", df)
    assert (r["p_rank"], r["p_entry"], r["p_c1"], r["x"], r["o"], r["pc"]) == (97.0, 96.5, 98.0, 98.2, 100.0, 104.0)
    assert np.isnan(r["pm_hi"])


def _case02():
    import importlib.util
    spec = importlib.util.spec_from_file_location("case02_strategy", os.path.join(CASE02, "strategy.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_case02_hand_made_short():
    """Yesterday's high 100.5; today sweeps to 101, a red candle (high 101, low 100.6), the next bar breaks 100.6 -> short,
    stop 101 (R 0.4), then price falls through 1R and 10R."""
    S = _case02()
    n = 375
    o, h, l, c = (np.full((2, n), np.nan) for _ in range(4))
    o[0], h[0], l[0], c[0] = 100.0, 100.5, 99.5, 100.0
    path = [(100.2, 100.4, 100.1, 100.3), (100.3, 101.0, 100.3, 100.9), (100.9, 101.0, 100.6, 100.7),   # sweep, red setup
            (100.7, 100.75, 100.5, 100.55)]                                                             # entry at 100.6
    path += [(100.55 - 0.05 * i, 100.6 - 0.05 * i, 100.45 - 0.05 * i, 100.5 - 0.05 * i) for i in range(1, 100)]
    for m, (a, b, cc, d) in enumerate(path):
        o[1, m], h[1, m], l[1, m], c[1, m] = a, b, cc, d
    T = S.simulate(o, h, l, c, 1, 1, 1, False)
    assert len(T) == 1
    di, side, setup, entry_bar, entry, stop, R, exit_reason, exit_bar, r, mfe, full_sl = T[0]
    assert (side, setup, entry_bar, entry, stop) == (-1, 2, 3, 100.6, 101.0) and abs(R - 0.4) < 1e-9
    assert exit_reason == 2 and abs(r - 3.25) < 1e-9          # 75% at 1R + 25% at 10R


def test_case02_runs_on_synthetic_data():
    S = _case02()
    from backtested.data import Panel
    with tempfile.TemporaryDirectory() as tmp:
        data, out = os.path.join(tmp, "data"), os.path.join(tmp, "out")
        subprocess.run([sys.executable, os.path.join(ROOT, "examples", "make_sample_data.py"), data, "--symbols", "4", "--sessions", "40"], check=True)
        R, _, _ = S.run(Panel.from_dir(data), out, "stocks", workers=1)
        assert len(R) == 32 and os.path.exists(os.path.join(out, "cells.csv"))


if __name__ == "__main__":
    test_case02_hand_made_short()
    test_case02_runs_on_synthetic_data()
    test_tick_replay_snapshot()
    test_case01_runs_on_synthetic_data()
    print("smoke tests passed")
