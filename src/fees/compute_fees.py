from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass
from fractions import Fraction
import math
import os
from typing import Any
from dotenv import load_dotenv
from eth_typing import Address
from hexbytes import HexBytes

from src.constants import REQUEST_TIMEOUT, NULL_ADDRESS
import requests
import json

# types for trades


@dataclass
class Trade:
    """Class for"""

    order_uid: HexBytes
    sell_amount: int
    buy_amount: int
    sell_token: HexBytes
    buy_token: HexBytes
    limit_sell_amount: int
    limit_buy_amount: int
    kind: str
    sell_token_clearing_price: int
    buy_token_clearing_price: int
    fee_policies: list["FeePolicy"]
    partner_fee_recipient: HexBytes  # if there is no partner, then its value is set to the null address
    network_fee: int
    protocol_fee: int
    partner_fee: int

    def volume(self) -> int:
        """Compute volume of a trade in the surplus token"""
        if self.kind == "sell":
            return self.buy_amount
        if self.kind == "buy":
            return self.sell_amount
        raise ValueError(f"Order kind {self.kind} is invalid.")

    def surplus(self) -> int:
        """Compute surplus of a trade in the surplus token
        For partially fillable orders, rounding is such that the reference for computing surplus is
        such that it gives the worst price still allowed by the smart contract. That means that for
        sell orders the limit buy amount is rounded up and for buy orders the limit sell amount is
        rounded down.
        """
        if self.kind == "sell":
            current_limit_buy_amount = math.ceil(
                self.limit_buy_amount
                * Fraction(self.sell_amount, self.limit_sell_amount)
            )
            return self.buy_amount - current_limit_buy_amount
        if self.kind == "buy":
            current_limit_sell_amount = int(
                self.limit_sell_amount
                * Fraction(self.buy_amount, self.limit_buy_amount)
            )
            return current_limit_sell_amount - self.sell_amount
        raise ValueError(f"Order kind {self.kind} is invalid.")

    def raw_surplus(self) -> int:
        """Compute raw surplus of a trade in the surplus token
        First, the application of protocol fees is reversed. Then, surplus of the resulting trade
        is computed."""
        raw_trade = deepcopy(self)
        i = 0
        self.protocol_fee = 0
        self.partner_fee = 0
        if self.fee_policies == []:
            return self.surplus()
        for fee_policy in reversed(self.fee_policies):
            raw_trade = fee_policy.reverse_protocol_fee(raw_trade)
            ## we assume that partner fee is the last to be applied
            if i == 0 and self.partner_fee_recipient is not NULL_ADDRESS:
                self.partner_fee = raw_trade.surplus() - self.surplus()
            i = i + 1
        self.protocol_fee = raw_trade.surplus() - self.surplus() - self.partner_fee()
        return raw_trade.surplus()

    def protocol_fee(self):
        """Compute protocol fees of a trade in the surplus token
        Protocol fees are computed as the difference of raw surplus and surplus."""

        return self.raw_surplus() - self.surplus()

    def surplus_token(self) -> HexBytes:
        """Returns the surplus token"""
        if self.kind == "sell":
            return self.buy_token
        if self.kind == "buy":
            return self.sell_token
        raise ValueError(f"Order kind {self.kind} is invalid.")

    def price_improvement(self, quote: "Quote") -> int:
        """Compute price improvement
        For partially fillable orders, rounding is such that the reference for computing price
        improvement is as if the quote would determine the limit price. That means that for sell
        orders the quote buy amount is rounded up and for buy orders the quote sell amount is
        rounded down.
        """
        effective_sell_amount = quote.effective_sell_amount(self.kind)
        effective_buy_amount = quote.effective_buy_amount(self.kind)
        if self.kind == "sell":
            current_limit_quote_amount = math.ceil(
                effective_buy_amount * Fraction(self.sell_amount, effective_sell_amount)
            )
            return self.buy_amount - current_limit_quote_amount
        if self.kind == "buy":
            current_quote_sell_amount = int(
                effective_sell_amount * Fraction(self.buy_amount, effective_buy_amount)
            )
            return current_quote_sell_amount - self.sell_amount
        raise ValueError(f"Order kind {self.kind} is invalid.")

    def compute_surplus_fee(self) -> int:
        if self.kind == "sell":
            buy_amount_clearing_prices = math.ceil(
                self.sell_amount
                * Fraction(
                    self.sell_token_clearing_price, self.buy_token_clearing_price
                )
            )
            return buy_amount_clearing_prices - self.buy_amount
        if self.kind == "buy":
            sell_amount_clearing_prices = int(
                self.buy_amount
                * Fraction(
                    self.buy_token_clearing_price, self.sell_token_clearing_price
                )
            )
            return self.sell_amount - sell_amount_clearing_prices
        raise ValueError(f"Order kind {self.kind} is invalid.")


# types for protocol fees


class FeePolicy(ABC):
    """Abstract class for protocol fees
    Concrete implementations have to implement a reverse_protocol_fee method.
    """

    # pylint: disable=too-few-public-methods

    @abstractmethod
    def reverse_protocol_fee(self, trade: Trade) -> Trade:
        """Reverse application of protocol fee
        Returns a new trade object
        """


@dataclass
class VolumeFeePolicy(FeePolicy):
    """Volume based protocol fee"""

    volume_factor: Fraction

    def reverse_protocol_fee(self, trade: Trade) -> Trade:
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
class SurplusFeePolicy(FeePolicy):
    """Surplus based protocol fee"""

    surplus_factor: Fraction
    surplus_max_volume_factor: Fraction

    def reverse_protocol_fee(self, trade: Trade) -> Trade:
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
class Quote:
    """Class representing quotes"""

    sell_amount: int
    buy_amount: int
    fee_amount: int

    def effective_sell_amount(self, kind: str) -> int:
        if kind == "sell":
            return self.sell_amount
        if kind == "buy":
            return self.sell_amount + self.fee_amount
        raise ValueError(f"Order kind {kind} is invalid.")

    def effective_buy_amount(self, kind: str) -> int:
        if kind == "sell":
            exchange_rate = Fraction(self.buy_amount, self.sell_amount)
            return math.ceil((self.sell_amount - self.fee_amount) * exchange_rate)
        if kind == "buy":
            return self.buy_amount
        raise ValueError(f"Order kind {kind} is invalid.")


@dataclass
class PriceImprovementFeePolicy(FeePolicy):
    """Price improvement based protocol fee"""

    price_improvement_factor: Fraction
    price_improvement_max_volume_factor: Fraction
    quote: Quote

    def reverse_protocol_fee(self, trade: Trade) -> Trade:
        new_trade = deepcopy(trade)
        price_improvement = trade.price_improvement(self.quote)
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


@dataclass
class SettlementData:
    """Class to describe info about a settlement."""

    # pylint: disable=too-many-instance-attributes

    auction_id: int
    tx_hash: HexBytes
    solver: HexBytes
    trades: list[Trade]
    native_prices: dict[HexBytes, int]


# fetching data


class OrderbookFetcher:
    """
    This is a class for connecting to the orderbook api, and contains a few functions that
    fetch necessary data to run the checks that we need.
    """

    def __init__(self) -> None:
        load_dotenv()
        chain_name = os.getenv("CHAIN_NAME")

        self.orderbook_urls = {
            "prod": f"https://api.cow.fi/{chain_name}/api/v1/",
            "barn": f"https://barn.api.cow.fi/{chain_name}/api/v1/",
        }

    def get_all_data(self, tx_hash: HexBytes) -> SettlementData:
        """
        Method that fetches all necessary data from the API.
        """
        endpoint_data, environment = self.get_auction_data(tx_hash)

        solutions = endpoint_data["solutions"]
        # here we detect the winning solution
        for sol in solutions:
            if sol["ranking"] == 1:
                winning_sol = sol

        auction_id = endpoint_data["auctionId"]
        solver = HexBytes(winning_sol["solverAddress"])

        executed_orders = [
            (HexBytes(order["id"]), int(order["sellAmount"]), int(order["buyAmount"]))
            for order in winning_sol["orders"]
        ]
        clearing_prices = {
            HexBytes(address): int(price)
            for address, price in winning_sol["clearingPrices"].items()
        }
        native_prices = {
            address: int(endpoint_data["auction"]["prices"][address.to_0x_hex()])
            for address, _ in clearing_prices.items()
        }
        trades = []
        for uid, executed_sell_amount, executed_buy_amount in executed_orders:
            order_data = self.get_order_data(uid, environment)
            if order_data == None:
                # this can only happen for now if the order is a jit CoW AMM order
                continue
            trade_data = self.get_trade_data(uid, tx_hash, environment)

            kind = order_data["kind"]
            sell_token = HexBytes(order_data["sellToken"])
            buy_token = HexBytes(order_data["buyToken"])
            limit_sell_amount = int(order_data["sellAmount"])
            limit_buy_amount = int(order_data["buyAmount"])
            sell_token_clearing_price = clearing_prices[sell_token]
            buy_token_clearing_price = clearing_prices[buy_token]
            fee_policies = self.parse_fee_policies(trade_data["feePolicies"])

            app_data = json.loads(order_data["fullAppData"])
            if "partnerFee" in app_data["metadata"].keys():
                partner_fee_recipient = HexBytes(
                    app_data["metadata"]["partnerFee"]["recipient"]
                )
            else:
                partner_fee_recipient = NULL_ADDRESS

            trade = Trade(
                order_uid=uid,
                sell_amount=executed_sell_amount,
                buy_amount=executed_buy_amount,
                sell_token=sell_token,
                buy_token=buy_token,
                limit_sell_amount=limit_sell_amount,
                limit_buy_amount=limit_buy_amount,
                kind=kind,
                sell_token_clearing_price=sell_token_clearing_price,
                buy_token_clearing_price=buy_token_clearing_price,
                fee_policies=fee_policies,
                partner_fee_recipient=partner_fee_recipient,
                network_fee=-1,  # this is to signal the entry is not yet computed
                protocol_fee=-1,  # this is to signal the entry is not yet computed
                partner_fee=-1,  # this is to signal the entry is not yet computed
            )
            trades.append(trade)

        settlement_data = SettlementData(
            auction_id=auction_id,
            tx_hash=tx_hash,
            solver=solver,
            trades=trades,
            native_prices=native_prices,
        )
        return settlement_data

    def get_auction_data(self, tx_hash: HexBytes):
        for environment, url in self.orderbook_urls.items():
            try:
                response = requests.get(
                    url + f"solver_competition/by_tx_hash/{tx_hash.to_0x_hex()}",
                    timeout=REQUEST_TIMEOUT,
                )
                response.raise_for_status()
                auction_data = response.json()
                return auction_data, environment
            except requests.exceptions.HTTPError as err:
                if err.response.status_code == 404:
                    pass
        raise ConnectionError(
            f"Error fetching off-chain data for tx {tx_hash.to_0x_hex()}"
        )

    def get_order_data(self, uid: HexBytes, environment: str):
        prefix = self.orderbook_urls[environment]
        url = prefix + f"orders/{uid.to_0x_hex()}"
        response = requests.get(
            url,
            timeout=REQUEST_TIMEOUT,
        )
        if response.ok == False:
            # jit CoW AMM detected
            return None
        order_data = response.json()
        return order_data

    def get_trade_data(self, uid: HexBytes, tx_hash: HexBytes, environment: str):
        prefix = self.orderbook_urls[environment]
        url = prefix + f"trades?orderUid={uid.to_0x_hex()}"
        response = requests.get(url)
        trade_data_temp = response.json()
        for t in trade_data_temp:
            if HexBytes(t["txHash"]) == tx_hash:
                trade_data = t
                break
        return trade_data

    def parse_fee_policies(
        self, protocol_fee_datum: list[dict[str, Any]]
    ) -> list[FeePolicy]:
        """Pase protocol fees into sorted list"""
        fee_policies: list[FeePolicy] = []
        for fee_policy in protocol_fee_datum:
            if "surplus" in fee_policy:
                fee_policies.append(
                    SurplusFeePolicy(
                        Fraction(fee_policy["surplus"]["factor"]),
                        Fraction(fee_policy["surplus"]["maxVolumeFactor"]),
                    )
                )
            elif "volume" in fee_policy:
                fee_policies.append(
                    VolumeFeePolicy(Fraction(fee_policy["volume"]["factor"]))
                )
            elif "priceImprovement" in fee_policy:
                quote = Quote(
                    int(fee_policy["priceImprovement"]["quote"]["sellAmount"]),
                    int(fee_policy["priceImprovement"]["quote"]["buyAmount"]),
                    int(fee_policy["priceImprovement"]["quote"]["fee"]),
                )
                fee_policies.append(
                    PriceImprovementFeePolicy(
                        Fraction(fee_policy["priceImprovement"]["factor"]),
                        Fraction(fee_policy["priceImprovement"]["maxVolumeFactor"]),
                        quote,
                    )
                )
            else:
                raise ValueError(f"Fee kind {fee_policy.keys()} is invalid.")
        return fee_policies


# computing fees
def compute_fee_imbalances(
    settlement_data: SettlementData,
) -> tuple[dict[str, tuple[str, int]], dict[str, tuple[str, int]]]:
    protocol_fees: dict[str, tuple[str, int]] = {}
    network_fees: dict[str, tuple[str, int]] = {}
    for trade in settlement_data.trades:
        # protocol fees
        protocol_fee_amount = trade.protocol_fee()
        protocol_fee_token = trade.surplus_token()
        protocol_fees[trade.order_uid.to_0x_hex()] = (
            protocol_fee_token.to_0x_hex(),
            protocol_fee_amount,
        )
        # network fees
        surplus_fee = trade.compute_surplus_fee()  # in the surplus token
        network_fee = surplus_fee - protocol_fee_amount
        if trade.kind == "sell":
            network_fee_sell = int(
                network_fee
                * Fraction(
                    trade.buy_token_clearing_price, trade.sell_token_clearing_price
                )
            )
        else:
            network_fee_sell = network_fee
        trade.network_fee = network_fee_sell
        network_fees[trade.order_uid.to_0x_hex()] = (
            trade.sell_token.to_0x_hex(),
            network_fee_sell,
        )

    return protocol_fees, network_fees


# combined function


def batch_fee_imbalances(
    tx_hash: HexBytes,
) -> tuple[dict[str, tuple[str, int]], dict[str, tuple[str, int]]]:
    orderbook_api = OrderbookFetcher()
    settlement_data = orderbook_api.get_all_data(tx_hash)
    protocol_fees, network_fees = compute_fee_imbalances(settlement_data)
    return protocol_fees, network_fees
