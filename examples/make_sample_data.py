#!/usr/bin/env python3
"""Write synthetic 1-minute bars (random walks) in the repo's format, so you can run any case without real data.

  python examples/make_sample_data.py examples/sample_data [--symbols 40] [--sessions 300]

The numbers you get from synthetic data mean nothing. It only proves the pipeline runs on your machine.
"""
import argparse
import os

import numpy as np
import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--symbols", type=int, default=40)
    ap.add_argument("--sessions", type=int, default=300)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rng = np.random.default_rng(7)
    days = pd.bdate_range("2025-01-01", periods=a.sessions)
    minutes = pd.timedelta_range("09:15:00", periods=375, freq="1min")
    for k in range(a.symbols):
        price, rows = float(rng.uniform(200, 3000)), []
        for d in days:
            price *= np.exp(rng.normal(0, 0.012))                       # overnight gap
            r = rng.normal(0, 0.0012, 375)
            r[0] += rng.normal(0, 0.008)                                 # a lively first minute
            close = price * np.exp(np.cumsum(r))
            open_ = np.concatenate([[price], close[:-1]])
            wig = np.abs(rng.normal(0, 0.0006, 375)) * close
            vol = rng.integers(20_000, 80_000, 375)
            ts = d + minutes
            rows.append(pd.DataFrame({"datetime": ts, "open": open_.round(2), "high": (np.maximum(open_, close) + wig).round(2),
                                      "low": (np.minimum(open_, close) - wig).round(2), "close": close.round(2), "volume": vol}))
            price = close[-1]
        pd.concat(rows).to_csv(os.path.join(a.out, f"SYN{k:03d}.csv.gz"), index=False)
    print(f"wrote {a.symbols} symbols x {a.sessions} sessions to {a.out}")


if __name__ == "__main__":
    main()
