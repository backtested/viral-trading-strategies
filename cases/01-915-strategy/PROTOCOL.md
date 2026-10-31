# CASE 01: the viral "9:15 strategy", pre-registered test

Written 2026-10-31, **before** any result was computed. Changes after the first run go in the Amendments section with
the reason; this text is never overwritten.

## Source
A viral YouTube video (Hindi, about 1 h 14 min, uploaded 17 Jul 2026, 12 lakh+ views by 31 Oct 2026) presenting a
"stupid, simple and proven" 9:15 AM options setup. We test the strategy, not the person, so we don't name the creator.
Rules were taken from the video's own explanation and worked examples.

## Rules as stated (paraphrased)
1. Sit at the screen at 9:15. Open NSE's gainers/losers list filtered to F&O securities and take the first name on the
   list. The presenter prefers the losers side.
2. Wait 30 seconds after the open ("no bravery before 30 seconds"); enter around the 40th–50th second of the first minute.
3. Direction comes from the first 1-minute candle: "If the first candle is red, most of the time it stays red for
   15 minutes." Red → buy a put; green → buy a call.
4. Always buy the **ATM** option.
5. Exit by 9:25–9:30 and stop for the day ("good night at 9:30").
6. No trade when the stock opens inside the previous day's last candle; it must open breaking it.
7. A stop loss is used, but its level is never given.

## Claims to check
- **C1** "If the first candle is red, most of the time it stays red for 15 minutes" (same for green).
- **C2** "This magic happens every day. It's been happening for years and years."
- **C3** "Stop-loss days will be only three [in 20]": a win rate of at least 85 %.
- **C4** "₹2,000 to ₹8,000 by 9:30", every day, on a single lot.

## Data and execution (fixed)
- 1-minute bars for 210 current NSE F&O stocks, 2016-09-01 → 2026-09-25 (2,482 sessions).
- Eligible stock-days: average traded value over the previous 20 sessions ≥ ₹50 crore, previous close ≥ ₹20, ≥ 300 bars
  that day, |opening gap| ≤ 15 %.
- Bar 0 = 09:15:00–09:15:59. Signal = colour of bar 0 (close vs open). A doji (close = open) means no trade.
- List rank = % change of the bar-0 close vs the previous close: the gainers/losers list as it stands at 09:16.
- Entry = open of bar 1 (09:16:00), the first moment the candle's colour is known. Sensitivity: entry at the bar-0 close.
- Exit = open of the exit bar (09:25 or 09:30).
- Gross result per trade = signed log-return of the stock × 10⁴ (bp).
- Options: no historical stock-option quotes are available. The verdict must hold on the stock's own move; if the
  gross underlying move is ≤ 0, no option model can make the trade profitable.

## Grid (24 variants, declared now)
- **S (selection):** S1 top-1 loser only · S2 top-1 gainer + top-1 loser · S3 top-5 gainers + top-5 losers
- **D (direction):** D1 first-candle colour, whichever way · D2 only when the colour agrees with the list side
  (red on a loser, green on a gainer)
- **G (gap filter):** off · on = open outside the [low, high] of the previous day's last 15-minute candle (15:15–15:29)
- **X (exit):** 09:25 · 09:30

Canonical variant (closest to the video): **S1 · D2 · G on · X 09:30**.

## Reported for every variant
Number of trades, trades per day, C1 rate (the 15-minute candle 09:15–09:29 keeps bar 0's colour), gross bp from entry,
win rate, and the three sub-periods 2016–21, 2022–24H1, 2024H2–26.

## Pass rule
Gross > cost and t ≥ 2 in **all three** sub-periods. Anything else is "doesn't work as stated".

## Option cost model (declared now; used only to translate into ₹)
One lot, ATM, 15-minute hold. Broker charges: ₹20 + ₹20 brokerage, STT 0.1 % of sell premium, exchange 0.03503 % of
premium per side, SEBI ₹10/crore, stamp 0.003 % of buy premium, GST 18 % on brokerage + exchange + SEBI. Plus a bid-ask
cost of 1 % of premium per side (sensitivity 0.5 %). Opening-minutes IV decay is not modelled, which flatters the strategy.

## Out of scope
Index options (the presenter says it works "very little" on NIFTY; we test the stock version he recommends).
Discretion ("this one is slow, skip it") can't be coded.

## Amendments
- **A1 (2026-10-31, after the first run):** the declared option translation (0.5 × the stock move minus spread) was
  supplemented by a Black-Scholes reprice: ATM strike, constant IV from the 20-session average daily range, monthly
  expiry, the same spread and charges. It credits the option's convexity, so it is **more generous** to the strategy.
  The video quotes the generous number.
- **A2 (2026-10-31):** tick-by-tick replay of 2026 sessions at the presenter's exact timing (rank at 09:15:30, enter at
  09:15:40, exit 09:30:00). A robustness check, not a new variant.
