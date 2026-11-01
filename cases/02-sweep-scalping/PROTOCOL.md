# CASE 02: the viral "liquidity sweep" scalping strategy (previous-day high/low), pre-registered test

Written 2026-10-31 (evening), **before** any case 02 code or result existed, and published here afterwards together with
the code (see "About this file" at the end). Changes after the first run go in the Amendments section with the reason;
this text is never overwritten.

## Source
A viral YouTube video (Hindi, about 23 min, uploaded 7 Jun 2026, 20 lakh+ views by 31 Oct 2026) presenting a scalping
strategy "for beginners". We test the strategy, not the person, so we don't name the creator. Rules were taken from
the video's own explanation (timestamps below are from the video). The presenter demonstrates on **gold (XAUUSD), on a
1-minute chart**, and says (≈06:35) that for Nifty/Sensex "you'll have to backtest it yourself". This test does that
for NIFTY and NSE F&O stocks.

## Rules as stated (paraphrased)
1. Daily chart: mark the **previous day's high and low** (ignore the running candle) (07:57–08:21).
2. Switch to the **1-minute** chart. If price stays inside the range, no trade (08:39–09:14).
3. **Short at the high:** once price crosses above the previous-day high ("fresh liquidity"), wait for a **red candle**;
   when a later candle **breaks that red candle's low**, go short. Stop-loss above it. First target = the next swing
   (09:57–10:30, 11:10–11:20).
4. **Long at the low:** the mirror image: after crossing below the previous-day low, a **green candle**; entry when its
   **high breaks**, stop below it, target the swing high (11:21–11:50).
5. Management: book **70–80% at the first target**, move the stop to cost, leave **20–30% for bigger targets**
   (10:27–10:33, 13:30–13:35). No trailing (13:13).
6. Per day: **2 trades**; at most **2 full stop-losses**; a trade moved to cost doesn't count as a stop-loss, so a
   third trade is allowed after a partial (11:19, 12:54–13:40, 16:13–16:26).
7. Only **fresh** sweeps count, not touches in the middle of the range (17:55–18:00, 20:14).

## Claims to check
- **C1** "World's best strategy… you will see results" (01:46, 02:22): positive expectancy after costs, in every period.
- **C2** "1:10 trades; my failure trade is 1:3", also "1:20, 1:30" (05:55–06:27, 12:28–12:33): how often trades reach 3R / 10R.
- **C3** "Works if you follow it; backtest it on Nifty/Sensex yourself" (06:35–06:41): the result on NIFTY + F&O stocks.

## Data and execution (fixed)
- NIFTY 50 index 1-minute bars 2016-09-01 → 2026-09-25 (2,482 sessions) and 210 current F&O stocks (same panel and
  same liquidity filter as case 01). 2026 tick data (Apr → Oct) for an execution check.
- Levels: the previous session's high/low (09:15–15:29). Entries 09:16–15:15; everything flat at 15:20 (intraday).
- Sweep: a 1-minute bar's high > PDH (short side) or low < PDL (long side). After the sweep, the **setup candle** is the
  most recent completed red (short) / green (long) candle; **entry** is a stop order at its low (short) / high (long),
  filled when a *later* bar trades through it (fill = trigger, or the bar's open if it gaps past). Doji = not a setup.
- Stop: per cell (below). Risk R = |entry − stop|. Trades with R < 2 ticks or R > 1% of price are skipped (degenerate;
  the presenter also says to skip very wide stops, 21:01–21:07).
- Same-bar conflict (stop and target inside one bar): **stop first** (conservative); sensitivity: target first.
- Fresh rule: after a trade on a level closes, that level re-arms only after a **new extreme** beyond the previous sweep.
- Per day: max 3 entries; stop for the day after 2 full stop-losses.

## Grid (32 cells, declared now)
- **U (universe):** NIFTY index · 210 F&O stocks
- **A (setup candle):** A1 = any red/green candle after the sweep · A2 = the candle must itself trade beyond the level
- **S (stop):** S1 = the setup candle's high/low · S2 = the sweep extreme (highest high / lowest low since the sweep)
- **X (exit):** X1 = 75% at 1R, stop to cost, 25% to 10R or 15:20 (his scheme) · X2 = fixed 1:3 · X3 = fixed 1:10 · X4 = fixed 1:1
Canonical cell (closest to the video): **NIFTY · A1 · S1 · X1**.

## Reported per cell
Trades, trades/day, win rate, average R, **expectancy in R and bp after costs**, t-stat, the share of trades whose best
point (MFE) reached 3R and 10R, and the three periods 2016–21 / 2022–24H1 / 2024H2–26.

## Costs (declared now)
- NIFTY: traded as index futures: charges ≈ 1.2 bp round trip + slippage 0.5 bp per side (2.2 bp round trip).
  Sensitivity 4 bp.
- Stocks: the case 01 cash-intraday model (charges + per-stock half-spread + 0.5 bp per side).
- Option version (2026 only, real recorded option prices): ATM option, same signals, reported separately.

## Pass rule
After costs: expectancy > 0 with t ≥ 2 in **all three** periods. Otherwise "doesn't work as stated".

## Verification
1. **Independent re-implementation**: a second engine written from this protocol alone (not from the first code); trade
   lists must match, or every difference is explained.
2. **Visual audit**: ≥ 12 random trades drawn on 1-minute charts with levels, setup candle, entry, stop and exits.
3. **Execution check**: 2026 tick data (NIFTY futures) vs the 1-minute result.

## Out of scope
Gold / forex / crypto (not our data; offshore gold/forex CFDs also aren't legal for Indian residents). Discretion ("be
creative", "micro-liquidity") can't be coded; the test uses the rules as stated.

## Amendments
- 2026-11-01: published. The option version (ATM options, 2026) declared above was **not run**; the execution check
  is the NIFTY futures tick replay only. Implementation details
  where this text is silent (one position at a time, the entry-bar rule, etc.) are listed in `strategy.py`.

## About this file
Case 01's README promised that from case 02 on the protocol would be committed here before the first run. For case 02
it wasn't: it was written privately before the first run (31 Oct 2026, evening) and is published here with the code.
The text above is the original apart from removing the creator's details and private data-source details. From case 03 on, the
protocol is committed first.
