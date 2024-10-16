import os
from src.helpers.config import initialize_connections, logger
from src.transaction_processor import TransactionProcessor
from src.helpers.database import Database
from src.helpers.blockchain_data import BlockchainData


def main() -> None:
    # valid chain names: mainnet, xdai, arbitrum_one
    chain_name = os.getenv("CHAIN_NAME")
    process_imbalances = os.getenv("PROCESS_IMBALANCES", "True") == "True"
    process_prices = os.getenv("PROCESS_PRICES", "False") == "True"
    process_fees = os.getenv("PROCESS_FEES", "False") == "True"

    if chain_name is None:
        logger.error("CHAIN_NAME environment variable is not set.")
        return

    processor = TransactionProcessor(
        chain_name, process_imbalances, process_fees, process_prices
    )
    processor.run()


if __name__ == "__main__":
    main()
