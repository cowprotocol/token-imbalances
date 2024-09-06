from sqlalchemy import text
from sqlalchemy.engine import Engine
from src.helpers.config import check_db_connection, logger
from src.helpers.helper_functions import read_sql_file
from src.constants import NULL_ADDRESS_STRING


class Database:
    """
    Class is used to write data to appropriate tables for the slippage project
    using a database connection.
    """

    def __init__(self, engine: Engine, chain_name: str):
        self.engine = engine
        self.chain_name = chain_name

    def execute_query(self, query: str, params: dict):
        """Function executes a read-only query."""
        self.engine = check_db_connection(self.engine, "solver_slippage")
        with self.engine.connect() as connection:
            try:
                result = connection.execute(text(query), params)
                return result
            except Exception as e:
                logger.error(f"Error executing query: {e}")
                raise

    def execute_and_commit(self, query: str, params: dict):
        """Function writes to the table."""
        self.engine = check_db_connection(self.engine, "solver_slippage")
        with self.engine.connect() as connection:
            try:
                connection.execute(text(query), params)
                connection.commit()
            except Exception as e:
                logger.error(f"Error executing and committing query: {e}")
                connection.rollback()
                raise

    def write_token_imbalances(
        self,
        tx_hash: str,
        auction_id: int,
        block_number: int,
        token_address: str,
        imbalance: float,
    ):
        """Function attempts to write token imbalances to the table."""
        tx_hash_bytes = bytes.fromhex(tx_hash[2:])
        token_address_bytes = bytes.fromhex(token_address[2:])

        query = read_sql_file("src/sql/insert_raw_token_imbalances.sql")
        self.execute_and_commit(
            query,
            {
                "auction_id": auction_id,
                "chain_name": self.chain_name,
                "block_number": block_number,
                "tx_hash": tx_hash_bytes,
                "token_address": token_address_bytes,
                "imbalance": imbalance,
            },
        )

    def write_prices(
        self,
        source: str,
        block_number: int,
        tx_hash: str,
        token_address: str,
        price: float,
    ):
        """Function attempts to write price data to the table."""
        tx_hash_bytes = bytes.fromhex(tx_hash[2:])
        token_address_bytes = bytes.fromhex(token_address[2:])

        query = read_sql_file("src/sql/insert_price.sql")
        self.execute_and_commit(
            query,
            {
                "chain_name": self.chain_name,
                "source": source,
                "block_number": block_number,
                "tx_hash": tx_hash_bytes,
                "token_address": token_address_bytes,
                "price": price,
            },
        )

    def write_fees(
        self,
        auction_id: int,
        block_number: int,
        tx_hash: str,
        order_uid: str,
        token_address: str,
        fee_amount: float,
        fee_type: str,
        recipient: str,
    ):
        """Function attempts to write price data to the table."""
        tx_hash_bytes = bytes.fromhex(tx_hash[2:])
        token_address_bytes = bytes.fromhex(token_address[2:])
        order_uid_bytes = bytes.fromhex(order_uid[2:])
        null_address_bytes = bytes.fromhex(NULL_ADDRESS_STRING[2:])

        query = read_sql_file("src/sql/insert_fee.sql")
        final_recipient = null_address_bytes
        if recipient != "":
            final_recipient = bytes.fromhex(recipient[2:])

        self.execute_and_commit(
            query,
            {
                "chain_name": self.chain_name,
                "auction_id": auction_id,
                "block_number": block_number,
                "tx_hash": tx_hash_bytes,
                "order_uid": order_uid_bytes,
                "token_address": token_address_bytes,
                "fee_amount": fee_amount,
                "fee_type": fee_type,
                "recipient": final_recipient,
            },
        )
