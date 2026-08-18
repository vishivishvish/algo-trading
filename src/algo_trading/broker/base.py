from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass
class Position:
    symbol: str
    qty: float
    avg_entry_price: float
    market_value: float
    unrealized_pl: float


class Broker(ABC):
    """Asset-agnostic order execution + account/position access. Implementations
    hide whether the underlying symbol is a US equity or crypto pair."""

    @abstractmethod
    def get_buying_power(self) -> float:
        """Return available cash/buying power in the account."""

    @abstractmethod
    def get_position(self, symbol: str) -> Position | None:
        """Return the current open position for `symbol`, or None if flat."""

    @abstractmethod
    def submit_market_order(self, symbol: str, side: OrderSide, notional_usd: float):
        """Submit a market order sized in dollars (notional), not share/coin qty —
        this keeps position sizing identical across equities and fractional crypto."""
