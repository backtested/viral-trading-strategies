# CASE 01 · The 9:15 strategy

> "Red candle at 9:15? Buy the put. It stays red for 15 minutes. Good night at 9:30."

▶ **Watch the episode:** *link coming soon*

| File | What it is |
|---|---|
| [`PROTOCOL.md`](PROTOCOL.md) | The rules, claims and 24 variants, written before the first run |
| [`strategy.py`](strategy.py) | Ten-year test on 1-minute bars: all 24 variants, the canonical trade list, the option model |
| [`ticks.py`](ticks.py) | Tick-by-tick replay at the presenter's exact timing (09:15:40 entry) |
| [`RESULTS.md`](RESULTS.md) | What we found, and the caveats |
| [`results/`](results) | Our aggregate output files: `cells.csv`, `by_year.csv`, `summary.json`, `path_option_rs.csv`, `ticks_cells_2026.csv`, `ticks_since_viral.json` |

**Verdict:** the candle claim is true (80.5 %), the trade loses (−21.2 bp a trade, 43.6 % winners, 0 of 24 variants pass).

```bash
python cases/01-915-strategy/strategy.py --data /path/to/minute_bars
```

Ideas to try yourself (write them into PROTOCOL.md as amendments first): a different exit time, the presenter's
"skip slow stocks" as a volatility filter, NIFTY instead of stocks, or entering only after the price breaks back through
the open.
