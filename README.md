# algo-trading

Intraday algorithmic trading system. The seed strategy is a naive momentum
scalper — buy when price momentum over a short lookback clears a threshold,
sell on a pullback, repeat many times a day. The goal is for this to evolve
in complexity over time (better signals, risk management, portfolio-level
logic, backtesting rigor) toward a long-run target of ~15% XIRR, beating
index returns.

Everything — strategy logic, data analysis, backtesting, order placement —
runs from scripts here. The only thing that happens outside this repo is
occasionally checking positions/fills in the Alpaca dashboard.

## Features

- **Momentum strategy (v0):** buy when price momentum over a lookback window
  clears an entry threshold, sell on a pullback ([`momentum.py`](src/algo_trading/strategy/momentum.py))
- **Paper trading loop:** polls the data feed on an interval, runs the
  strategy per symbol, submits orders through the broker ([`paper_trading_loop.py`](src/algo_trading/execution/paper_trading_loop.py))
- **Asset-agnostic broker/data interfaces:** same code path for crypto and
  US equities; switching asset class is a one-line config change
- **Per-trade stop-loss:** force-exits a position once price drops
  `stop_loss_pct` from entry, independent of the momentum exit signal
- **Per-symbol max daily loss circuit breaker:** halts trading on a symbol
  once its cumulative realized loss for the run breaches `max_daily_loss_usd`;
  other symbols keep trading; no auto-reset, requires a manual restart
- **Unit tests** for strategy and loop logic (fake broker/data-feed/strategy,
  no API keys needed)

## Why Alpaca

- Free Python SDK (`alpaca-py`) built for programmatic trading — no manual
  UI steps required for data or execution.
- Free, unlimited **paper trading** environment that mirrors the live API,
  so the strategy can run for real (fake money) before any capital is at risk.
- Supports both **US equities** and **crypto** through mostly the same API.
- Commission-free equities when eventually going live.

**Note on the PDT rule:** US regulations require $25k equity to day-trade a
stock more than 3x in 5 rolling business days. Since this strategy trades a
symbol many times a day, `crypto` is the default asset class for now (no PDT
restriction, market never closes). The broker/data layer is asset-agnostic —
switching to `us_equity` later is a one-line config change, once ready to
deal with the capital requirement (or trade a small enough number of times).

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Get free paper trading API keys from
https://app.alpaca.markets/paper/dashboard/overview, then:

```bash
cp .env.example .env
# edit .env and paste in ALPACA_API_KEY / ALPACA_SECRET_KEY
```

## Running

```bash
# single pass (good for testing config/credentials)
python scripts/run_paper_trading.py --once

# loop forever, polling on the interval set in config/settings.yaml
python scripts/run_paper_trading.py
```

Strategy parameters (symbols, lookback, thresholds, position size, poll
interval) live in [`config/settings.yaml`](config/settings.yaml) — no code
changes needed to tune them.

**Max daily loss:** each symbol tracks its own cumulative realized P&L for
the run. Once a symbol's P&L drops to `-risk.max_daily_loss_usd` or worse,
the loop halts trading on that symbol only (it keeps polling and logging,
but stops placing orders for it) — other symbols are unaffected. There is
no automatic reset — restart the process to resume trading.

## Historical sanity check

```bash
python scripts/historical_sanity_check.py --bars 1000
```

Pulls recent historical bars from Alpaca and replays the current strategy +
stop-loss + max-daily-loss rules over them, printing trade count, win/loss
split, and total realized P&L per symbol. This is a quick gut-check, not a
real backtester — no slippage/fees, no order queue, and it currently gets
however many bars Alpaca's free crypto client actually returns (can be less
than `--bars`).

**Findings (2026-08-22, ~450 1-min bars per symbol):** BTC/USD ‑$0.65 over
6 trades (2W/4L), ETH/USD ‑$2.10 over 11 trades (2W/9L) — net negative on
both, no stop-loss or daily-halt triggers fired. The root cause from the
trade-by-trade log: entries barely clear the 0.3% threshold (buying the top
of a noise-level blip, not a real trend), while the exit is a *rolling*
5-bar momentum reading rather than P&L from entry — so it lags a sharp
reversal and losers (‑0.14% to ‑0.57%) run bigger than winners (+0.07% to
+0.17%) before the exit fires. At 1-min crypto resolution, 0.3%/‑0.1% sit
inside normal price noise, and none of this includes real fees/spread,
which would make live results worse. Conclusion: the thresholds need
widening or the signal needs a real trend filter before this is worth
running with actual capital.

## Running tests

```bash
python -m pytest tests/ -v
```

## Project structure

```
config/settings.yaml           strategy + runtime config (asset class, symbols, thresholds, risk limits)
src/algo_trading/
  broker/
    base.py                    abstract Broker interface (asset-agnostic)
    alpaca_broker.py           Alpaca implementation (paper or live via config)
  data/
    base.py                    abstract DataFeed interface (asset-agnostic)
    alpaca_data.py             Alpaca implementation (equities + crypto)
  strategy/
    base.py                    abstract Strategy interface
    momentum.py                v0 momentum strategy
  execution/
    paper_trading_loop.py      polls data -> strategy -> broker, on a timer
scripts/run_paper_trading.py         entry point wiring config + components together
scripts/historical_sanity_check.py   one-off replay of strategy rules over historical bars
tests/                                unit tests (pure logic, no API keys needed)
```

## Roadmap

This v0 is intentionally naive — a single symbol-agnostic momentum signal
with fixed thresholds, a fixed-percentage stop-loss per trade, and a
per-symbol max daily loss circuit breaker as the only risk management.
Planned directions (not yet built):

- Backtesting engine against historical bars, with realistic slippage/fees
- Multiple strategies + an allocator/portfolio layer instead of one strategy per symbol
- Richer risk management: position sizing by volatility, trailing stops
- Walk-forward parameter tuning instead of hand-set thresholds
- Transition path from crypto paper trading to funded equity live trading
