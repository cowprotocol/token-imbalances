import os
import psycopg2
from typing import Any, Optional
from sqlalchemy import create_engine, Engine
from dotenv import load_dotenv
from urllib.parse import urlparse
from psycopg2.extensions import connection as Psycopg2Connection
from src.helper_functions import get_logger


load_dotenv()
ETHEREUM_NODE_URL = os.getenv("ETHEREUM_NODE_URL")
GNOSIS_NODE_URL = os.getenv("GNOSIS_NODE_URL")

CHAIN_RPC_ENDPOINTS = {"Ethereum": ETHEREUM_NODE_URL, "Gnosis": GNOSIS_NODE_URL}

logger = get_logger("raw_token_imbalances")


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


CHAIN_SLEEP_TIMES = {
    "Ethereum": get_env_int("ETHEREUM_SLEEP_TIME"),
    "Gnosis": get_env_int("GNOSIS_SLEEP_TIME"),
}


def create_backend_db_connection(chain_name: str) -> Engine:
    """function that creates a connection to the CoW db."""
    if chain_name == "Ethereum":
        read_db_url = os.getenv("ETHEREUM_DB_URL")
    elif chain_name == "Gnosis":
        read_db_url = os.getenv("GNOSIS_DB_URL")

    if not read_db_url:
        raise ValueError(f"No database URL found for chain: {chain_name}")

    return create_engine(f"postgresql+psycopg2://{read_db_url}")


def create_solver_slippage_db_connection() -> Psycopg2Connection:
    """Function that creates a connection to the write database."""

    parsed_url = urlparse(os.getenv("SOLVER_SLIPPAGE_DB_URL"))

    if not parsed_url.hostname or not parsed_url.path:
        raise ValueError("Invalid or missing write database URL")

    # Connect to the database
    solver_slippage_connection = psycopg2.connect(
        database=parsed_url.path[1:],
        user=parsed_url.username,
        password=parsed_url.password,
        host=parsed_url.hostname,
        port=parsed_url.port,
    )
    return solver_slippage_connection


def check_db_connection(connection: Any, chain_name: Optional[str] = None) -> Any:
    """
    Check if the database connection is still active. If not, create a new one.
    """
    try:
        if connection.closed:
            raise psycopg2.OperationalError("Connection is closed")
    except (psycopg2.OperationalError, AttributeError):
        connection = (
            create_backend_db_connection(chain_name)
            if chain_name
            else create_solver_slippage_db_connection()
        )
    return connection
