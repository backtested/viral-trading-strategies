<p align="center"><b>BACKTESTED</b><br/>Viral trading strategies, tested on real market data.<br/><i>Sach ya jhooth? We let the data decide.</i><br/><a href="https://www.youtube.com/@ai_backtested">▶ Watch on YouTube: @ai_backtested</a></p>

---

Every week someone on YouTube promises a "simple, proven" trading strategy. We take those strategies, write their
rules as code **before** looking at any result, and run them on years of real 1-minute NSE data. This repo is the
code behind every episode, so you don't have to trust us: **run it yourself.**

## Cases

| # | Strategy | The claim | What the data says | Video | Code |
|---|---|---|---|---|---|
| 01 | **The 9:15 strategy**: at 9:15 take the top loser; if the first 1-minute candle is red, buy the ATM put; exit 09:30 | "Red candle stays red for 15 minutes" · "only 3 stop-losses in 20 days" | Candle claim **true** (80.5%, 10 years). Trade **loses**: −21.2 bp per trade before costs, 43.6% winners, **0 of 24** rule variants pass. Since the video went viral: 47 trades, 22 won, 25 lost. | [▶ Watch](https://youtu.be/wTFa6A3pCkM) | [`cases/01-915-strategy`](cases/01-915-strategy) |
| 02 | **Liquidity-sweep scalping**: yesterday's high/low swept on the 1-minute chart, opposite candle, enter on its break; 75% at 1:1, 25% to 1:10 | "1:10 trades; 1:3 is my failure trade" · "world's best strategy" | A **coin flip** before costs (49% winners, +₹60,258 in 10 years at ₹1,000 risk a trade); the one-candle stop makes each position ~₹20 lakh, so costs (₹26.49 lakh) sink it: **−₹25.89 lakh**, 5,220 NIFTY trades, **0 of 32** variants pass. 10R reached in 1 trade of 20. | Coming soon | [`cases/02-sweep-scalping`](cases/02-sweep-scalping) |

Each case folder has the same four files:

- `PROTOCOL.md`: the rules, the claims and every variant to test, written **before** the first run. (Case 01's protocol was written at 10:50 on 31 Oct 2026, a minute before the first result at 10:51, and published here afterwards. Case 02's was also written before its first run and published with the code; see the note at the end of its PROTOCOL.md. From case 03 on, the protocol is committed to this repo before the first run, so the commit history is the proof.)
- `strategy.py`: the rules as code. Plain Python + pandas, no framework.
- `RESULTS.md`: what we found, with the caveats.
- `results/`: our aggregate output files, so you can diff your run against ours.

## Run it in 60 seconds (no data needed)

```bash
git clone https://github.com/backtested/viral-trading-strategies.git && cd viral-trading-strategies
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

python examples/make_sample_data.py examples/sample_data          # synthetic random-walk bars, just to see it run
python cases/01-915-strategy/strategy.py --data examples/sample_data
```

Synthetic data is random, so its numbers mean nothing. It only proves the pipeline works on your machine.

## Run it on real data

The code reads one file per stock: `SYMBOL.csv`, `SYMBOL.csv.gz` or `SYMBOL.parquet`, with columns
`datetime, open, high, low, close, volume` (1-minute bars, IST). Then:

```bash
python cases/01-915-strategy/strategy.py --data /path/to/your/minute_bars
python cases/01-915-strategy/ticks.py --ticks /path/to/your/ticks --since 2026-07-17   # optional tick replay
```

**How we got our data, briefly.** Our 1-minute bars (210 F&O stocks, Sep 2016 to Sep 2026, 2,482 sessions) come from a
licensed broker historical-data API, and the 2026 tick-level sessions were recorded live from a broker websocket feed.
Exchange data licences don't allow us to redistribute raw prices, so this repo has the **code and our aggregate
results**, not the data.

**Where you can get similar data:** your broker's historical API (for example Zerodha Kite Connect, Upstox, Dhan,
Angel One SmartAPI or Fyers; check what your account includes), or paid NSE data vendors. Any source works if it gives
1-minute OHLCV per stock. With a different stock list or date range, your numbers will differ a little from ours; the
conclusions in `RESULTS.md` should not.

Our run is reproducible to the trade: on our data, this exact code gives 1,432 trades, −21.25 bp and 43.6% winners for
the main variant, and −₹2,97,183 in the option model, identical to the video. Case 02 too: all 32 cells, 5,220 NIFTY
trades and −₹25,89,225 at ₹1,000 risk a trade, plus all 915 tick-replay trades, identical.

## Use it with AI coding tools

The repo is built to be driven by an AI coding agent: Claude Code, Cursor, GitHub Copilot, OpenAI Codex, Gemini CLI,
Windsurf and similar. [`AGENTS.md`](AGENTS.md) tells the agent how the repo works and the rules of a fair backtest.
Open the folder in your tool and try:

- *"Read AGENTS.md. My Zerodha 1-minute exports are in ~/data/kite. Convert them to the repo format and run case 01."*
- *"Run case 01 with the exit at 09:20 instead of 09:30. Add it to PROTOCOL.md as an amendment first, then run it."*
- *"Explain, using cases/01-915-strategy/results, why the candle claim is true but the trade still loses."*
- *"Create case 02 for the opening range breakout strategy described below. Write PROTOCOL.md first and commit it before writing any code."*
- *"Plot the ₹ path from results/path_option_rs.csv and mark 2022."*
- *"Run case 02 with the stop at the swing instead of one candle (an amendment first). Do costs still sink it?"*

## The rules we hold ourselves to

1. **Rules before results.** The protocol is written and committed before the first run, and never edited after: changes go in an Amendments section with the reason.
2. **No cherry-picking.** Every declared variant is reported, including the ones that look bad for our conclusion.
3. **No look-ahead.** A trade only uses information that existed at that moment (filters use previous sessions; entry is the first moment a signal is known).
4. **Costs shown separately.** Gross first, then charges and spread, so you can plug in your own broker's numbers.
5. **Corrections in public.** If we get a number wrong, the fix and the reason go in the repo.

## Disclaimer

Educational research only. **Not investment advice.** We don't recommend any trade, stock or strategy. F&O trading
carries a high risk of loss: SEBI's studies found that about 9 in 10 individual F&O traders lose money. Past results,
including ours, don't predict future returns. Don't trade based on any YouTube video, including ours.

## Licence

Code: MIT (see [`LICENSE`](LICENSE)). Use it, change it, test your own ideas with it.

---
YouTube: **[@ai_backtested](https://www.youtube.com/@ai_backtested)** · Have a viral strategy you want tested? Open an issue with the video and the rules.
