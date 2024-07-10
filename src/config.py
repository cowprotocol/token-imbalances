import os
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

CREATE_DB_URLS = {
    "backend": os.getenv("DB_URL"),
    "solver_slippage": os.getenv("SOLVER_SLIPPAGE_DB_URL"),
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


def create_db_connection(db_type: str) -> Engine:
    """
    Function that creates a connection to the specified database.
    db_type should be either "backend" or "solver_slippage".
    """
    db_url = CREATE_DB_URLS.get(db_type)
    if not db_url:
        raise ValueError(f"{db_type} database URL not found in environment variables.")

    return create_engine(f"postgresql+psycopg2://{db_url}")


def check_db_connection(connection: Engine, db_type: str) -> Engine:
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
            create_db_connection("backend")
            if db_type == "backend"
            else create_db_connection("solver_slippage")
        )
    return connection
