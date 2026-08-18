from abc import ABC, abstractmethod
from enum import Enum

import pandas as pd


class Signal(Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class Strategy(ABC):
    """Turns a bar history into a trading signal. Strategies never touch the
    broker or data feed directly — they're pure functions of OHLCV history plus
    whatever position state the caller passes in."""

    @abstractmethod
    def generate_signal(self, bars: pd.DataFrame, has_open_position: bool) -> Signal:
        """`bars` is oldest-first OHLCV history for one symbol."""
