import os
from typing import Optional
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy import create_engine, Engine
from dotenv import load_dotenv
from src.helper_functions import get_logger


load_dotenv()
NODE_URL = os.getenv("NODE_URL")

logger = get_logger("raw_token_imbalances")

# Utilized by imbalances_script for computing for single tx hash
CHAIN_RPC_ENDPOINTS = {
    "Ethereum": os.getenv("ETHEREUM_NODE_URL"),
    "Gnosis": os.getenv("GNOSIS_NODE_URL"),
}


def get_env_int(var_name: str) -> int:
    """
    Function for safe conversion to int (prevents None -> int conversion issues raised by mypy)
    Retrieve environment variable and convert to int. Raise an error if not set.
    """
    value = os.getenv(var_name)
    if value is None:
        raise ValueError(f"Environment variable {var_name} is not set.")
    try:
        return int(value)
    except ValueError:
        raise ValueError(f"Environment variable {var_name} must be a int.")


CHAIN_SLEEP_TIME = get_env_int("CHAIN_SLEEP_TIME")


def create_backend_db_connection(chain_name: str) -> Engine:
    """function that creates a connection to the CoW db."""
    read_db_url = os.getenv("DB_URL")

    if not read_db_url:
        raise ValueError(f"No database URL found for chain: {chain_name}")

    return create_engine(f"postgresql+psycopg2://{read_db_url}")


def create_solver_slippage_db_connection() -> Engine:
    """function that creates a connection to the CoW db."""
    solver_db_url = os.getenv("SOLVER_SLIPPAGE_DB_URL")
    if not solver_db_url:
        raise ValueError(
            "Solver slippage database URL not found in environment variables."
        )

    return create_engine(f"postgresql+psycopg2://{solver_db_url}")


def check_db_connection(connection: Engine, chain_name: Optional[str] = None) -> Engine:
    """
    Check if the database connection is still active. If not, create a new one.
    """
    try:
        if connection:
            with connection.connect() as conn:  # Use connection.connect() to get a Connection object
                conn.execute(text("SELECT 1"))
    except OperationalError:
        # if connection is closed, create new one
        connection = (
            create_backend_db_connection(chain_name)
            if chain_name
            else create_solver_slippage_db_connection()
        )
    return connection
