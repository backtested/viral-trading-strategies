"""Trading costs, from the broker's public charge schedule (Zerodha, as used in EP01, Oct 2026).

Charges change: check your broker's current page before relying on these numbers.
Costs are reported separately from the gross result in every case, so you can plug in your own.
"""


def cash_intraday_fee_bp(notional: float) -> float:
    """Equity intraday (MIS) round-trip charges in bp of one-way notional: brokerage 0.03 % or ₹20 per order (lower),
    STT 0.025 % on sell, exchange 0.00307 % per side, SEBI ₹10/crore per side, GST 18 %, stamp duty 0.003 % on buy."""
    n = notional
    brokerage = 2 * min(n * 0.0003, 20)
    stt = n * 0.00025
    exchange = 2 * n * 0.0000307
    sebi = 2 * n * 1e-6
    gst = 0.18 * (brokerage + exchange + sebi)
    stamp = n * 0.00003
    return (brokerage + stt + exchange + gst + sebi + stamp) / n * 1e4


def cash_round_trip_bp(notional: float = 100_000, half_spread_bp: float = 2.0, slippage_bp: float = 0.5) -> float:
    """Total round-trip cost: charges + crossing the bid-ask spread twice + a little slippage.

    EP01's video figure (stock, ₹1 L a trade) used per-stock half-spreads measured from our own quote data, which we
    don't publish. Here the half-spread is one number you choose; 2 bp is typical for liquid F&O stocks at 09:16,
    and the most volatile top-of-list names can be wider."""
    return cash_intraday_fee_bp(notional) + 2 * (half_spread_bp + slippage_bp)


def option_round_trip_charges(buy_premium: float, sell_premium: float) -> float:
    """Option round trip in ₹ for premium turnover (₹) bought and sold: brokerage ₹20 + ₹20, STT 0.1 % of sell premium,
    exchange 0.03503 % per side, SEBI ₹10/crore, stamp 0.003 % of buy premium, GST 18 % on brokerage + exchange + SEBI."""
    brokerage = 40.0
    stt = 0.001 * sell_premium
    exchange = 0.0003503 * (buy_premium + sell_premium)
    sebi = 1e-6 * (buy_premium + sell_premium)
    stamp = 0.00003 * buy_premium
    gst = 0.18 * (brokerage + exchange + sebi)
    return brokerage + stt + exchange + sebi + stamp + gst
