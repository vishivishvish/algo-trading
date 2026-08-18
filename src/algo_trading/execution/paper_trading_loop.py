import logging
import time

from algo_trading.broker.base import Broker, OrderSide
from algo_trading.data.base import DataFeed
from algo_trading.strategy.base import Signal, Strategy

logger = logging.getLogger("algo_trading.loop")


class PaperTradingLoop:
    """Polls the data feed on an interval, runs the strategy per symbol, and
    submits orders through the broker. Works unmodified against paper or live
    accounts — the safety boundary is which API keys/paper flag the broker
    was constructed with, not anything in this loop."""

    def __init__(
        self,
        broker: Broker,
        data_feed: DataFeed,
        strategy: Strategy,
        symbols: list[str],
        timeframe: str,
        lookback_bars: int,
        position_size_usd: float,
        poll_interval_seconds: int,
    ):
        self.broker = broker
        self.data_feed = data_feed
        self.strategy = strategy
        self.symbols = symbols
        self.timeframe = timeframe
        self.lookback_bars = lookback_bars
        self.position_size_usd = position_size_usd
        self.poll_interval_seconds = poll_interval_seconds

    def run_once(self):
        for symbol in self.symbols:
            self._process_symbol(symbol)

    def run_forever(self):
        logger.info("Starting paper trading loop for %s", self.symbols)
        while True:
            self.run_once()
            time.sleep(self.poll_interval_seconds)

    def _process_symbol(self, symbol: str):
        bars = self.data_feed.get_recent_bars(symbol, self.timeframe, limit=self.lookback_bars + 1)
        position = self.broker.get_position(symbol)
        signal = self.strategy.generate_signal(bars, has_open_position=position is not None)

        if signal == Signal.BUY:
            logger.info("BUY signal for %s — submitting $%.2f market order", symbol, self.position_size_usd)
            self.broker.submit_market_order(symbol, OrderSide.BUY, self.position_size_usd)
        elif signal == Signal.SELL and position is not None:
            logger.info("SELL signal for %s — closing position worth $%.2f", symbol, position.market_value)
            self.broker.submit_market_order(symbol, OrderSide.SELL, position.market_value)
        else:
            logger.debug("HOLD for %s", symbol)
