from os import getenv

from dotenv import load_dotenv
from sqlalchemy import create_engine
from web3 import Web3

from src.helpers.blockchain_data import get_token_decimals
from src.helpers.database import Database


load_dotenv()


def update_token_decimals(engine, web3) -> None:
    db = Database(engine, "mainnet")

    token_addresses = db.get_tokens_without_decimals()

    token_decimals = [
        (token_address, get_token_decimals(token_address, web3))
        for token_address in token_addresses
    ]
    if token_decimals:
        db.write_token_decimals(token_decimals)


if __name__ == "__main__":
    engine = create_engine(f"postgresql+psycopg2://{getenv('SOLVER_SLIPPAGE_DB_URL')}")
    web3 = Web3(Web3.HTTPProvider(getenv("NODE_URL")))

    update_token_decimals(engine, web3)
