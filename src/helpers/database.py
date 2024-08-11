from sqlalchemy import text
from sqlalchemy.engine import Engine
from src.helpers.config import check_db_connection, logger


class Database:
    def __init__(self, engine: Engine):
        self.engine = engine

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
