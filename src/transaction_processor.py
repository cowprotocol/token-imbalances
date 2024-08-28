from hexbytes import HexBytes
from web3 import Web3
from src.helpers.blockchain_data import BlockchainData
from src.helpers.database import Database
from src.imbalances_script import RawTokenImbalances
from src.price_providers.price_feed import PriceFeed
from src.helpers.helper_functions import read_sql_file, set_params
from src.helpers.config import CHAIN_SLEEP_TIME, logger
from src.fees.compute_fees import batch_fee_imbalances
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

        protocol_fees, network_fees = batch_fee_imbalances(HexBytes(tx_hash))
        self.handle_fees(protocol_fees, network_fees, auction_id, block_number, tx_hash)
        slippage = calculate_slippage(token_imbalances, protocol_fees, network_fees)

        for token_address in slippage.keys():
            # fetch price for tokens with non-zero imbalance and write to table
            if slippage[token_address] != 0:
                price_data = self.price_providers.get_price(
                    set_params(token_address, block_number, tx_hash)
                )
                if price_data:
                    price, source = price_data
                    self.db.write_prices(
                        source, block_number, tx_hash, token_address, price
                    )
                    log_message.append(f"Token: {token_address}, Price: {price} ETH")

        logger.info("\n".join(log_message))

    def handle_fees(
        self,
        protocol_fees: dict[str, tuple[str, int]],
        network_fees: dict[str, tuple[str, int]],
        auction_id: int,
        block_number: int,
        tx_hash: str,
    ):
        """This function loops over (token, fee) and calls write_fees to write to table."""
        # Write protocol fees
        for order_uid, (token_address, fee_amount) in protocol_fees.items():
            self.db.write_fees(
                chain_name=self.chain_name,
                auction_id=auction_id,
                block_number=block_number,
                tx_hash=tx_hash,
                order_uid=order_uid,
                token_address=token_address,
                fee_amount=float(fee_amount),
                fee_type="protocol",
            )

        # Write network fees
        for order_uid, (token_address, fee_amount) in network_fees.items():
            self.db.write_fees(
                chain_name=self.chain_name,
                auction_id=auction_id,
                block_number=block_number,
                tx_hash=tx_hash,
                order_uid=order_uid,
                token_address=token_address,
                fee_amount=float(fee_amount),
                fee_type="network",
            )


def calculate_slippage(
    token_imbalances: dict[str, int],
    protocol_fees: dict[str, tuple[str, int]],
    network_fees: dict[str, tuple[str, int]],
) -> dict[str, int]:
    """Function calculates net slippage for each token per tx."""

    # checksum on token addresses
    token_imbalances = {
        Web3.to_checksum_address(token): value
        for token, value in token_imbalances.items()
    }
    protocol_fees = {
        order_uid: (Web3.to_checksum_address(token_address), fee_amount)
        for order_uid, (token_address, fee_amount) in protocol_fees.items()
    }

    network_fees = {
        order_uid: (Web3.to_checksum_address(token_address), fee_amount)
        for order_uid, (token_address, fee_amount) in network_fees.items()
    }

    # To find all tokens for which we need a price -> set of tokens from all dicts
    all_tokens = (
        set(token_imbalances.keys())
        .union([token_address for token_address, _ in protocol_fees.values()])
        .union([token_address for token_address, _ in network_fees.values()])
    )

    slippage = {}

    # calculate net slippage per token
    for token in all_tokens:
        imbalance = token_imbalances.get(token, 0)
        protocol_fee = sum(
            fee_amount
            for _, (token_address, fee_amount) in protocol_fees.items()
            if token_address == token
        )
        network_fee = sum(
            fee_amount
            for _, (token_address, fee_amount) in network_fees.items()
            if token_address == token
        )
        # for a final slippage per token per tx basis
        total = imbalance - protocol_fee - network_fee
        slippage[token] = total

    return slippage
