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

## Running tests

```bash
python -m pytest tests/ -v
```

## Project structure

```
config/settings.yaml           strategy + runtime config (asset class, symbols, thresholds)
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
scripts/run_paper_trading.py   entry point wiring config + components together
tests/                         unit tests (pure logic, no API keys needed)
```

## Roadmap

This v0 is intentionally naive — a single symbol-agnostic momentum signal
with fixed thresholds and a fixed-percentage stop-loss as the only risk
management. Planned directions (not yet built):

- Backtesting engine against historical bars, with realistic slippage/fees
- Multiple strategies + an allocator/portfolio layer instead of one strategy per symbol
- Richer risk management: max daily drawdown, position sizing by volatility, trailing stops
- Walk-forward parameter tuning instead of hand-set thresholds
- Transition path from crypto paper trading to funded equity live trading
