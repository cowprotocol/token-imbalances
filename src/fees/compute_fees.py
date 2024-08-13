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
from requests.exceptions import RequestException
from web3 import Web3
from web3.logs import DISCARD
from web3.types import TxData, TxReceipt, EventData

from src.constants import (
    SETTLEMENT_CONTRACT_ADDRESS,
    REQUEST_TIMEOUT,
)
from contracts.gpv2_settlement_abi import gpv2_settlement_abi

import requests

# types for trades


@dataclass
class Trade:
    """Class for"""

    order_uid: HexBytes
    sell_amount: int
    buy_amount: int
    owner: HexBytes
    sell_token: HexBytes
    buy_token: HexBytes
    limit_sell_amount: int
    limit_buy_amount: int
    kind: str
    sell_token_clearing_price: int
    buy_token_clearing_price: int

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

    def raw_surplus(self, fee_policies: list["FeePolicy"]) -> int:
        """Compute raw surplus of a trade in the surplus token
        First, the application of protocol fees is reversed. Then, surplus of the resulting trade
        is computed."""
        raw_trade = deepcopy(self)
        for fee_policy in reversed(fee_policies):
            raw_trade = fee_policy.reverse_protocol_fee(raw_trade)
        return raw_trade.surplus()

    def protocol_fee(self, fee_policies):
        """Compute protocol fees of a trade in the surplus token
        Protocol fees are computed as the difference of raw surplus and surplus."""

        return self.raw_surplus(fee_policies) - self.surplus()

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
class OnchainSettlementData:
    """Class to describe onchain info about a settlement."""

    auction_id: int
    tx_hash: HexBytes
    solver: HexBytes
    call_data: HexBytes
    trades: list[Trade]


@dataclass
class OffchainSettlementData:
    """Class to describe offchain info about a settlement."""

    # pylint: disable=too-many-instance-attributes

    auction_id: int
    solver: HexBytes
    call_data: HexBytes
    trade_fee_policies: dict[HexBytes, list[FeePolicy]]
    score: int
    valid_orders: set[HexBytes]
    jit_order_addresses: set[HexBytes]
    native_prices: dict[HexBytes, int]


# fetching data


class BlockchainFetcher:
    """
    Class to connect to a node and fetch/process onchain data.
    """

    def __init__(self) -> None:
        load_dotenv()

        node_url = os.getenv("NODE_URL")
        self.node = Web3(Web3.HTTPProvider(node_url))

        self.contract = self.node.eth.contract(
            address=Address(HexBytes(SETTLEMENT_CONTRACT_ADDRESS)),
            abi=gpv2_settlement_abi,
        )

    def get_onchain_data(self, tx_hash: HexBytes) -> OnchainSettlementData:
        """
        This function can error since nodes are called.
        """
        transaction = self.node.eth.get_transaction(tx_hash)
        receipt = self.node.eth.wait_for_transaction_receipt(tx_hash)
        decoded_data = self.decode_data(transaction, receipt)
        return decoded_data

    def decode_data(
        self, transaction: TxData, receipt: TxReceipt
    ) -> OnchainSettlementData:
        """
        Method that decodes a tx and returns a summary of this decoding.
        """
        tx_hash = transaction["hash"]
        call_data = transaction["input"]

        auction_id = int.from_bytes(call_data[-8:])

        settlement_event = self.contract.events.Settlement().process_receipt(
            receipt, errors=DISCARD
        )[0]
        solver = HexBytes(settlement_event["args"]["solver"])
        trade_events: tuple[EventData] = self.contract.events.Trade().process_receipt(
            receipt, errors=DISCARD
        )

        settlement = self.contract.decode_function_input(call_data)[1]

        tokens = settlement["tokens"]
        prices = settlement["clearingPrices"]

        trades: list[Trade] = []
        for trade_event, settlement_trade in zip(trade_events, settlement["trades"]):
            sell_token_address = HexBytes(tokens[settlement_trade["sellTokenIndex"]])
            buy_token_address = HexBytes(tokens[settlement_trade["buyTokenIndex"]])
            sell_token_clearing_price = prices[
                tokens.index(tokens[settlement_trade["sellTokenIndex"]])
            ]
            buy_token_clearing_price = prices[
                tokens.index(tokens[settlement_trade["buyTokenIndex"]])
            ]
            trade = Trade(
                HexBytes(trade_event["args"]["orderUid"]),
                trade_event["args"]["sellAmount"],
                trade_event["args"]["buyAmount"],
                HexBytes(trade_event["args"]["owner"]),
                sell_token_address,
                buy_token_address,
                settlement_trade["sellAmount"],
                settlement_trade["buyAmount"],
                "sell" if settlement_trade["flags"] % 2 == 0 else "buy",
                sell_token_clearing_price,
                buy_token_clearing_price,
            )
            trades.append(trade)

        return OnchainSettlementData(auction_id, tx_hash, solver, call_data, trades)


class OrderbookAWSFetcher:
    """
    This is a class for connecting to the db, and contains a few functions that
    fetch necessary data to run the checks that we need.
    """

    def __init__(self) -> None:
        load_dotenv()
        network = os.getenv("NETWORK")

        self.orderbook_urls = {
            "prod": f"https://api.cow.fi/{network}/api/v1/",
            "barn": f"https://barn.api.cow.fi/{network}/api/v1/",
        }
        self.aws_urls = {
            "prod": "https://solver-instances.s3.eu-central-1.amazonaws.com/"
            f"prod/{network}/autopilot/",
            "barn": "https://solver-instances.s3.eu-central-1.amazonaws.com/"
            f"staging/{network}/autopilot/",
        }

    def get_offchain_data(
        self, onchain_data: OnchainSettlementData
    ) -> OffchainSettlementData:
        """
        Method that fetches all necessary data from the API.
        """
        solver = onchain_data.solver
        auction_id = onchain_data.auction_id

        solution_data, environment = self.get_solution_data(auction_id, solver)
        auction_data = self.get_auction_data(auction_id, environment)

        offchain_data = self.convert_to_offchain_data(
            onchain_data,
            auction_data,
            solution_data,
        )
        return offchain_data

    def convert_to_offchain_data(
        self,
        onchain_data: OnchainSettlementData,
        auction_data: dict[str, Any],
        solution_data: dict[str, Any],
    ) -> OffchainSettlementData:
        """Turn Row from database query into OffchainSettlementData"""
        # pylint: disable=too-many-locals
        auction_id = onchain_data.auction_id

        solver = HexBytes(solution_data["solverAddress"])
        call_data = HexBytes(solution_data["callData"])

        trade_fee_policies: dict[HexBytes, list[FeePolicy]] = {}
        onchain_trades_dict = {trade.order_uid: trade for trade in onchain_data.trades}
        protocol_fees_dict = {
            HexBytes(order["uid"]): order["protocolFees"]
            for order in auction_data["orders"]
            if HexBytes(order["uid"]) in onchain_trades_dict
        }
        for order in solution_data["orders"]:
            order_uid = HexBytes(order["id"])

            fee_policies = self.parse_fee_policies(
                protocol_fees_dict.get(order_uid, [])
            )

            trade_fee_policies[order_uid] = fee_policies

        score = int(solution_data["score"])
        valid_orders = {HexBytes(order["uid"]) for order in auction_data["orders"]}
        native_prices = {
            HexBytes(address): int(price)
            for address, price in auction_data["prices"].items()
        }
        jit_order_addresses = {
            HexBytes(address)
            for address in auction_data["surplusCapturingJitOrderOwners"]
        }

        return OffchainSettlementData(
            auction_id,
            solver,
            call_data,
            trade_fee_policies,
            score,
            valid_orders,
            jit_order_addresses,
            native_prices,
        )

    def get_solution_data(
        self, auction_id: int, solver: HexBytes
    ) -> tuple[dict[str, Any], str]:
        """Fetch competition data from the database"""
        for environment, url in self.orderbook_urls.items():
            try:
                response = requests.get(
                    url + f"solver_competition/{auction_id}",
                    timeout=REQUEST_TIMEOUT,
                )
                response.raise_for_status()
                solution_data = response.json()["solutions"][-1]
                if HexBytes(solution_data["solverAddress"]) == solver:
                    return solution_data, environment
            except requests.exceptions.HTTPError as err:
                if err.response.status_code == 404:
                    pass
        raise ConnectionError(f"Error fetching off-chain data for id {auction_id}")

    def get_auction_data(
        self,
        auction_id: int,
        environment: str,
    ) -> dict[str, Any]:
        """Fetch auction data from AWS."""
        url = self.aws_urls[environment] + f"{auction_id}.json"
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        auction_data: dict[str, Any] = response.json()
        return auction_data

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


def fetch_settlement_data(
    tx_hash: HexBytes,
) -> tuple[OnchainSettlementData, OffchainSettlementData]:
    onchain_fetcher = BlockchainFetcher()
    offchain_fetcher = OrderbookAWSFetcher()

    onchain_data = onchain_fetcher.get_onchain_data(tx_hash)
    offchain_data = offchain_fetcher.get_offchain_data(onchain_data)

    return onchain_data, offchain_data


# computing fees


def compute_fee_imbalances(
    onchain_data: OnchainSettlementData, offchain_data: OffchainSettlementData
) -> tuple[dict[HexBytes, int], dict[HexBytes, int]]:
    protocol_fees: dict[HexBytes, int] = {}
    network_fees: dict[HexBytes, int] = {}
    for trade in onchain_data.trades:
        # protocol fees
        fee_policies = offchain_data.trade_fee_policies[trade.order_uid]
        protocol_fee_amount = trade.protocol_fee(fee_policies)
        protocol_fee_token = trade.surplus_token()
        protocol_fees[protocol_fee_token] = protocol_fee_amount

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

        network_fees[trade.sell_token] = network_fee_sell

    return protocol_fees, network_fees


# combined function


def batch_fee_imbalances(
    tx_hash: HexBytes,
) -> tuple[dict[HexBytes, int], dict[HexBytes, int]]:
    onchain_data, offchain_data = fetch_settlement_data(tx_hash)
    protocol_fees, network_fees = compute_fee_imbalances(onchain_data, offchain_data)
    return protocol_fees, network_fees


if __name__ == "__main__":
    tx_hash = HexBytes(
        "0xbd8cf4a21ad811cc3b9e49cff5e95563c3c2651b0ea41e0f8a7987818205c984"
    )
    protocol_fees, network_fees = batch_fee_imbalances(tx_hash)
