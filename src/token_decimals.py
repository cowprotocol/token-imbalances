from os import getenv

from dotenv import load_dotenv
from sqlalchemy import create_engine
from web3 import Web3

from src.helpers.blockchain_data import BlockchainData
from src.helpers.database import Database


load_dotenv()


def update_token_decimals(database: Database, blockchain: BlockchainData) -> None:
    token_addresses = database.get_tokens_without_decimals()

    token_decimals = [
        (token_address, blockchain.get_token_decimals(token_address))
        for token_address in token_addresses
    ]
    if token_decimals:
        database.write_token_decimals(token_decimals)


if __name__ == "__main__":
    engine = create_engine(f"postgresql+psycopg://{getenv('SOLVER_SLIPPAGE_DB_URL')}")
    database = Database(engine, "mainnet")
    web3 = Web3(Web3.HTTPProvider(getenv("NODE_URL")))
    blockchain_data = BlockchainData(web3)

    update_token_decimals(database, blockchain_data)
