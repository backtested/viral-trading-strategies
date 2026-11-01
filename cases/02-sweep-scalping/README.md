# CASE 02 · The "liquidity sweep" scalping strategy

> "Yesterday's high breaks, a red candle, its low breaks: short. Book 75% at 1:1, let the rest run to 1:10."

▶ **Watch the episode:** link added after upload ([@ai_backtested](https://www.youtube.com/@ai_backtested))

| File | What it is |
|---|---|
| [`PROTOCOL.md`](PROTOCOL.md) | The rules, claims and 32 cells, written before the first run |
| [`strategy.py`](strategy.py) | Ten-year test on 1-minute bars: NIFTY + F&O stocks, all 32 cells, the ₹ view of the canonical cell |
| [`ticks.py`](ticks.py) | Execution check: NIFTY futures tick replay with real bid/ask fills |
| [`RESULTS.md`](RESULTS.md) | What we found, and the caveats |
| [`results/`](results) | Our aggregate output files: `cells.csv`, `summary.json`, `by_year.csv`, `path_rs.csv`, `ticks_cells_2026.csv` |

**Verdict:** a coin flip before costs (+₹60,258 in 10 years at ₹1,000 risk a trade), but the one-candle stop makes
each position huge, so costs (₹26.49 lakh) sink it: **−₹25.89 lakh**, 5,220 trades, **0 of 32** cells pass.

```bash
pip install numba          # optional: the 210-stock run takes minutes with it, hours without
python cases/02-sweep-scalping/strategy.py --data /path/to/minute_bars              # NIFTY.csv + stock files
python cases/02-sweep-scalping/ticks.py --ticks /path/to/nifty_futures_ticks        # optional
```

Ideas to try yourself (write them into PROTOCOL.md as amendments first): a wider stop (the swing, not one candle) so
the position and its costs shrink, BANKNIFTY, only the first sweep of the day, or trading it on 5-minute candles.
