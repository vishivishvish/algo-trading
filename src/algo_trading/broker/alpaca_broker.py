from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide as AlpacaOrderSide
from alpaca.trading.enums import TimeInForce
from alpaca.trading.requests import MarketOrderRequest

from algo_trading.broker.base import Broker, OrderSide, Position


class AlpacaBroker(Broker):
    """Broker backed by Alpaca's paper/live trading API. Works for both us_equity
    and crypto symbols through the same TradingClient — only time_in_force differs
    (crypto orders must be GTC, equity day-trades use DAY)."""

    def __init__(self, api_key: str, secret_key: str, asset_class: str, paper: bool = True):
        self._client = TradingClient(api_key, secret_key, paper=paper)
        self.asset_class = asset_class

    def get_buying_power(self) -> float:
        account = self._client.get_account()
        return float(account.buying_power)

    def get_position(self, symbol: str) -> Position | None:
        try:
            pos = self._client.get_open_position(symbol.replace("/", ""))
        except Exception:
            return None
        return Position(
            symbol=symbol,
            qty=float(pos.qty),
            avg_entry_price=float(pos.avg_entry_price),
            market_value=float(pos.market_value),
            unrealized_pl=float(pos.unrealized_pl),
        )

    def submit_market_order(self, symbol: str, side: OrderSide, notional_usd: float):
        time_in_force = TimeInForce.GTC if self.asset_class == "crypto" else TimeInForce.DAY
        request = MarketOrderRequest(
            symbol=symbol,
            notional=round(notional_usd, 2),
            side=AlpacaOrderSide.BUY if side == OrderSide.BUY else AlpacaOrderSide.SELL,
            time_in_force=time_in_force,
        )
        return self._client.submit_order(request)
