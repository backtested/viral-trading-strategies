"""Black-Scholes option repricing, for strategies that trade stock options when historical option quotes aren't available.

This is a MODEL, not market data. It is deliberately generous to the option buyer: implied volatility is held
constant, while in reality it usually falls in the first minutes after the open (which hurts buyers).
"""
from math import erf, exp, log, sqrt

import numpy as np

MIN_PER_DAY = 375


def ncdf(x: float) -> float:
    return 0.5 * (1 + erf(x / sqrt(2)))


def black_scholes(S: float, K: float, T: float, sigma: float, cp: int, r: float = 0.065) -> float:
    """Price of a European call (cp=+1) or put (cp=-1). T in years."""
    if T <= 0:
        return max(cp * (S - K), 0.0)
    d1 = (log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * sqrt(T))
    d2 = d1 - sigma * sqrt(T)
    return cp * (S * ncdf(cp * d1) - K * exp(-r * T) * ncdf(cp * d2))


def years_to_expiry(expiry_idx: np.ndarray, di: int, minute: int) -> float:
    """Trading-time years from bar `minute` of session `di` to 15:30 on the next monthly expiry (252 days x 375 min)."""
    k = expiry_idx[np.searchsorted(expiry_idx, di)]
    return ((k - di) * MIN_PER_DAY + (MIN_PER_DAY - minute)) / (252 * MIN_PER_DAY)


def sigma_from_range(avg_range: float) -> float:
    """Annualised volatility from the average daily (high-low)/prev_close (Parkinson: E[range] ≈ 1.664 σ_day)."""
    return avg_range * 0.601 * sqrt(252)
