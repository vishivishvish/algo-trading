import pandas as pd

from algo_trading.strategy.base import Signal, Strategy


class MomentumStrategy(Strategy):
    """v0 momentum strategy: measures % price change over the last `lookback_bars`
    closes. Enters long when momentum clears `entry_threshold_pct`; exits an open
    position when momentum drops to `exit_threshold_pct` (a pullback, not
    necessarily a loss). Deliberately naive — this is the seed to iterate on, not
    the final strategy."""

    def __init__(self, lookback_bars: int, entry_threshold_pct: float, exit_threshold_pct: float):
        self.lookback_bars = lookback_bars
        self.entry_threshold_pct = entry_threshold_pct
        self.exit_threshold_pct = exit_threshold_pct

    def generate_signal(self, bars: pd.DataFrame, has_open_position: bool) -> Signal:
        if len(bars) < self.lookback_bars + 1:
            return Signal.HOLD

        window = bars["close"].iloc[-(self.lookback_bars + 1):]
        momentum_pct = (window.iloc[-1] - window.iloc[0]) / window.iloc[0] * 100

        if has_open_position:
            return Signal.SELL if momentum_pct <= self.exit_threshold_pct else Signal.HOLD
        return Signal.BUY if momentum_pct >= self.entry_threshold_pct else Signal.HOLD
