import os
import psycopg2
from sqlalchemy import create_engine
from dotenv import load_dotenv
from src.helper_functions import get_logger

load_dotenv()
ETHEREUM_NODE_URL = os.getenv("ETHEREUM_NODE_URL")
GNOSIS_NODE_URL = os.getenv("GNOSIS_NODE_URL")

ARBITRUM_NODE_URL = os.getenv("ARBITRUM_NODE_URL")
SOLVER_SLIPPAGE_DB_URL = os.getenv("SOLVER_SLIPPAGE_DB_URL")

CHAIN_RPC_ENDPOINTS = {"Ethereum": ETHEREUM_NODE_URL, "Gnosis": GNOSIS_NODE_URL}

# sleep time can be configured here
CHAIN_SLEEP_TIMES = {"Ethereum": 60, "Gnosis": 120}


def create_read_db_connection(chain_name: str):
    """function that creates a connection to the CoW db."""
    if chain_name == "Ethereum":
        read_db_url = os.getenv("ETHEREUM_DB_URL")
    elif chain_name == "Gnosis":
        read_db_url = os.getenv("GNOSIS_DB_URL")

    return create_engine(f"postgresql+psycopg2://{read_db_url}")


def create_write_db_connection():
    """Function that creates a connection to the write database."""
    write_db_connection = psycopg2.connect(
        database="solver_slippage",
        host=os.getenv("SOLVER_SLIPPAGE_HOST"),
        user=os.getenv("SOLVER_SLIPPAGE_USER"),
        password=os.getenv("SOLVER_SLIPPAGE_PASS"),
        port=5432,
    )
    return write_db_connection


logger = get_logger("raw_token_imbalances")
