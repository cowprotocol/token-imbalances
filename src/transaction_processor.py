from hexbytes import HexBytes
from web3 import Web3
from src.helpers.blockchain_data import BlockchainData
from src.helpers.database import Database
from src.imbalances_script import RawTokenImbalances
from src.price_providers.price_feed import PriceFeed
from src.helpers.helper_functions import read_sql_file, set_params
from src.helpers.config import CHAIN_SLEEP_TIME, logger
from src.fees.compute_fees import compute_all_fees_of_batch
import time


class TransactionProcessor:
    """Class processes transactions for the slippage project."""

    def __init__(
        self,
        blockchain_data: BlockchainData,
        db: Database,
        chain_name: str,
        process_imbalances: bool,
        process_fees: bool,
        process_prices: bool,
    ):
        self.blockchain_data = blockchain_data
        self.db = db
        self.chain_name = chain_name
        self.process_imbalances = process_imbalances
        self.process_fees = process_fees
        self.process_prices = process_prices

        self.imbalances = RawTokenImbalances(self.blockchain_data.web3, self.chain_name)
        self.price_providers = PriceFeed(activate=process_prices)
        self.log_message: list[str] = []

    def get_start_block(self) -> int:
        """
        Retrieve the most recent block X already present in raw_token_imbalances table,
        and return block X+1 as start_block.
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
            blockchain_latest_block = self.blockchain_data.get_latest_block()

            # If no entries present, fallback to get_latest_block()
            if max_block is None:
                return blockchain_latest_block

            logger.info("Fetched max block number from database: %d", max_block)
            if max_block > blockchain_latest_block - 7200:
                return max_block + 1
            else:
                return blockchain_latest_block
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
    ) -> None:
        """Function processes a single tx to find imbalances, fees, prices including writing to database."""
        self.log_message = []
        try:
            # Compute Raw Token Imbalances
            if self.process_imbalances:
                token_imbalances = self.process_token_imbalances(
                    tx_hash, auction_id, block_number
                )

            # Compute Fees
            if self.process_fees:
                (
                    protocol_fees,
                    partner_fees,
                    network_fees,
                ) = self.process_fees_for_transaction(tx_hash)

            # Compute Prices
            if self.process_prices and self.process_imbalances:
                prices = self.process_prices_for_tokens(
                    token_imbalances, block_number, tx_hash
                )

            # Write to database iff no errors in either computations
            if (
                (not self.process_imbalances)
                and (not self.process_fees)
                and (not self.process_prices)
            ):
                return

            if self.process_imbalances and token_imbalances:
                self.handle_imbalances(
                    token_imbalances, tx_hash, auction_id, block_number
                )

            if self.process_fees:
                self.handle_fees(
                    protocol_fees,
                    partner_fees,
                    network_fees,
                    auction_id,
                    block_number,
                    tx_hash,
                )

            if self.process_prices and prices:
                self.handle_prices(prices, tx_hash, block_number)

            logger.info("\n".join(self.log_message))

        except Exception as err:
            logger.error(f"An Error occurred: {err}")
            return

    def process_token_imbalances(
        self, tx_hash: str, auction_id: int, block_number: int
    ) -> dict[str, int]:
        """Process token imbalances for a given transaction and return imbalances."""
        try:
            token_imbalances = self.imbalances.compute_imbalances(tx_hash)
            if token_imbalances:
                self.log_message.append(
                    f"Token Imbalances on {self.chain_name} for tx {tx_hash}:"
                )
            return token_imbalances
        except Exception as e:
            logger.error(f"Failed to compute imbalances for transaction {tx_hash}: {e}")
            return {}

    def process_fees_for_transaction(
        self,
        tx_hash: str,
    ) -> tuple[
        dict[str, tuple[str, int]],
        dict[str, tuple[str, int, str]],
        dict[str, tuple[str, int]],
    ]:
        """Process and return protocol and network fees for a given transaction."""
        try:
            protocol_fees, partner_fees, network_fees = compute_all_fees_of_batch(
                HexBytes(tx_hash)
            )
            return protocol_fees, partner_fees, network_fees
        except Exception as e:
            logger.error(f"Failed to process fees for transaction {tx_hash}: {e}")
            return {}, {}, {}

    def process_prices_for_tokens(
        self,
        token_imbalances: dict[str, int],
        block_number: int,
        tx_hash: str,
    ) -> dict[str, tuple[float, str]]:
        """Compute prices for tokens with non-null imbalances."""
        prices = {}
        try:
            for token_address in token_imbalances.keys():
                price_data = self.price_providers.get_price(
                    set_params(token_address, block_number, tx_hash)
                )
                if price_data:
                    price, source = price_data
                    prices[token_address] = (price, source)
        except Exception as e:
            logger.error(f"Failed to process prices for transaction {tx_hash}: {e}")

        return prices

    def handle_imbalances(
        self,
        token_imbalances: dict[str, int],
        tx_hash: str,
        auction_id: int,
        block_number: int,
    ) -> None:
        """Function loops over non-null raw imbalances and writes them to the database."""
        try:
            for token_address, imbalance in token_imbalances.items():
                if imbalance != 0:
                    self.db.write_token_imbalances(
                        tx_hash,
                        auction_id,
                        block_number,
                        token_address,
                        imbalance,
                    )
                    self.log_message.append(
                        f"Token: {token_address}, Imbalance: {imbalance}"
                    )
        except Exception as err:
            logger.error(f"Error: {err}")

    def handle_fees(
        self,
        protocol_fees: dict[str, tuple[str, int]],
        partner_fees: dict[str, tuple[str, int, str]],
        network_fees: dict[str, tuple[str, int]],
        auction_id: int,
        block_number: int,
        tx_hash: str,
    ):
        """This function loops over (token, fee) and calls write_fees to write to table."""
        try:
            # Write protocol fees
            for order_uid, (token_address, fee_amount) in protocol_fees.items():
                self.db.write_fees(
                    auction_id=auction_id,
                    block_number=block_number,
                    tx_hash=tx_hash,
                    order_uid=order_uid,
                    token_address=token_address,
                    fee_amount=float(fee_amount),
                    fee_type="protocol",
                    recipient="",
                )

            # Write partner fees
            for order_uid, (
                token_address,
                fee_amount,
                recipient,
            ) in partner_fees.items():
                self.db.write_fees(
                    auction_id=auction_id,
                    block_number=block_number,
                    tx_hash=tx_hash,
                    order_uid=order_uid,
                    token_address=token_address,
                    fee_amount=float(fee_amount),
                    fee_type="partner",
                    recipient=recipient,
                )

            # Write network fees
            for order_uid, (token_address, fee_amount) in network_fees.items():
                self.db.write_fees(
                    auction_id=auction_id,
                    block_number=block_number,
                    tx_hash=tx_hash,
                    order_uid=order_uid,
                    token_address=token_address,
                    fee_amount=float(fee_amount),
                    fee_type="network",
                    recipient="",
                )
        except Exception as err:
            logger.error(
                f"Failed to write fees to database for transaction {tx_hash}: {err}"
            )

    def handle_prices(
        self, prices: dict[str, tuple[float, str]], tx_hash: str, block_number: int
    ) -> None:
        """Function writes prices to table per token."""
        try:
            for token_address, (price, source) in prices.items():
                self.db.write_prices(
                    source, block_number, tx_hash, token_address, price
                )
                self.log_message.append(f"Token: {token_address}, Price: {price} ETH")
        except Exception as err:
            logger.error(f"Error: {err}")


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
