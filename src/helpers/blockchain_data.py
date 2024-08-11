from web3 import Web3
from src.helpers.helper_functions import get_tx_hashes_blocks, get_auction_id
from src.helpers.config import logger


class BlockchainData:
    def __init__(self, web3: Web3):
        self.web3 = web3

    def get_latest_block(self) -> int:
        """Returns finalized block number."""
        return self.web3.eth.block_number - 67

    def fetch_tx_data(self, start_block: int, end_block: int):
        """
        Fetch transaction data beginning from start_block to end_block.
        Returns (tx_hash, auction_id, block_number) as a tuple.
        """
        tx_data = []
        tx_hashes_blocks = get_tx_hashes_blocks(self.web3, start_block, end_block)

        for tx_hash, block_number in tx_hashes_blocks:
            try:
                auction_id = get_auction_id(self.web3, tx_hash)
                tx_data.append((tx_hash, auction_id, block_number))
            except Exception as e:
                logger.error(f"Error fetching auction ID for {tx_hash}: {e}")

        return tx_data
