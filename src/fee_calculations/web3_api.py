"""
Class to connect to a node and fetch/process onchain data.
"""

# pylint: disable=logging-fstring-interpolation
from os import getenv
from dotenv import load_dotenv

from eth_typing import Address
from hexbytes import HexBytes
from web3 import Web3
from web3.exceptions import BlockNotFound
from web3.logs import DISCARD
from web3.types import TxData, TxParams, TxReceipt, EventData

from src.fee_calculations.constants import (
    SETTLEMENT_CONTRACT_ADDRESS,

)
from src.fee_calculations.contracts.gpv2settlement import gpv2_settlement
from src.fee_calculations.contracts.gpv2_authenticator import gpv2_authenticator
from src.fee_calculations.contracts.zodiac_module import zodiac_module
from src.fee_calculations.exceptions import MissingOnchainData, InvalidSettlement, WhitelistedSolver
from src.fee_calculations.logger import logger
from src.fee_calculations.models import OnchainTrade, OnchainSettlementData


class Blockchain:
    """
    Class to connect to a node and fetch/process onchain data.
    """

    def __init__(self) -> None:
        load_dotenv()

        node_url = getenv("NODE_URL")
        self.node = Web3(Web3.HTTPProvider(node_url))

        logger.info("Established connection to node.")

        self.contract = self.node.eth.contract(
            address=Address(HexBytes(SETTLEMENT_CONTRACT_ADDRESS)), abi=gpv2_settlement
        )

    def get_latest_block_num(self) -> int:
        """
        Method that computes the latest block the node has "seen".
        """
        try:
            return self.node.eth.get_block_number()
        except ConnectionError as e:
            raise ConnectionError(
                "Latest block unknown. No block number fetched."
            ) from e

    def get_onchain_data(self, tx_hash: HexBytes) -> OnchainSettlementData:
        """
        This function can error since nodes are called.
        """
        transaction = self.node.eth.get_transaction(tx_hash)
        receipt = self.node.eth.wait_for_transaction_receipt(tx_hash)
        decoded_data = self.decode_data(transaction, receipt)
        return decoded_data

    def scan_blocks(self, start_block: int, end_block: int) -> list[HexBytes]:
        """
        Method that computes the relevant hashes that need to be inspected
        within a block range.
        """
        settlement_logs = self.contract.events.Settlement().get_logs(  # type: ignore
            fromBlock=start_block, toBlock=end_block
        )
        tx_hashes = [log["transactionHash"] for log in settlement_logs]
        return list(set(tx_hashes))

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

        try:
            settlement = self.contract.decode_function_input(call_data)[1]
        except ValueError as e:
            raise InvalidSettlement(
                f"Calldata cannot be decoded for transaction {tx_hash!r}",
                solver=solver,
            ) from e

        tokens = settlement["tokens"]

        trades = [
            OnchainTrade(
                HexBytes(trade_event["args"]["orderUid"]),
                HexBytes(trade_event["args"]["owner"]),
                HexBytes(tokens[settlement_trade["sellTokenIndex"]]),
                HexBytes(tokens[settlement_trade["buyTokenIndex"]]),
                trade_event["args"]["sellAmount"],
                trade_event["args"]["buyAmount"],
                settlement_trade["sellAmount"],
                settlement_trade["buyAmount"],
                "sell" if settlement_trade["flags"] % 2 == 0 else "buy",
            )
            for trade_event, settlement_trade in zip(trade_events, settlement["trades"])
        ]

        return OnchainSettlementData(auction_id, tx_hash, solver, call_data, trades)

    def get_block_time(self, block_num: int) -> int:
        """
        Method computes the timestamp of a block.
        """
        try:
            block = self.node.eth.get_block(block_num, False)
        except BlockNotFound as e:
            raise MissingOnchainData(f"Error fetching block {block_num}") from e
        return block["timestamp"]
