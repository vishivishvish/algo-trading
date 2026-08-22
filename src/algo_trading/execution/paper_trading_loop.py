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
        stop_loss_pct: float,
        max_daily_loss_usd: float,
    ):
        self.broker = broker
        self.data_feed = data_feed
        self.strategy = strategy
        self.symbols = symbols
        self.timeframe = timeframe
        self.lookback_bars = lookback_bars
        self.position_size_usd = position_size_usd
        self.poll_interval_seconds = poll_interval_seconds
        self.stop_loss_pct = stop_loss_pct
        self.max_daily_loss_usd = max_daily_loss_usd
        self.realized_pnl_today = {symbol: 0.0 for symbol in symbols}
        self.halted_symbols = set()

    def run_once(self):
        for symbol in self.symbols:
            if symbol in self.halted_symbols:
                logger.debug("Trading halted for %s — skipping poll", symbol)
                continue
            self._process_symbol(symbol)

    def run_forever(self):
        logger.info("Starting paper trading loop for %s", self.symbols)
        while True:
            self.run_once()
            time.sleep(self.poll_interval_seconds)

    def _process_symbol(self, symbol: str):
        bars = self.data_feed.get_recent_bars(symbol, self.timeframe, limit=self.lookback_bars + 1)
        position = self.broker.get_position(symbol)

        if position is not None and self._stop_loss_triggered(position, bars):
            self._close_position(symbol, position, reason="STOP-LOSS")
            return

        signal = self.strategy.generate_signal(bars, has_open_position=position is not None)

        if signal == Signal.BUY:
            logger.info("BUY signal for %s — submitting $%.2f market order", symbol, self.position_size_usd)
            self.broker.submit_market_order(symbol, OrderSide.BUY, self.position_size_usd)
        elif signal == Signal.SELL and position is not None:
            self._close_position(symbol, position, reason="SELL signal")
        else:
            logger.debug("HOLD for %s", symbol)

    def _stop_loss_triggered(self, position, bars) -> bool:
        """Force-exit if price has dropped `stop_loss_pct` or worse from the
        position's entry price, regardless of what the strategy's momentum
        signal says — a hard floor on a single trade's loss."""
        current_price = bars["close"].iloc[-1]
        pct_change = (current_price - position.avg_entry_price) / position.avg_entry_price * 100
        return pct_change <= self.stop_loss_pct

    def _close_position(self, symbol: str, position, reason: str):
        logger.info("%s for %s — closing position worth $%.2f", reason, symbol, position.market_value)
        self.broker.submit_market_order(symbol, OrderSide.SELL, position.market_value)
        self._record_realized_pnl(symbol, position.unrealized_pl)

    def _record_realized_pnl(self, symbol: str, pnl: float):
        """Track cumulative P&L per symbol for the day. Once a symbol's losses
        breach `max_daily_loss_usd`, halt trading on that symbol only — other
        symbols keep trading. Stays halted until the process is restarted."""
        self.realized_pnl_today[symbol] += pnl
        pnl_today = self.realized_pnl_today[symbol]
        if symbol not in self.halted_symbols and pnl_today <= -self.max_daily_loss_usd:
            self.halted_symbols.add(symbol)
            logger.warning(
                "MAX DAILY LOSS breached for %s (realized P&L $%.2f <= -$%.2f) — halting %s until restarted",
                symbol,
                pnl_today,
                self.max_daily_loss_usd,
                symbol,
            )
