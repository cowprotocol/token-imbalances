from hexbytes import HexBytes
from web3 import Web3
from src.helpers.config import logger
from src.constants import SETTLEMENT_CONTRACT_ADDRESS


class BlockchainData:
    """ Class provides functions for fetching blockchain data. """
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
                    tx_hashes_blocks.append((tx.hash.hex(), block_number))
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
