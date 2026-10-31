# CASE NN: <strategy name>, pre-registered test

Written <date>, **before** any result was computed. Commit this file before writing `strategy.py`.
Changes after the first run go in Amendments, with the reason. Never overwrite this text.

## Source
<Where the strategy comes from: platform, upload date, views. Describe the strategy, not the person.>

## Rules as stated
1. <Entry condition, in the creator's words, paraphrased>
2. <Direction / instrument>
3. <Exit>
4. <Filters, position size, stop loss (if any)>

## Claims to check
- **C1** <a measurable claim, e.g. "wins 8 days out of 10">
- **C2** <...>

## Data and execution (fixed)
- Data: <instruments, date range, bar size>
- Signal time / first moment it is knowable: <...>
- Entry price: <the first tradable price after the signal; no look-ahead>
- Exit price: <...>
- Gross result per trade: <e.g. signed log-return × 10⁴ (bp)>

## Variants (declared now)
<List every variant you will report. Mark the one closest to the creator's rules as canonical.>

## Pass rule
<e.g. gross > cost and t ≥ 2 in all three sub-periods of backtested.stats.periods()>

## Costs
<broker charges + spread assumptions; see backtested/costs.py>

## Out of scope
<what can't be coded, and why>

## Amendments
<none yet>
