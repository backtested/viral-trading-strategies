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


if __name__ == "__main__":
    test_tick_replay_snapshot()
    test_case01_runs_on_synthetic_data()
    print("smoke tests passed")
