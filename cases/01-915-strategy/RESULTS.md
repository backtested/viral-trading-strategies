# CASE 01 results: the 9:15 strategy

**The candle claim is true. The trade loses.** All 24 pre-registered variants are negative before any cost; 0 of 24
pass. Every number below is produced by `strategy.py` / `ticks.py` in this folder; our output files are in `results/`.

## Ten years (1-minute bars, 210 F&O stocks, 2016-09 → 2026-09)
| What | Number |
|---|---|
| Sessions | 2,482 |
| Trades, canonical variant (top loser, red first candle, gap filter, exit 09:30) | 1,432 (a signal on 57.7 % of days) |
| C1: the 15-minute candle keeps the first candle's colour | **80.5 %** (all 24 variants: 77–82 %) |
| Median first-minute move, already gone before anyone can enter | −117 bp |
| Average gross move, 09:16 entry → 09:30 | **−21.2 bp**, t −4.84 |
| Win rate | **43.6 %** (claim C3 implies ≥ 85 %) |
| 20-trade stretches with ≤ 3 losers (claim C3) | **0 %**; median 12 losers in 20 |
| Average best point after entry | +100 bp (why so many trades *look* good at some moment) |
| Sub-periods | 2016–21 −26.0 bp (t −4.10) · 2022–24H1 −8.6 bp (t −0.97) · 2024H2–26 −24.7 bp (t −3.04) |
| Entry at the 09:15 close instead of 09:16 open | −22.8 bp (earlier is not better) |
| Option model, ₹10,000 of ATM premium per trade, 1 % spread | −₹208 per trade, **−₹2,97,183 total**, lowest point −₹3,73,991, 39 % winners |
| Same at a 0.5 % spread | −₹1,53,733 total |
| Same with zero spread (impossible in practice) | −₹10,283: about breakeven before trading costs |
| Option model by year | 9 of 11 years negative; 2022 positive (+₹1,54,485 for the year) |

## 2026, tick by tick (the presenter's exact timing: enter at 09:15:40, exit 09:30:00)
| Window | Result |
|---|---|
| Since the video went viral, 17 Jul → 30 Oct 2026 (70 sessions) | **47 trades: 22 won, 25 lost**; candle claim held 87.2 %; −8.8 bp per trade (t −0.47); ₹1 lakh of stock per trade after charges and spread: **−₹10,078** |
| All recorded 2026 sessions, 10 Apr → 30 Oct (127 sessions) | 92 trades, 44 won; candle claim 84.8 %; −3.9 bp |
| 2026 trades that were ≥ 0.25 % in profit at some point before 09:30 | 82.9 % ("8 in 10", the screenshot moment); in profit at 09:30: 53.2 % |

## Why
The 15-minute candle is measured from 09:15:00, so the first minute is inside it, and that minute has already moved a
median of 1.17 % before anyone could act on its colour. After that, extreme first-minute movers bounce back a little on
average. So "the candle stays red" and "the trade loses" are both true: the colour is decided by the minute you can't trade.

## Caveats
- The stock list is today's 210 F&O stocks (survivor bias). This usually *flatters* a strategy.
- Option ₹ figures are a Black-Scholes model, not real fills: historical stock-option prices aren't available. Constant
  IV is generous on big-gap mornings, when real IV is higher at the open and falls soon after.
- The presenter's discretion ("skip slow stocks") and his unstated stop loss can't be coded; we test the rules as stated.
- 2026 (Jan–Sep) is near breakeven on the stock (−1.1 bp) and positive in the generous option model. We say so.
- The −₹10,078 stock figure uses per-stock spreads from our own quote data; with `--half-spread-bp` you choose one number.

## Reproduce
```bash
python cases/01-915-strategy/strategy.py --data /path/to/minute_bars        # 24 variants + canonical detail
python cases/01-915-strategy/ticks.py --ticks /path/to/ticks --since 2026-07-17
```
On our data this code reproduces the figures above exactly (1,432 trades, −21.25 bp, 47 post-viral trades, −₹2,97,183).

*Educational research only. Not investment advice.*
