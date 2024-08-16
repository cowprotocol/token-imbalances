from src.helpers.blockchain_data import BlockchainData
from src.helpers.database import Database
from src.imbalances_script import RawTokenImbalances
from src.price_providers.price_feed import PriceFeed
from src.helpers.helper_functions import read_sql_file
from src.helpers.config import CHAIN_SLEEP_TIME, logger
import time


class TransactionProcessor:
    """Class processes transactions for the slippage project."""

    def __init__(self, blockchain_data: BlockchainData, db: Database, chain_name: str):
        self.blockchain_data = blockchain_data
        self.db = db
        self.chain_name = chain_name
        self.imbalances = RawTokenImbalances(self.blockchain_data.web3, self.chain_name)
        self.price_providers = PriceFeed()

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

            # If no entries present, fallback to get_latest_block()
            if max_block is None:
                return self.blockchain_data.get_latest_block()

            logger.info("Fetched max block number from database: %d", max_block)

            # Delete entries for the max block from the table
            delete_sql = read_sql_file("src/sql/delete_entries_max_block.sql")
            self.db.execute_and_commit(
                delete_sql, {"chain_name": self.chain_name, "block_number": max_block}
            )
            return max_block
        except Exception as e:
            logger.error("Error fetching start block from database: %s", e)
            raise

    def process(self, start_block: int) -> None:
        """Main Daemon loop that finds imbalances for txs and prices."""
        previous_block = start_block
        unprocessed_txs: list[tuple[str, int, int]] = []
        logger.info("%s daemon started. Start block: %d", self.chain_name, start_block)

        while True:
            try:
                latest_block = self.blockchain_data.get_latest_block()
                # new_txs = self.blockchain_data.fetch_tx_data(
                #     previous_block, latest_block
                # )
                new_txs = self.blockchain_data.fetch_tx_data(20537440, 20537940)
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
        try:
            token_imbalances = self.imbalances.compute_imbalances(tx_hash)
        except Exception as e:
            logger.error(f"Failed to compute imbalances for transaction {tx_hash}: {e}")
            return

        log_message: list[str] = []
        log_message.append(f"Token Imbalances on {self.chain_name} for tx {tx_hash}:")
        for token_address, imbalance in token_imbalances.items():
            # write imbalance to table if it's non-zero
            if imbalance != 0:
                self.db.write_token_imbalances(
                    tx_hash, auction_id, block_number, token_address, imbalance
                )
                log_message.append(f"Token: {token_address}, Imbalance: {imbalance}")
        for token_address in token_imbalances.keys():
            # fetch price for tokens with non-zero imbalance and write to table
            if token_imbalances[token_address] != 0:
                price_params = {
                    "tx_hash": tx_hash,
                    "block_number": block_number,
                    "token_address": token_address,
                }
                price_data = self.price_providers.get_price(price_params)
                # price_data = self.price_providers.get_price(block_number, token_address)
                if price_data:
                    price, source = price_data
                    self.db.write_prices(
                        source, block_number, tx_hash, token_address, price
                    )
                    log_message.append(f"Token: {token_address}, Price: {price} ETH")

        logger.info("\n".join(log_message))
