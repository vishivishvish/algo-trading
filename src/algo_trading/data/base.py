from abc import ABC, abstractmethod

import pandas as pd


class DataFeed(ABC):
    """Asset-agnostic market data source. Implementations hide whether the
    underlying symbol is a US equity or crypto pair."""

    @abstractmethod
    def get_recent_bars(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        """Return the most recent `limit` OHLCV bars for `symbol`, oldest first.
        Columns: open, high, low, close, volume. Index: timestamp (UTC)."""

    @abstractmethod
    def get_latest_price(self, symbol: str) -> float:
        """Return the latest traded/quoted price for `symbol`."""
