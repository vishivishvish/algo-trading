import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from algo_trading.broker.base import Broker, OrderSide, Position
from algo_trading.data.base import DataFeed
from algo_trading.execution.paper_trading_loop import PaperTradingLoop
from algo_trading.strategy.base import Signal, Strategy


class FakeBroker(Broker):
    def __init__(self, position=None):
        self.position = position
        self.orders = []

    def get_buying_power(self) -> float:
        return 10_000.0

    def get_position(self, symbol):
        return self.position

    def submit_market_order(self, symbol, side, notional_usd):
        self.orders.append((symbol, side, notional_usd))


class FakeDataFeed(DataFeed):
    def __init__(self, closes):
        self.closes = closes

    def get_recent_bars(self, symbol, timeframe, limit):
        return pd.DataFrame({"close": self.closes})

    def get_latest_price(self, symbol) -> float:
        return self.closes[-1]


class FakeStrategy(Strategy):
    """Always returns HOLD — isolates the stop-loss check from strategy logic."""

    def generate_signal(self, bars, has_open_position) -> Signal:
        return Signal.HOLD


def _make_loop(position, closes, stop_loss_pct):
    broker = FakeBroker(position=position)
    loop = PaperTradingLoop(
        broker=broker,
        data_feed=FakeDataFeed(closes),
        strategy=FakeStrategy(),
        symbols=["BTC/USD"],
        timeframe="1Min",
        lookback_bars=3,
        position_size_usd=100,
        poll_interval_seconds=30,
        stop_loss_pct=stop_loss_pct,
    )
    return loop, broker


def test_stop_loss_forces_exit_even_when_strategy_holds():
    position = Position(symbol="BTC/USD", qty=1, avg_entry_price=100.0, market_value=98.0, unrealized_pl=-2.0)
    loop, broker = _make_loop(position, closes=[100, 99.5, 99, 98], stop_loss_pct=-1.0)

    loop.run_once()

    assert broker.orders == [("BTC/USD", OrderSide.SELL, 98.0)]


def test_no_stop_loss_when_within_threshold():
    position = Position(symbol="BTC/USD", qty=1, avg_entry_price=100.0, market_value=99.5, unrealized_pl=-0.5)
    loop, broker = _make_loop(position, closes=[100, 99.8, 99.6, 99.5], stop_loss_pct=-1.0)

    loop.run_once()

    assert broker.orders == []


def test_no_stop_loss_check_when_flat():
    loop, broker = _make_loop(position=None, closes=[100, 99, 98, 50], stop_loss_pct=-1.0)

    loop.run_once()

    assert broker.orders == []
