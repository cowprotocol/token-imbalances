import os
from src.helpers.config import initialize_connections, logger
from src.transaction_processor import TransactionProcessor
from src.helpers.database import Database
from src.helpers.blockchain_data import BlockchainData


def main() -> None:
    # valid chain names: mainnet, xdai, arbitrum_one
    chain_name = os.getenv("CHAIN_NAME")
    if chain_name is None:
        logger.error("CHAIN_NAME environment variable is not set.")
        return

    process_imbalances = True
    process_fees = False
    process_prices = True

    web3, db_engine = initialize_connections()
    blockchain = BlockchainData(web3)
    db = Database(db_engine, chain_name)

    if chain_name == "arbitrum_one":
        process_imbalances = False
        process_prices = False

    if chain_name == "xdai":
        process_prices = False

    processor = TransactionProcessor(
        blockchain, db, chain_name, process_imbalances, process_fees, process_prices
    )

    start_block = processor.get_start_block()
    processor.process(start_block)


if __name__ == "__main__":
    main()
