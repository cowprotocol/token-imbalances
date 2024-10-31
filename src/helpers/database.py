from datetime import datetime, timezone

from hexbytes import HexBytes
import psycopg
from sqlalchemy import text, insert, Table, Column, Integer, LargeBinary, MetaData
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
                logger.info(f"Error executing and committing query: {e}")
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
                "fee_recipient": final_recipient,
            },
        )

    def write_transaction_timestamp(
        self, transaction_timestamp: tuple[str, int]
    ) -> None:
        """Writes the transaction timestamp to database."""
        query = (
            "INSERT INTO transaction_timestamp (tx_hash, time) "
            "VALUES (:tx_hash, :time);"
        )
        self.execute_and_commit(
            query,
            {
                "tx_hash": bytes.fromhex(transaction_timestamp[0][2:]),
                "time": datetime.fromtimestamp(
                    transaction_timestamp[1], tz=timezone.utc
                ),
            },
        )

    def write_transaction_tokens(
        self, transaction_tokens: list[tuple[str, str]]
    ) -> None:
        """Writes the transaction tokens to the database."""
        query = (
            "INSERT INTO transaction_tokens (tx_hash, token_address) "
            "VALUES (:tx_hash, :token_address);"
        )
        for tx_hash, token_address in transaction_tokens:
            self.execute_and_commit(
                query,
                {
                    "tx_hash": bytes.fromhex(tx_hash[2:]),
                    "token_address": bytes.fromhex(token_address[2:]),
                },
            )

    def write_prices_new(self, prices: list[tuple[str, int, float, str]]) -> None:
        """Write prices to database."""
        query = (
            "INSERT INTO prices (token_address, time, price, source) "
            "VALUES (:token_address, :time, :price, :source);"
        )
        for token_address, time, price, source in prices:
            try:
                self.execute_and_commit(
                    query,
                    {
                        "token_address": bytes.fromhex(token_address[2:]),
                        "time": datetime.fromtimestamp(time, tz=timezone.utc),
                        "price": price,
                        "source": source,
                    },
                )
            except Exception as err:
                pass
            # except psycopg.errors.NumericValueOutOfRange:
            #     logger.info(
            #         f"Error while writing price data. token: {token_address}, "
            #         f"time: {time}, price: {price}, source: {source}"
            #     )

    def get_latest_transaction(self) -> str | None:
        """Get latest transaction hash.
        If no transaction is found, return None."""
        query = "SELECT tx_hash FROM transaction_timestamp ORDER BY time DESC LIMIT 1;"
        result = self.execute_query(query, {}).fetchone()

        if result is None:
            return None

        latest_tx_hash = HexBytes(result[0]).to_0x_hex()
        return latest_tx_hash

    def get_tokens_without_decimals(self) -> list[str]:
        """Get tokens without decimals."""
        query = (
            "SELECT token_address FROM transaction_tokens "
            "WHERE token_address not in (SELECT token_address FROM token_decimals);"
        )
        result = self.execute_query(query, {}).fetchall()
        return list({HexBytes(row[0]).to_0x_hex() for row in result})

    def write_token_decimals(self, token_decimals: list[tuple[str, int]]) -> None:
        self.engine = check_db_connection(self.engine, "solver_slippage")

        # Define the table without creating a model class
        token_decimals_table = Table(
            "token_decimals", MetaData(), autoload_with=self.engine
        )

        # Prepare the data
        records = [
            {"token_address": bytes.fromhex(token_address[2:]), "decimals": decimals}
            for token_address, decimals in token_decimals
        ]

        # Execute the bulk insert
        with self.engine.connect() as conn:
            conn.execute(token_decimals_table.insert(), records)
            conn.commit()
