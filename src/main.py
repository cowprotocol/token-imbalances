import os
from src.config import initialize_connections, logger
from src.transaction_processor import TransactionProcessor
from src.helper_classes.database import Database
from src.helper_classes.blockchain_data import BlockchainData


def main() -> None:
    chain_name = os.getenv("CHAIN_NAME")
    if chain_name is None:
        logger.error("CHAIN_NAME environment variable is not set.")
        return

    web3, db_engine = initialize_connections()
    blockchain = BlockchainData(web3)
    db = Database(db_engine)
    processor = TransactionProcessor(blockchain, db, chain_name)

    start_block = processor.get_start_block()
    processor.process(start_block)


if __name__ == "__main__":
    main()
