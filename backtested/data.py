"""Load 1-minute bars into a session grid: one row per trading session, 375 columns (09:15 ... 15:29 IST).

Every case in this repo works on the same grid, so a strategy only ever deals with numpy arrays:
    g["o"][di, m], g["h"], g["l"], g["c"], g["v"]   di = session index, m = minute index (09:15 -> 0)
Missing bars are NaN. Sessions are the union of trading dates across all symbols you provide.

Input files (one per symbol) in a folder: SYMBOL.csv, SYMBOL.csv.gz or SYMBOL.parquet with columns
    datetime, open, high, low, close, volume
`datetime` is the bar's start time in IST (naive, or tz-aware: it is converted to Asia/Kolkata).
A column pair `date` + `time` also works.
"""
from __future__ import annotations

import datetime as dt
import glob
import os
from typing import Callable, Dict, Iterable, List

import numpy as np
import pandas as pd

MINUTES = 375  # 09:15:00 .. 15:29:00
FIELDS = "ohlcv"
Grid = Dict[str, np.ndarray]


def minute_index(hh: int, mm: int) -> int:
    """Index of the 1-minute bar that starts at hh:mm IST (09:15 -> 0, 09:30 -> 15, 15:29 -> 374)."""
    return (hh - 9) * 60 + (mm - 15)


# ---------------------------------------------------------------- file reading
def _files(folder: str) -> Dict[str, str]:
    out = {}
    for f in sorted(glob.glob(os.path.join(folder, "*"))):
        b = os.path.basename(f)
        for ext in (".csv.gz", ".csv", ".parquet"):
            if b.endswith(ext):
                out[b[: -len(ext)]] = f
    return out


def _read(path: str, columns: List[str] | None = None) -> pd.DataFrame:
    df = pd.read_parquet(path, columns=columns) if path.endswith(".parquet") else pd.read_csv(path, usecols=columns)
    if "datetime" not in df.columns and {"date", "time"} <= set(df.columns):
        df["datetime"] = df["date"].astype(str) + " " + df["time"].astype(str)
    ts = pd.to_datetime(df["datetime"])
    if getattr(ts.dt, "tz", None) is not None:
        ts = ts.dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
    df["_date"] = ts.dt.strftime("%Y-%m-%d")
    df["_m"] = (ts.dt.hour - 9) * 60 + (ts.dt.minute - 15)
    return df


def _dates_in(path: str) -> np.ndarray:
    try:
        df = _read(path, ["datetime"])
    except (ValueError, KeyError):
        df = _read(path, ["date", "time"])
    return df["_date"].unique()


# ---------------------------------------------------------------- the panel
class Panel:
    """Sessions x 375 minute grids for many symbols, loaded one symbol at a time (memory friendly)."""

    def __init__(self, dates: Iterable[str], symbols: Iterable[str], loader: Callable[[str], Grid]):
        self.dates = np.array(sorted(dates))
        self.years = np.array([int(d[:4]) for d in self.dates])
        self.symbols = list(symbols)
        self._loader = loader

    def load(self, sym: str) -> Grid:
        return self._loader(sym)

    @classmethod
    def from_dir(cls, folder: str, calendar: Iterable[str] | None = None) -> "Panel":
        files = _files(folder)
        if not files:
            raise FileNotFoundError(f"no SYMBOL.csv / .csv.gz / .parquet files in {folder}")
        if calendar is None:
            cal = set()
            for f in files.values():
                cal.update(_dates_in(f))
            calendar = cal
        dates = np.array(sorted(calendar))
        return cls(dates, files.keys(), _DirLoader(files, dates))


class _DirLoader:
    """Picklable loader (so symbols can be processed in parallel)."""

    def __init__(self, files: Dict[str, str], dates: np.ndarray):
        self.files, self.dates = files, dates

    def __call__(self, sym: str) -> Grid:
        df = _read(self.files[sym])
        df = df[(df["_m"] >= 0) & (df["_m"] < MINUTES)]
        di = np.searchsorted(self.dates, df["_date"].values)
        ok = (di < len(self.dates)) & (self.dates[np.minimum(di, len(self.dates) - 1)] == df["_date"].values)
        g = {k: np.full((len(self.dates), MINUTES), np.nan) for k in FIELDS}
        for k, col in zip(FIELDS, ("open", "high", "low", "close", "volume")):
            g[k][di[ok], df["_m"].values[ok]] = df[col].values[ok].astype(float)
        return g


# ---------------------------------------------------------------- per-session features (used by eligibility and option models)
def daily_fields(g: Grid) -> Dict[str, np.ndarray]:
    """Per session: open (09:15 bar open), close (last bar), prev_close (previous session's close), high, low, turnover, nbars."""
    fin = np.isfinite(g["c"])
    n = fin.shape[0]
    has = fin.any(axis=1)
    last = np.where(has, fin.shape[1] - 1 - np.argmax(fin[:, ::-1], axis=1), 0)
    close = np.where(has, g["c"][np.arange(n), last], np.nan)
    with np.errstate(all="ignore"):
        high = np.where(has, np.nanmax(np.where(fin, g["h"], np.nan), axis=1), np.nan)
        low = np.where(has, np.nanmin(np.where(fin, g["l"], np.nan), axis=1), np.nan)
    turnover = np.where(has, np.nansum(g["c"] * g["v"], axis=1), np.nan)
    prev_close = np.concatenate([[np.nan], close[:-1]])
    return dict(open=g["o"][:, 0], close=close, prev_close=prev_close, high=high, low=low, turnover=turnover, nbars=fin.sum(axis=1))


def rolling_mean_prev(x: np.ndarray, w: int, min_obs: int = 10) -> np.ndarray:
    """Mean of the previous `w` sessions, excluding today (no look-ahead)."""
    return pd.Series(x).shift(1).rolling(w, min_periods=min_obs).mean().to_numpy()


def session_features(g: Grid) -> pd.DataFrame:
    """Per-session features, all computed from information available before the session opens (except `open`/`gap`)."""
    d = daily_fields(g)
    F = pd.DataFrame({"di": np.arange(len(d["open"])), "open": d["open"], "prev_close": d["prev_close"], "nbars": d["nbars"]})
    F["turn20"] = rolling_mean_prev(d["turnover"], 20)                       # avg daily traded value, last 20 sessions
    F["range20"] = rolling_mean_prev((d["high"] - d["low"]) / d["prev_close"], 20)  # avg daily range / prev close
    with np.errstate(all="ignore"):
        F["gap"] = np.log(F.open / F.prev_close)
    return F


def eligible(F: pd.DataFrame, min_turnover=50e7, min_price=20.0, min_bars=300, max_gap=0.15) -> pd.Series:
    """Liquid enough to trade: 20-day turnover >= ₹50 cr, price >= ₹20, >= 300 bars that day, |gap| <= 15 %."""
    return (F.turn20 >= min_turnover) & (F.prev_close >= min_price) & (F.nbars >= min_bars) & (F.gap.abs() <= max_gap)


def monthly_expiry_flags(dates: Iterable[str]) -> np.ndarray:
    """NSE monthly stock F&O expiry sessions: last Thursday of the month up to Aug 2025, last Tuesday from Sep 2025,
    moved back to the previous trading day when that day is a holiday."""
    dates = list(dates)
    ds = [dt.date.fromisoformat(x) for x in dates]
    have, flags = set(ds), np.zeros(len(ds), bool)
    for y, mo in sorted({(d.year, d.month) for d in ds}):
        weekday = 3 if (y, mo) < (2025, 9) else 1
        last = dt.date(y + (mo == 12), mo % 12 + 1, 1) - dt.timedelta(days=1)
        while last.weekday() != weekday:
            last -= dt.timedelta(days=1)
        while last not in have and last >= dt.date(y, mo, 1):
            last -= dt.timedelta(days=1)
        if last in have:
            flags[dates.index(last.isoformat())] = True
    return flags
