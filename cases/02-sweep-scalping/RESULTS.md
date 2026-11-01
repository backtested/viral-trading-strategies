# CASE 02 results: the "liquidity sweep" scalping strategy (previous-day high/low)

Run 2026-10-31 on NIFTY 50 1-minute bars (Sep 2016 → Sep 2026, 2,482 sessions) and 210 NSE F&O stocks; tick replay on
2026 NIFTY futures. Rules: [`PROTOCOL.md`](PROTOCOL.md). Code: [`strategy.py`](strategy.py), [`ticks.py`](ticks.py).
Our output files: [`results/`](results).

## Verdict
**Doesn't work as stated.** All 32 pre-registered cells (16 NIFTY, 16 F&O stocks) lose money after costs in **every**
period; 0 of 32 pass. Before costs it is a coin flip: the setup is about break-even (+0.01 to +0.14 R a trade), but the
stop sits on one 1-minute candle, so the risk per trade is tiny and costs eat about half of it.

## Canonical cell: NIFTY · A1 · S1 · X1 (the video's rules: 75% at 1R, stop to cost, 25% to 10R)
| What | Result |
|---|---|
| Trades (Sep 2016 → Sep 2026) | 5,220 (≈ 2.1 a day) |
| Win rate | 49.0% |
| Before costs | +0.012 R a trade (+0.13 bp) |
| After costs (2.2 bp round trip) | **−2.07 bp a trade, t −13.3** |
| 2016–21 / 2022–24H1 / 2024H2–26 | −2.04 / −1.90 / −2.35 bp |
| Median risk per trade | **7.8 NIFTY points = 5.0 bp**; costs are 44% of it |
| Exits | 51% stop · 41% break-even after the partial · 5% 10R · 4% at 15:20 |
| Every calendar year 2016–2026 | net negative (`results/by_year.csv`) |

**In ₹, at a fixed ₹1,000 risk a trade** (the video's own "risk a fixed amount" advice; `results/summary.json`):
before costs **+₹60,258** over 10 years; costs **₹26,49,482**; net **−₹25,89,225**. Why so much cost: a 7.8-point stop
means ₹1,000 of risk is a median **₹19.94 lakh** NIFTY position, and each round trip on that costs a median **₹439**.
Every trade pays that "toll", win or lose. 2026 alone (1 Jan → 25 Sep): 365 trades, −₹1,78,625.

## Claims
- **C1 "World's best strategy… you will see results"**: false on NIFTY and F&O stocks. 0 of 32 cells pass.
- **C2 "1:10 trades; 1:3 is my failure trade"**: trades that ever reached **10R: 5.0%** (1 in 20; 3.7% on stocks);
  reached 3R: 18.5%. With a fixed 1:3 target the win rate is 26%; with 1:10 it is 14%. The big R-multiples are real,
  but rare, and they don't pay for the many small stops plus costs.
- **C3 "Backtest it on Nifty/Sensex yourself"**: done: NIFTY 10 years, 210 F&O stocks 10 years, 2026 ticks.

## All cells (net bp a trade after costs, `results/cells.csv`)
- NIFTY: −1.38 to −2.20 bp (best: A2·S2·X3, −1.38 bp, t −2.95: fixed 1:10 target, wider stop).
- Stocks: −7.65 to −11.13 bp with our per-stock spread costs; canonical A1·S1·X1: 6,27,184 trades, win 49.7%,
  +0.019 R before costs, **−10.74 bp** after; every period negative. With this repo's default `--half-spread-bp 2`
  (our measured per-stock spreads aren't published) the stock cells range −8.85 to −12.32 bp: same verdict.
- Rows ending in `TF` are the target-first sensitivity (stop and target in the same bar → target first): no change in
  verdict (canonical −2.05 bp).

## Checks
1. **Independent engine**: a second implementation written from PROTOCOL.md alone, without seeing this code: no cell
   passes; canonical −1.90 bp (vs −2.07 here). 94.4% of trades identical (date, side, entry minute); on those, entry and
   stop prices match 100%. The rest: the second engine runs the PDH and PDL sides independently (overlapping positions),
   this one allows one position at a time.
2. **Visual audit**: 12 random trades drawn on 1-minute charts (levels, setup candle, entry, stop, 1R/10R, exit):
   the engine follows the rules. Prompted by the audit: days that *open* beyond the level (44% of trades) −1.79 bp vs
   intraday crosses −2.29 bp; the entry-bar rule (12% of trades stopped on the entry candle) relaxed: still −1.78 bp.
3. **2026 tick replay, real NIFTY futures bid/ask** (`ticks.py`, `results/ticks_cells_2026.csv`): 17 Apr → 30 Oct 2026,
   106 days with signals, 243 trades (canonical). Tick-level +0.025 R a trade before charges (the bar model said −0.058),
   entry slippage ≈ 0, **net −1.47 bp (t −2.2) = −₹59,798** at ₹1,000 risk, with only 1.2 bp of charges (the spread is
   already paid in the fills).
4. **Reproduction**: on our data this exact code gives every number above, to the trade.

## Why
The stop is one 1-minute candle away, a median 7.8 NIFTY points (5 bp). Before costs the setup is about 50/50. A round
trip costs 2+ bp, about 0.45 R every trade, so even 50% winners at 1:1 lose. The occasional 10R run (5% of trades) is
real, which is why the examples look spectacular, but it can't pay for everything else.

## Caveats
- The video demonstrates on **gold (XAUUSD)**, a 24-hour market we have no data for; it says Nifty needs its own
  backtest. This tests NIFTY and NSE F&O stocks.
- Discretion ("be creative", "micro-liquidity", skipping big stops) can't be coded; the rules as stated are tested.
- The NIFTY cost model is **generous**: exact futures charges (STT on the sell side rose to 0.02% in Oct 2024, plus
  exchange, stamp, GST) are higher than the 1.2 bp of charges assumed, which makes every result worse.
- Survivor bias in the stock list (today's F&O names) usually flatters a strategy.
