#!/usr/bin/env python3
"""Entry point for the intraday momentum paper-trading loop.

Usage:
    python scripts/run_paper_trading.py           # loop forever
    python scripts/run_paper_trading.py --once     # single pass, useful for testing
"""
import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from algo_trading.broker.alpaca_broker import AlpacaBroker
from algo_trading.config import load_settings
from algo_trading.data.alpaca_data import AlpacaDataFeed
from algo_trading.execution.paper_trading_loop import PaperTradingLoop
from algo_trading.strategy.momentum import MomentumStrategy


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Run a single pass instead of looping forever")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    settings = load_settings()

    if not settings.alpaca_api_key and settings.asset_class == "us_equity":
        raise SystemExit("ALPACA_API_KEY/ALPACA_SECRET_KEY not set — copy .env.example to .env and fill them in.")

    broker = AlpacaBroker(
        api_key=settings.alpaca_api_key,
        secret_key=settings.alpaca_secret_key,
        asset_class=settings.asset_class,
        paper=settings.alpaca_paper,
    )
    data_feed = AlpacaDataFeed(
        asset_class=settings.asset_class,
        api_key=settings.alpaca_api_key,
        secret_key=settings.alpaca_secret_key,
    )
    strategy = MomentumStrategy(
        lookback_bars=settings.strategy.lookback_bars,
        entry_threshold_pct=settings.strategy.entry_threshold_pct,
        exit_threshold_pct=settings.strategy.exit_threshold_pct,
    )
    loop = PaperTradingLoop(
        broker=broker,
        data_feed=data_feed,
        strategy=strategy,
        symbols=settings.symbols,
        timeframe=settings.strategy.timeframe,
        lookback_bars=settings.strategy.lookback_bars,
        position_size_usd=settings.strategy.position_size_usd,
        poll_interval_seconds=settings.poll_interval_seconds,
    )

    if args.once:
        loop.run_once()
    else:
        loop.run_forever()


if __name__ == "__main__":
    main()
