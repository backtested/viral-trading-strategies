"""BACKTESTED: shared tools for testing viral trading strategies on real 1-minute data."""
from .data import Panel, minute_index, session_features, eligible, monthly_expiry_flags  # noqa: F401
from .stats import tstat, periods  # noqa: F401

__version__ = "0.1.0"
