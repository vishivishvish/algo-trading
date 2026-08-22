#!/usr/bin/env python3
"""One-off sanity check: replay the current momentum strategy + stop-loss +
max-daily-loss rules over real historical bars and print what would have
happened. Not a real backtester (no slippage/fees modeling, no fills queue)
— just a quick gut-check using the exact thresholds in config/settings.yaml.

Usage:
    python scripts/historical_sanity_check.py [--bars 1000]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from algo_trading.config import load_settings
from algo_trading.data.alpaca_data import AlpacaDataFeed
from algo_trading.strategy.base import Signal
from algo_trading.strategy.momentum import MomentumStrategy


def replay_symbol(symbol, bars, strategy, stop_loss_pct, max_daily_loss_usd, position_size_usd):
    closes = bars["close"]
    lookback = strategy.lookback_bars

    position = None  # (entry_price, qty) or None
    realized_pnl = 0.0
    halted = False
    trades = []

    for i in range(lookback, len(closes)):
        if halted:
            break

        window = bars.iloc[i - lookback : i + 1]
        price = closes.iloc[i]

        if position is not None:
            entry_price, qty = position
            pct_change = (price - entry_price) / entry_price * 100
            if pct_change <= stop_loss_pct:
                pnl = qty * (price - entry_price)
                trades.append(("STOP-LOSS", price, pnl))
                realized_pnl += pnl
                position = None
                if realized_pnl <= -max_daily_loss_usd:
                    halted = True
                continue

        signal = strategy.generate_signal(window, has_open_position=position is not None)

        if signal == Signal.BUY and position is None:
            qty = position_size_usd / price
            position = (price, qty)
        elif signal == Signal.SELL and position is not None:
            entry_price, qty = position
            pnl = qty * (price - entry_price)
            trades.append(("SELL signal", price, pnl))
            realized_pnl += pnl
            position = None
            if realized_pnl <= -max_daily_loss_usd:
                halted = True

    return trades, realized_pnl, halted


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bars", type=int, default=1000, help="How many recent bars to replay per symbol")
    args = parser.parse_args()

    settings = load_settings()
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

    print(f"Replaying {args.bars} bars per symbol at {settings.strategy.timeframe} timeframe\n")

    for symbol in settings.symbols:
        bars = data_feed.get_recent_bars(symbol, settings.strategy.timeframe, limit=args.bars)
        trades, realized_pnl, halted = replay_symbol(
            symbol,
            bars,
            strategy,
            settings.strategy.stop_loss_pct,
            settings.max_daily_loss_usd,
            settings.strategy.position_size_usd,
        )

        wins = sum(1 for _, _, pnl in trades if pnl > 0)
        losses = sum(1 for _, _, pnl in trades if pnl <= 0)
        stop_loss_exits = sum(1 for reason, _, _ in trades if reason == "STOP-LOSS")

        print(f"=== {symbol} ===")
        print(f"  bars replayed:     {len(bars)}")
        print(f"  trades closed:     {len(trades)}  ({wins} win / {losses} loss, {stop_loss_exits} via stop-loss)")
        print(f"  total realized PnL: ${realized_pnl:.2f}")
        print(f"  would be halted:   {halted}")
        print()


if __name__ == "__main__":
    main()
