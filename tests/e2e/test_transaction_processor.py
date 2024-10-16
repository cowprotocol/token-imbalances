from os import getenv, environ
from unittest.mock import Mock

from src.helpers.config import initialize_connections
from src.transaction_processor import TransactionProcessor
from src.helpers.database import Database
from src.helpers.blockchain_data import BlockchainData


def tests_process_single_transaction():
    chain_name = "mainnet"
    process_imbalances = True
    process_fees = False
    process_prices = True

    processor = TransactionProcessor(
        chain_name, process_imbalances, process_fees, process_prices
    )

    # delete data

    # process hash
    processor.process_single_transaction(
        "0x68e7183363be7460642e78ab09a2898c8aeac6657c2434f7b318f54590c46299",
        9481594,
        20935017,
    )
