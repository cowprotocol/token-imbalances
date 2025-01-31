import time

from hexbytes import HexBytes
from web3 import Web3

from src.fees.compute_fees import compute_all_fees_of_batch
from src.helpers.blockchain_data import BlockchainData
from src.helpers.config import CHAIN_SLEEP_TIME, logger, initialize_connections
from src.helpers.database import Database
from src.helpers.helper_functions import set_params
from src.raw_imbalances import RawTokenImbalances
from src.price_providers.price_feed import PriceFeed
from src.token_decimals import update_token_decimals

# pylint: disable=logging-fstring-interpolation


class TransactionProcessor:
    """Class processes transactions for the slippage project."""

    # pylint: disable=too-many-instance-attributes, too-many-arguments

    def __init__(
        self,
        chain_name: str,
        process_imbalances: bool,
        process_fees: bool,
        process_prices: bool,
    ):
        self.chain_name = chain_name
        self.process_imbalances = process_imbalances
        self.process_fees = process_fees
        self.process_prices = process_prices

        web3, db_engine = initialize_connections()
        self.blockchain_data = BlockchainData(web3)
        self.db = Database(db_engine, chain_name)
        self.imbalances = RawTokenImbalances(self.blockchain_data.web3, self.chain_name)
        self.price_providers = PriceFeed(activate=process_prices)

    ###################### MAIN RUN LOOP ######################
    def run(self) -> None:
        """Main Daemon loop that processes txs and computes imbalances,
        relevant prices and fees, if needed."""

        start_block = self.get_start_block()
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

    ###########################################################

    def get_start_block(self) -> int:
        """
        Retrieve the most recent block X already present in raw_token_imbalances table,
        and return block X+1 as start_block.
        If block X is from more than 1 day ago, a recent finalized block is returned.
        TODO: Remove that rule before moving to production.

        If no entries are present, fallback to get_finalized_block_number().
        """
        try:
            # 1) get latest block on chain
            block_number_latest = self.blockchain_data.get_latest_block()
            # 2) get last transaction from DB
            latest_tx_hash = self.db.get_latest_transaction()
            # 3) get block of that transaction
            if latest_tx_hash:
                block_number_db = int(
                    self.blockchain_data.web3.eth.get_transaction_receipt(
                        HexBytes(latest_tx_hash)
                    )["blockNumber"]
                )
                if block_number_db < block_number_latest - 7200:
                    #  TODO: Remove this rule before moving to production.
                    logger.warning(
                        "Only old transactions found in database, latest was on block"
                        f"{block_number_db}. Using recent block instead."
                    )
                    start_block = block_number_latest
                else:
                    start_block = block_number_db + 1
            else:
                logger.warning(
                    "No transaction found in database. Using recent block instead."
                )
                start_block = block_number_latest
        except Exception as e:
            logger.error(f"Error fetching start block: {e}")
            raise

        return start_block

    def process_single_transaction(
        self,
        tx_hash: str,
        auction_id: int,
        block_number: int,
    ) -> None:
        """Function processes a single tx to find imbalances, fees, prices including writing to database."""
        try:
            logger.info(f"Processing transaction {tx_hash}")
            if self.process_prices:
                self.process_tx_prices(tx_hash)

            if self.process_imbalances:
                self.process_tx_imbalances(tx_hash, auction_id, block_number)

            if self.process_fees:
                self.process_tx_fees(tx_hash, auction_id, block_number)

        except Exception as err:
            logger.error(f"An Error occurred: {err}")
            return

    def process_tx_prices(self, tx_hash: str) -> None:
        # get transaction timestamp
        transaction_timestamp = self.blockchain_data.get_transaction_timestamp(tx_hash)
        # store transaction timestamp
        self.db.write_transaction_timestamp(transaction_timestamp)

        # get transaction tokens
        transaction_tokens = self.imbalances.get_transaction_tokens(tx_hash)
        # store transaction tokens
        self.db.write_transaction_tokens(transaction_tokens)

        # update token decimals
        update_token_decimals(self.db, self.blockchain_data)

        # get prices
        prices_new = self.get_prices_for_tokens(
            transaction_timestamp, transaction_tokens
        )
        # store prices
        self.db.write_prices_new(prices_new)

    def get_prices_for_tokens(
        self,
        transaction_timestamp: tuple[str, int],
        transaction_tokens: list[tuple[str, str]],
    ) -> list[tuple[str, int, float, str]]:
        """Fetch prices for all transferred tokens."""
        prices: list[tuple[str, int, float, str]] = []
        tx_hash = transaction_timestamp[0]
        timestamp = transaction_timestamp[1]
        token_addresses = [token_address for _, token_address in transaction_tokens]
        block_number = self.blockchain_data.web3.eth.get_transaction_receipt(
            HexBytes(tx_hash)
        )["blockNumber"]
        try:
            for token_address in token_addresses:
                price_data = self.price_providers.get_price(
                    set_params(token_address, block_number, tx_hash)
                )
                if price_data:
                    prices += [
                        (token_address, timestamp, price, source)
                        for price, source in price_data
                    ]
                else:
                    logger.warning(
                        f"Failed to fetch price for token {token_address} and"
                        f"transaction {tx_hash}."
                    )
        except Exception as e:
            logger.error(f"Failed to process prices for transaction {tx_hash}: {e}")

        return prices

    def process_tx_imbalances(
        self, tx_hash: str, auction_id: int, block_number: int
    ) -> None:
        token_imbalances = self.imbalances.compute_token_imbalances(tx_hash)
        if token_imbalances:
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
                        logger.info(f"Token: {token_address}, Imbalance: {imbalance}")
            except Exception as err:
                logger.error(f"Error: {err}")

    def process_tx_fees(
        self,
        tx_hash: str,
        auction_id: int,
        block_number: int,
    ) -> None:
        """Process protocol, partner and network fees for a given transaction."""
        try:
            protocol_fees, partner_fees, network_fees = compute_all_fees_of_batch(
                HexBytes(tx_hash)
            )
        except Exception as e:
            logger.error(f"Failed to compute fees for transaction {tx_hash}: {e}")
            return

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
