import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from algo_trading.broker.base import Broker, OrderSide, Position
from algo_trading.data.base import DataFeed
from algo_trading.execution.paper_trading_loop import PaperTradingLoop
from algo_trading.strategy.base import Signal, Strategy


class FakeBroker(Broker):
    def __init__(self, positions=None):
        self.positions = positions or {}
        self.orders = []

    def get_buying_power(self) -> float:
        return 10_000.0

    def get_position(self, symbol):
        return self.positions.get(symbol)

    def submit_market_order(self, symbol, side, notional_usd):
        self.orders.append((symbol, side, notional_usd))


class FakeDataFeed(DataFeed):
    def __init__(self, closes_by_symbol):
        self.closes_by_symbol = closes_by_symbol

    def get_recent_bars(self, symbol, timeframe, limit):
        return pd.DataFrame({"close": self.closes_by_symbol[symbol]})

    def get_latest_price(self, symbol) -> float:
        return self.closes_by_symbol[symbol][-1]


class FakeStrategy(Strategy):
    """Always returns HOLD — isolates the stop-loss check from strategy logic."""

    def generate_signal(self, bars, has_open_position) -> Signal:
        return Signal.HOLD


def _make_loop(positions, closes_by_symbol, symbols, stop_loss_pct, max_daily_loss_usd=1_000_000):
    broker = FakeBroker(positions=positions)
    loop = PaperTradingLoop(
        broker=broker,
        data_feed=FakeDataFeed(closes_by_symbol),
        strategy=FakeStrategy(),
        symbols=symbols,
        timeframe="1Min",
        lookback_bars=3,
        position_size_usd=100,
        poll_interval_seconds=30,
        stop_loss_pct=stop_loss_pct,
        max_daily_loss_usd=max_daily_loss_usd,
    )
    return loop, broker


def _single_symbol_loop(position, closes, stop_loss_pct, max_daily_loss_usd=1_000_000):
    positions = {"BTC/USD": position} if position is not None else {}
    return _make_loop(
        positions,
        closes_by_symbol={"BTC/USD": closes},
        symbols=["BTC/USD"],
        stop_loss_pct=stop_loss_pct,
        max_daily_loss_usd=max_daily_loss_usd,
    )


def test_stop_loss_forces_exit_even_when_strategy_holds():
    position = Position(symbol="BTC/USD", qty=1, avg_entry_price=100.0, market_value=98.0, unrealized_pl=-2.0)
    loop, broker = _single_symbol_loop(position, closes=[100, 99.5, 99, 98], stop_loss_pct=-1.0)

    loop.run_once()

    assert broker.orders == [("BTC/USD", OrderSide.SELL, 98.0)]


def test_no_stop_loss_when_within_threshold():
    position = Position(symbol="BTC/USD", qty=1, avg_entry_price=100.0, market_value=99.5, unrealized_pl=-0.5)
    loop, broker = _single_symbol_loop(position, closes=[100, 99.8, 99.6, 99.5], stop_loss_pct=-1.0)

    loop.run_once()

    assert broker.orders == []


def test_no_stop_loss_check_when_flat():
    loop, broker = _single_symbol_loop(position=None, closes=[100, 99, 98, 50], stop_loss_pct=-1.0)

    loop.run_once()

    assert broker.orders == []


def test_max_daily_loss_halts_trading_after_breach():
    position = Position(symbol="BTC/USD", qty=1, avg_entry_price=100.0, market_value=85.0, unrealized_pl=-15.0)
    loop, broker = _single_symbol_loop(position, closes=[100, 95, 90, 85], stop_loss_pct=-1.0, max_daily_loss_usd=10)

    loop.run_once()  # stop-loss fires, realized loss $15 breaches the $10 daily cap

    assert broker.orders == [("BTC/USD", OrderSide.SELL, 85.0)]
    assert loop.halted_symbols == {"BTC/USD"}

    loop.run_once()  # a second poll should do nothing — halted until manually restarted

    assert broker.orders == [("BTC/USD", OrderSide.SELL, 85.0)]


def test_max_daily_loss_not_triggered_by_small_losses():
    position = Position(symbol="BTC/USD", qty=1, avg_entry_price=100.0, market_value=98.0, unrealized_pl=-2.0)
    loop, broker = _single_symbol_loop(position, closes=[100, 99.5, 99, 98], stop_loss_pct=-1.0, max_daily_loss_usd=10)

    loop.run_once()

    assert loop.halted_symbols == set()


def test_max_daily_loss_halts_only_the_breaching_symbol():
    btc_position = Position(symbol="BTC/USD", qty=1, avg_entry_price=100.0, market_value=85.0, unrealized_pl=-15.0)
    eth_position = Position(symbol="ETH/USD", qty=1, avg_entry_price=100.0, market_value=99.5, unrealized_pl=-0.5)
    loop, broker = _make_loop(
        positions={"BTC/USD": btc_position, "ETH/USD": eth_position},
        closes_by_symbol={"BTC/USD": [100, 95, 90, 85], "ETH/USD": [100, 99.8, 99.6, 99.5]},
        symbols=["BTC/USD", "ETH/USD"],
        stop_loss_pct=-1.0,
        max_daily_loss_usd=10,
    )

    loop.run_once()  # BTC stop-loss breaches its own $10 cap; ETH stays within its own

    assert loop.halted_symbols == {"BTC/USD"}
    assert broker.orders == [("BTC/USD", OrderSide.SELL, 85.0)]

    loop.run_once()  # BTC skipped (halted); ETH still polled but has no reason to trade

    assert broker.orders == [("BTC/USD", OrderSide.SELL, 85.0)]
