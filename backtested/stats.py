"""Small statistics helpers shared by every case."""
import math

import numpy as np


def tstat(x) -> float:
    """t-statistic of the mean (is the average really different from zero, or just noise?)."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return x.mean() / (x.std(ddof=1) / math.sqrt(len(x))) if len(x) > 2 else np.nan


def periods(dates: np.ndarray):
    """The three fixed sub-periods every case reports, so a result can't hide in one lucky stretch."""
    return (
        ("2016-21", dates <= "2021-12-31"),
        ("2022-24H1", (dates >= "2022-01-01") & (dates <= "2024-06-30")),
        ("2024H2-26", dates >= "2024-07-01"),
    )
