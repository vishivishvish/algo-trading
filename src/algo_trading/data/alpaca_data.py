import pandas as pd
from alpaca.data.historical.crypto import CryptoHistoricalDataClient
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest, CryptoLatestTradeRequest, StockBarsRequest, StockLatestTradeRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

from algo_trading.data.base import DataFeed

_TIMEFRAME_UNITS = {"Min": TimeFrameUnit.Minute, "Hour": TimeFrameUnit.Hour, "Day": TimeFrameUnit.Day}


def _parse_timeframe(timeframe: str) -> TimeFrame:
    # e.g. "1Min", "5Min", "1Hour"
    digits = "".join(c for c in timeframe if c.isdigit()) or "1"
    unit_str = "".join(c for c in timeframe if c.isalpha())
    return TimeFrame(int(digits), _TIMEFRAME_UNITS[unit_str])


class AlpacaDataFeed(DataFeed):
    """DataFeed backed by Alpaca. `asset_class` must be "us_equity" or "crypto" —
    crypto needs no API keys for market data, equities do."""

    def __init__(self, asset_class: str, api_key: str = None, secret_key: str = None):
        self.asset_class = asset_class
        if asset_class == "crypto":
            self._client = CryptoHistoricalDataClient(api_key or None, secret_key or None)
        elif asset_class == "us_equity":
            self._client = StockHistoricalDataClient(api_key, secret_key)
        else:
            raise ValueError(f"Unsupported asset_class: {asset_class}")

    def get_recent_bars(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        tf = _parse_timeframe(timeframe)
        if self.asset_class == "crypto":
            req = CryptoBarsRequest(symbol_or_symbols=symbol, timeframe=tf, limit=limit)
            bars = self._client.get_crypto_bars(req)
        else:
            req = StockBarsRequest(symbol_or_symbols=symbol, timeframe=tf, limit=limit)
            bars = self._client.get_stock_bars(req)

        df = bars.df
        if isinstance(df.index, pd.MultiIndex):
            df = df.loc[symbol]
        return df[["open", "high", "low", "close", "volume"]].tail(limit)

    def get_latest_price(self, symbol: str) -> float:
        if self.asset_class == "crypto":
            req = CryptoLatestTradeRequest(symbol_or_symbols=symbol)
            trade = self._client.get_crypto_latest_trade(req)[symbol]
        else:
            req = StockLatestTradeRequest(symbol_or_symbols=symbol)
            trade = self._client.get_stock_latest_trade(req)[symbol]
        return float(trade.price)
