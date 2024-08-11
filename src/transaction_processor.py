from typing import List, Tuple
from src.helper_classes.blockchain_data import BlockchainData
from src.helper_classes.database import Database
from src.imbalances_script import RawTokenImbalances
from src.price_providers.price_feed import PriceFeed
from src.helper_functions import read_sql_file
from src.config import CHAIN_SLEEP_TIME, logger
import time


class TransactionProcessor:
    """Class processes transactions for the slippage project."""

    def __init__(self, blockchain_data: BlockchainData, db: Database, chain_name: str):
        self.blockchain_data = blockchain_data
        self.db = db
        self.chain_name = chain_name
        self.imbalances = RawTokenImbalances(self.blockchain_data.web3, self.chain_name)
        self.price_providers = PriceFeed()
        self.log_message: List[str] = []

    def get_start_block(self) -> int:
        """
        Retrieve the most recent block already present in raw_token_imbalances table,
        delete entries for that block, and return this block number as start_block.
        If no entries are present, fallback to get_finalized_block_number().
        """
        try:
            # Query for the maximum block number
            query_max_block = read_sql_file("src/sql/select_max_block.sql")
            result = self.db.execute_query(
                query_max_block, {"chain_name": self.chain_name}
            )
            row = result.fetchone()
            max_block = row[0] if row is not None else None

            if max_block is not None:
                logger.debug("Fetched max block number from database: %d", max_block)

            # If no entries present, fallback to get_latest_block()
            if max_block is None:
                return self.blockchain_data.get_latest_block()

            # Delete entries for the max block from the table
            delete_sql = read_sql_file("src/sql/delete_entries_max_block.sql")
            self.db.execute_and_commit(
                delete_sql, {"chain_name": self.chain_name, "block_number": max_block}
            )
            logger.debug("Successfully deleted entries for block number: %s", max_block)

            return max_block
        except Exception as e:
            logger.error("Error accessing database: %s", e)
            return self.blockchain_data.get_latest_block()

    def process(self, start_block: int):
        """Main Daemon loop that finds imbalances for txs and prices."""
        previous_block = start_block
        unprocessed_txs: List[Tuple[str, int, int]] = []
        logger.info("%s Daemon started. Start block: %d", self.chain_name, start_block)

        while True:
            try:
                latest_block = self.blockchain_data.get_latest_block()
                print(previous_block, latest_block)
                new_txs = self.blockchain_data.fetch_tx_data(
                    previous_block, latest_block
                )
                all_txs = new_txs + unprocessed_txs
                unprocessed_txs.clear()

                for tx_hash, auction_id, block_number in all_txs:
                    try:
                        self.process_single_transaction(
                            tx_hash, auction_id, block_number
                        )
                    except Exception as e:
                        unprocessed_txs.append((tx_hash, auction_id, block_number))
                        logger.error(f"Error processing transaction {tx_hash}: {e}")

                previous_block = latest_block + 1
                time.sleep(CHAIN_SLEEP_TIME)

            except Exception as e:
                logger.error(f"Error in processing loop: {e}")
                time.sleep(CHAIN_SLEEP_TIME)

    def process_single_transaction(
        self, tx_hash: str, auction_id: int, block_number: int
    ):
        """Function processes a single tx to find imbalances, prices."""
        token_imbalances = self.imbalances.compute_imbalances(tx_hash)
        if token_imbalances is not None:
            self.log_message.clear()  # reset log message for each transaction
            self.log_message.append(
                f"Token Imbalances on {self.chain_name} for tx {tx_hash}:"
            )
            for token_address, imbalance in token_imbalances.items():
                if imbalance != 0:
                    self.write_token_imbalances(
                        tx_hash, auction_id, block_number, token_address, imbalance
                    )
                    self.write_prices_if_available(tx_hash, block_number, token_address)

                    self.log_message.append(
                        f"Token: {token_address}, Imbalance: {imbalance}"
                    )

            logger.info("\n".join(self.log_message))
        else:
            raise ValueError("Imbalances computation returned None.")

    def record_exists(self, tx_hash: bytes, token_address: bytes) -> bool:
        """
        Function checks if an entry of (tx_hash, token) already exists in the token imbalances table.
        """
        query = read_sql_file("src/sql/select_record_exists.sql")
        result = self.db.execute_query(
            query, {"tx_hash": tx_hash, "token_address": token_address}
        )
        return result.fetchone() is not None

    def write_token_imbalances(
        self,
        tx_hash: str,
        auction_id: int,
        block_number: int,
        token_address: str,
        imbalance: float,
    ):
        """Function attempts to write token imbalances to the table."""
        tx_hash_bytes = bytes.fromhex(tx_hash[2:])
        token_address_bytes = bytes.fromhex(token_address[2:])

        if not self.record_exists(tx_hash_bytes, token_address_bytes):
            query = read_sql_file("src/sql/insert_raw_token_imbalances.sql")
            self.db.execute_and_commit(
                query,
                {
                    "auction_id": auction_id,
                    "chain_name": self.chain_name,
                    "block_number": block_number,
                    "tx_hash": tx_hash_bytes,
                    "token_address": token_address_bytes,
                    "imbalance": imbalance,
                },
            )

    def write_prices_if_available(
        self, tx_hash: str, block_number: int, token_address: str
    ):
        """Function checks if price data can be fetched for writing to table."""
        price_data = self.price_providers.get_price(block_number, token_address)
        if price_data:
            price, source = price_data
            self.write_prices(source, block_number, tx_hash, token_address, price)
            self.log_message.append(f"Token: {token_address}, Price: {price} ETH")

    def write_prices(
        self,
        source: str,
        block_number: int,
        tx_hash: str,
        token_address: str,
        price: float,
    ):
        """Function attempts to write price data to the table."""
        tx_hash_bytes = bytes.fromhex(tx_hash[2:])
        token_address_bytes = bytes.fromhex(token_address[2:])

        query = read_sql_file("src/sql/insert_price.sql")
        self.db.execute_and_commit(
            query,
            {
                "chain_name": self.chain_name,
                "source": source,
                "block_number": block_number,
                "tx_hash": tx_hash_bytes,
                "token_address": token_address_bytes,
                "price": price,
            },
        )
