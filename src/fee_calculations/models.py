"""
Various definitions.
"""

from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass
from fractions import Fraction
from hexbytes import HexBytes


@dataclass
class Trade:
    """Base class for trades"""

    # pylint: disable=too-many-instance-attributes

    order_uid: HexBytes
    owner: HexBytes
    sell_token: HexBytes
    buy_token: HexBytes
    sell_amount: int
    buy_amount: int
    limit_sell_amount: int
    limit_buy_amount: int
    kind: str

    def volume(self) -> int:
        """Compute surplus of a trade in the surplus token"""
        if self.kind == "sell":
            return self.buy_amount
        if self.kind == "buy":
            return self.sell_amount
        raise ValueError(f"Order kind {self.kind} is invalid.")

    def surplus(self) -> Fraction:
        """Compute surplus of a trade in the surplus token"""
        if self.kind == "sell":
            return self.buy_amount - self.limit_buy_amount * Fraction(
                self.sell_amount, self.limit_sell_amount
            )

        if self.kind == "buy":
            return (
                self.limit_sell_amount
                * Fraction(self.buy_amount, self.limit_buy_amount)
                - self.sell_amount
            )
        raise ValueError(f"Order kind {self.kind} is invalid.")

    def surplus_token(self) -> HexBytes:
        """Returns the surplus token"""
        if self.kind == "sell":
            return self.buy_token
        if self.kind == "buy":
            return self.sell_token
        raise ValueError(f"Order kind {self.kind} is invalid.")


class ProtocolFee(ABC):
    """Abstract class for protocol fees
    Concrete implementations have to implement a reverse_protocol_fee method.
    """

    # pylint: disable=too-few-public-methods

    @abstractmethod
    def reverse_protocol_fee(self, trade: "OffchainTrade") -> "OffchainTrade":
        """Reverse application of protocol fee
        Returns a new trade object
        """


@dataclass
class OnchainTrade(Trade):
    """
    Class to describe onchain info about a trade.
    """


@dataclass
class OffchainTrade(Trade):
    """Class to describe offchain info about a trade."""

    # qute amounts are effective amounts, fees are handled before
    quote_sell_amount: int
    quote_buy_amount: int
    protocol_fees: list[ProtocolFee]

    def price_improvement(self) -> Fraction:
        """Compute price improvement"""
        if self.kind == "sell":
            return self.buy_amount - self.quote_buy_amount * Fraction(
                self.sell_amount, self.quote_sell_amount
            )
        if self.kind == "buy":
            return (
                self.quote_sell_amount
                * Fraction(self.buy_amount, self.quote_buy_amount)
                - self.sell_amount
            )
        raise ValueError(f"Order kind {self.kind} is invalid.")

    def reverse_protocol_fees(self) -> "OffchainTrade":
        """Compute protocol fees of a trade in the surplus token"""
        new_trade = deepcopy(self)
        for protocol_fee in reversed(self.protocol_fees):
            new_trade = protocol_fee.reverse_protocol_fee(new_trade)

        return new_trade

    def raw_surplus(self) -> Fraction:
        """Compute surplus as if there were no protocol fees"""
        new_trade = self.reverse_protocol_fees()
        return new_trade.surplus()


@dataclass
class OnchainSettlementData:
    """Class to describe onchain info about a settlement."""

    auction_id: int
    tx_hash: HexBytes
    solver: HexBytes
    call_data: HexBytes
    trades: list[OnchainTrade]


@dataclass
class OffchainSettlementData:
    """Class to describe offchain info about a settlement."""

    # pylint: disable=too-many-instance-attributes

    auction_id: int
    solver: HexBytes
    call_data: HexBytes
    trades: list[OffchainTrade]
    valid_orders: set[HexBytes]
    jit_order_addresses: set[HexBytes]
    native_prices: dict[HexBytes, int]
    clearing_prices: dict[HexBytes, int]


@dataclass
class VolumeFee(ProtocolFee):
    """Volume based protocol fee"""

    volume_factor: Fraction

    def reverse_protocol_fee(self, trade: OffchainTrade) -> OffchainTrade:
        new_trade = deepcopy(trade)
        volume = trade.volume()
        if trade.kind == "sell":
            fee = round(volume * self.volume_factor / (1 - self.volume_factor))
            new_trade.buy_amount = trade.buy_amount + fee
        elif trade.kind == "buy":
            fee = round(volume * self.volume_factor / (1 + self.volume_factor))
            new_trade.sell_amount = trade.sell_amount - fee
        else:
            raise ValueError(f"Order kind {trade.kind} is invalid.")
        return new_trade


@dataclass
class SurplusFee(ProtocolFee):
    """Surplus based protocol fee"""

    surplus_factor: Fraction
    surplus_max_volume_factor: Fraction

    def reverse_protocol_fee(self, trade: OffchainTrade) -> OffchainTrade:
        new_trade = deepcopy(trade)
        surplus = trade.surplus()
        volume = trade.volume()
        surplus_fee = round(surplus * self.surplus_factor / (1 - self.surplus_factor))
        if trade.kind == "sell":
            volume_fee = round(
                volume
                * self.surplus_max_volume_factor
                / (1 - self.surplus_max_volume_factor)
            )
            fee = min(surplus_fee, volume_fee)
            new_trade.buy_amount = trade.buy_amount + fee
        elif trade.kind == "buy":
            volume_fee = round(
                volume
                * self.surplus_max_volume_factor
                / (1 + self.surplus_max_volume_factor)
            )
            fee = min(surplus_fee, volume_fee)
            new_trade.sell_amount = trade.sell_amount - fee
        else:
            raise ValueError(f"Order kind {trade.kind} is invalid.")
        return new_trade


@dataclass
class PriceImprovementFee(ProtocolFee):
    """Price improvement based protocol fee"""

    price_improvement_factor: Fraction
    price_improvement_max_volume_factor: Fraction

    def reverse_protocol_fee(self, trade: OffchainTrade) -> OffchainTrade:
        new_trade = deepcopy(trade)
        price_improvement = trade.price_improvement()
        volume = trade.volume()
        price_improvement_fee = max(
            0,
            round(
                price_improvement
                * self.price_improvement_factor
                / (1 - self.price_improvement_factor)
            ),
        )
        if trade.kind == "sell":
            volume_fee = round(
                volume
                * self.price_improvement_max_volume_factor
                / (1 - self.price_improvement_max_volume_factor)
            )
            fee = min(price_improvement_fee, volume_fee)
            new_trade.buy_amount = trade.buy_amount + fee
        elif trade.kind == "buy":
            volume_fee = round(
                volume
                * self.price_improvement_max_volume_factor
                / (1 + self.price_improvement_max_volume_factor)
            )
            fee = min(price_improvement_fee, volume_fee)
            new_trade.sell_amount = trade.sell_amount - fee
        else:
            raise ValueError(f"Order kind {trade.kind} is invalid.")
        return new_trade
