# AGENTS.md: instructions for AI coding agents

This repo tests viral trading strategies on real 1-minute market data. You (an AI coding agent: Claude Code, Cursor,
Copilot, Codex, Gemini CLI, ...) will usually be asked to run a case on the user's data, change a variant, explain a
result, or add a new case. Read this first.

## Map

```
backtested/            shared library (no strategy logic here)
  data.py              Panel: loads one file per symbol into a sessions x 375-minute grid (09:15 -> index 0)
                       session_features(), eligible(), monthly_expiry_flags()
  costs.py             broker charges (cash intraday, options) + configurable bid-ask spread
  options.py           Black-Scholes repricing (a model, used only when option history is unavailable)
  stats.py             tstat(), periods(): the three fixed sub-periods every case reports
cases/NN-name/
  PROTOCOL.md          the rules and variants, written BEFORE any result
  strategy.py          the case, runnable: python cases/NN-name/strategy.py --data DIR
  RESULTS.md           findings + caveats
  results/             the maintainers' aggregate outputs (compare your run against these)
cases/_template/       copy this to start a new case
examples/              make_sample_data.py: synthetic bars to smoke-test without real data
tests/                 python tests/test_smoke.py
```

## Data format

One file per symbol in a folder: `SYMBOL.csv`, `SYMBOL.csv.gz` or `SYMBOL.parquet`, columns
`datetime, open, high, low, close, volume`; `datetime` is the bar's start time in IST (tz-aware timestamps are
converted). `date` + `time` columns also work. When a user's files look different (broker exports, JSON, one big file
for all symbols), write a small converter script into `examples/` rather than changing `backtested/data.py`.

Grid conventions: `g["o"][di, m]` is the open of minute `m` on session `di`; `minute_index(9, 30) == 15`. Missing bars
are NaN. Sessions are the union of dates across all files.

## Rules of a fair backtest (non-negotiable)

1. **Protocol first.** For a new case or a new variant, write or amend `PROTOCOL.md` before running anything, and
   suggest the user commits it first, so the history proves the rules came before the results.
2. **Never tune on the result.** Don't change thresholds, times or filters after seeing numbers unless it's recorded as
   an amendment with the reason. Report every declared variant, not just the best one.
3. **No look-ahead.** Filters may only use previous sessions (see `rolling_mean_prev`). Entry happens at the first moment
   the signal is knowable (e.g. a 09:15 candle's colour is known at 09:16:00, so enter at the 09:16 open).
4. **Gross, then costs.** Report the gross move (bp) first, then costs from `costs.py`, so they can be swapped.
5. **Sub-periods.** Report the three periods from `stats.periods()`. A strategy that only works in one is luck.
6. **Label models as models.** Option P&L from `options.py` is a Black-Scholes model, not market fills. Say so in output.
7. **Don't overclaim.** Results describe the past on this data. Never phrase anything as advice.

## Common tasks

- *Run a case:* `python cases/01-915-strategy/strategy.py --data DIR [--out DIR] [--half-spread-bp 2]`
- *Smoke test:* `python examples/make_sample_data.py examples/sample_data && python tests/test_smoke.py`
- *New case:* copy `cases/_template` to `cases/NN-short-name`, fill `PROTOCOL.md` from the user's description or
  transcript (rules as stated, claims to check, variants, pass rule), stop for the user to commit, then implement
  `strategy.py` reusing `backtested/` (mirror case 01's structure: build -> select -> metrics -> report).
- *Explain a result:* read the case's `RESULTS.md` and `results/*.csv` before running anything.

## Style

Plain Python 3.10+, numpy and pandas only (pyarrow optional for Parquet). Vectorise over the grid; one process per
symbol is fine (`ProcessPoolExecutor`). Keep each case self-contained and readable by a non-expert.
