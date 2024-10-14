from hexbytes import HexBytes
from web3 import Web3
from web3.types import HexStr

from contracts.erc20_abi import erc20_abi
from src.helpers.config import logger
from src.constants import SETTLEMENT_CONTRACT_ADDRESS, INVALIDATED_ORDER_TOPIC


class BlockchainData:
    """Class provides functions for fetching blockchain data."""

    def __init__(self, web3: Web3):
        self.web3 = web3

    def get_latest_block(self) -> int:
        """Returns finalized block number."""
        return self.web3.eth.block_number - 67

    def fetch_tx_data(
        self, start_block: int, end_block: int
    ) -> list[tuple[str, int, int]]:
        """
        Fetch transaction data beginning from start_block to end_block.
        Returns (tx_hash, auction_id, block_number) as a tuple.
        """
        tx_data = []
        tx_hashes_blocks = self.get_tx_hashes_blocks(start_block, end_block)

        for tx_hash, block_number in tx_hashes_blocks:
            try:
                auction_id = self.get_auction_id(tx_hash)
                tx_data.append((tx_hash, auction_id, block_number))
            except Exception as e:
                logger.error(f"Error fetching auction ID for {tx_hash}: {e}")

        return tx_data

    def get_tx_hashes_blocks(
        self, start_block: int, end_block: int
    ) -> list[tuple[str, int]]:
        """
        Get all transaction hashes appended with corresponding block (tuple) transactions
        involving the settlement contract.
        """
        tx_hashes_blocks = []
        for block_number in range(start_block, end_block + 1):
            block = self.web3.eth.get_block(block_number, full_transactions=True)
            for tx in block.transactions:  # type: ignore[attr-defined]
                if tx.to and tx.to.lower() == SETTLEMENT_CONTRACT_ADDRESS.lower():
                    receipt = self.web3.eth.get_transaction_receipt(tx.hash)
                    # ignore txs that trigger the OrderInvalidated event
                    if any(
                        log.topics[0].to_0x_hex() == INVALIDATED_ORDER_TOPIC
                        for log in receipt.logs  # type: ignore[attr-defined]
                        if log.topics  # type: ignore[attr-defined]
                    ):
                        continue
                    # status = 0 indicates a reverted tx, status = 1 is successful tx
                    if receipt.status == 1:  # type: ignore[attr-defined]
                        tx_hashes_blocks.append((tx.hash.to_0x_hex(), block_number))
        return tx_hashes_blocks

    def get_auction_id(self, tx_hash: str) -> int:
        """
        Method that finds an auction id given a transaction hash.
        """
        transaction = self.web3.eth.get_transaction(HexBytes(tx_hash))
        call_data = transaction["input"]
        # convert call_data to hexString if it's in hexBytes
        call_data_bytes = bytes.fromhex(
            call_data.hex()[2:] if isinstance(call_data, HexBytes) else call_data[2:]
        )
        # convert bytes to int
        auction_id = int.from_bytes(call_data_bytes[-8:], byteorder="big")
        return auction_id

    def get_transaction_timestamp(self, tx_hash: str) -> tuple[str, int]:
        receipt = self.web3.eth.get_transaction_receipt(HexStr(tx_hash))
        block_number = receipt["blockNumber"]
        block = self.web3.eth.get_block(block_number)
        timestamp = block["timestamp"]

        return tx_hash, timestamp

    def get_transaction_tokens(self, tx_hash: str) -> list[tuple[str, str]]:
        receipt = self.web3.eth.get_transaction_receipt(HexStr(tx_hash))

        transfer_topic = self.web3.keccak(text="Transfer(address,address,uint256)")

        token_addresses: set[str] = set()
        for log in receipt["logs"]:
            if log["topics"] and log["topics"][0] == transfer_topic:
                token_address = log["address"]
                token_addresses.add(token_address)

        return [(tx_hash, token_address) for token_address in token_addresses]

    def get_token_decimals(self, token_address: str) -> int:
        """Get number of decimals for a token."""
        contract = self.web3.eth.contract(
            address=Web3.to_checksum_address(token_address), abi=erc20_abi
        )
        return contract.functions.decimals().call()
