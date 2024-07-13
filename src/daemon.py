"""
Running this daemon computes raw imbalances for finalized blocks by calling imbalances_script.py.
"""
import os
import time
from typing import List, Tuple
from web3 import Web3
from sqlalchemy import text
from sqlalchemy.engine import Engine
from src.imbalances_script import RawTokenImbalances
from src.helper_functions import (
    get_web3_instance,
    get_finalized_block_number,
    get_tx_hashes_blocks,
    get_auction_id,
)
from src.config import (
    CHAIN_SLEEP_TIME,
    create_db_connection,
    check_db_connection,
    logger,
)


def get_start_block(
    chain_name: str, solver_slippage_connection: Engine, web3: Web3
) -> int:
    """
    Retrieve the most recent block already present in raw_token_imbalances table,
    delete entries for that block, and return this block number as start_block.
    If no entries are present, fallback to get_finalized_block_number().
    """
    try:
        solver_slippage_connection = check_db_connection(
            solver_slippage_connection, "solver_slippage"
        )

        query_max_block = text(
            """
            SELECT MAX(block_number) FROM raw_token_imbalances_temp
            WHERE chain_name = :chain_name
        """
        )

        with solver_slippage_connection.connect() as connection:
            result = connection.execute(query_max_block, {"chain_name": chain_name})
            row = result.fetchone()
            max_block = (
                row[0] if row is not None else None
            )  # Fetch the maximum block number
            if max_block is not None:
                logger.debug("Fetched max block number from database: %d", max_block)

            # If no entries present, fallback to get_finalized_block_number()
            if max_block is None:
                return get_finalized_block_number(web3)

            # delete entries for the max block from the table
            delete_sql = text(
                """
                DELETE FROM raw_token_imbalances_temp WHERE chain_name = :chain_name AND block_number = :block_number
            """
            )
            try:
                connection.execute(
                    delete_sql, {"chain_name": chain_name, "block_number": max_block}
                )
                connection.commit()
                logger.debug(
                    "Successfully deleted entries for block number: %s", max_block
                )
            except Exception as e:
                logger.error(
                    "Failed to delete entries for block number %s: %s", max_block, e
                )

            return max_block
    except Exception as e:
        logger.error("Error accessing database: %s", e)
        return get_finalized_block_number(web3)


def fetch_tx_data(
    start_block: int, end_block: int, web3: Web3
) -> List[Tuple[str, int, int]]:
    """Fetch transaction hashes beginning from start_block to end_block."""
    tx_data: List[Tuple[str, int, int]] = []
    tx_hashes_blocks = get_tx_hashes_blocks(start_block, end_block, web3)

    for tx_hash, block_number in tx_hashes_blocks:
        try:
            auction_id = get_auction_id(web3, tx_hash)
            tx_data.append((tx_hash, auction_id, block_number))
        except Exception as e:
            print(f"Error fetching auction ID for {tx_hash}: {e}")

    return tx_data


def record_exists(
    solver_slippage_connection: Engine,
    tx_hash_bytes: bytes,
    token_address_bytes: bytes,
) -> bool:
    """
    Check if a record with the given (tx_hash, token_address) already exists in the database.
    """
    solver_slippage_connection = check_db_connection(
        solver_slippage_connection, "solver_slippage"
    )

    query = text(
        """
        SELECT 1 FROM raw_token_imbalances_temp
        WHERE tx_hash = :tx_hash AND token_address = :token_address
    """
    )
    try:
        with solver_slippage_connection.connect() as connection:
            result = connection.execute(
                query, {"tx_hash": tx_hash_bytes, "token_address": token_address_bytes}
            )
            record_exists = result.fetchone() is not None
            return record_exists
    except Exception as e:
        logger.error("Error checking record existence: %s", e)
        return False


def write_token_imbalances_to_db(
    chain_name: str,
    solver_slippage_connection: Engine,
    auction_id: int,
    block_number: int,
    tx_hash: str,
    token_address: str,
    imbalance: float,
) -> None:
    """
    Write token imbalances to the database if the (tx_hash, token_address) combination does not already exist.
    """
    solver_slippage_connection = check_db_connection(
        solver_slippage_connection, "solver_slippage"
    )

    tx_hash_bytes = bytes.fromhex(tx_hash[2:])
    token_address_bytes = bytes.fromhex(token_address[2:])
    if not record_exists(
        solver_slippage_connection, tx_hash_bytes, token_address_bytes
    ):
        insert_sql = text(
            """
            INSERT INTO raw_token_imbalances_temp (auction_id, chain_name, block_number, tx_hash, token_address, imbalance)
            VALUES (:auction_id, :chain_name, :block_number, :tx_hash, :token_address, :imbalance)
        """
        )
        try:
            with solver_slippage_connection.connect() as connection:
                connection.execute(
                    insert_sql,
                    {
                        "auction_id": auction_id,
                        "chain_name": chain_name,
                        "block_number": block_number,
                        "tx_hash": tx_hash_bytes,
                        "token_address": token_address_bytes,
                        "imbalance": imbalance,
                    },
                )
                connection.commit()
                logger.debug("Record inserted successfully.")
        except Exception as e:
            logger.error("Error inserting record: %s", e)
    else:
        logger.info(
            "Record with tx_hash %s and token_address %s already exists.",
            tx_hash,
            token_address,
        )


def process_transactions(chain_name: str) -> None:
    """
    Process transactions to compute imbalances for a given blockchain via chain name.
    """
    web3 = get_web3_instance()
    rt = RawTokenImbalances(web3, chain_name)
    solver_slippage_db_connection = create_db_connection("solver_slippage")
    start_block = get_start_block(chain_name, solver_slippage_db_connection, web3)
    previous_block = start_block
    unprocessed_txs: List[Tuple[str, int, int]] = []

    logger.info("%s Daemon started. Start block: %d", chain_name, start_block)
    while True:
        try:
            latest_block = get_finalized_block_number(web3)
            new_txs = fetch_tx_data(previous_block, latest_block, web3)
            # Add any unprocessed txs for processing, then clear list of unprocessed
            all_txs = new_txs + unprocessed_txs
            unprocessed_txs.clear()

            for tx, auction_id, block_number in all_txs:
                logger.info("Processing transaction on %s: %s", chain_name, tx)
                try:
                    imbalances = rt.compute_imbalances(tx)
                    # Append imbalances to a single log message
                    if imbalances is not None:
                        log_message = [f"Token Imbalances on {chain_name} for tx {tx}:"]
                        for token_address, imbalance in imbalances.items():
                            # Ignore tokens that have null imbalances
                            if imbalance != 0:
                                write_token_imbalances_to_db(
                                    chain_name,
                                    solver_slippage_db_connection,
                                    auction_id,
                                    block_number,
                                    tx,
                                    token_address,
                                    imbalance,
                                )
                                log_message.append(
                                    f"Token: {token_address}, Imbalance: {imbalance}"
                                )
                        logger.info("\n".join(log_message))
                    else:
                        raise ValueError("Imbalances computation returned None.")
                except ValueError as e:
                    logger.error("ValueError: %s", e)
                    unprocessed_txs.append((tx, auction_id, block_number))
            previous_block = latest_block + 1
        except ConnectionError as e:
            logger.error(
                "Connection error processing transactions on %s: %s", chain_name, e
            )
        except Exception as e:
            logger.error("Error processing transactions on %s: %s", chain_name, e)

        if CHAIN_SLEEP_TIME is not None:
            time.sleep(CHAIN_SLEEP_TIME)


def main() -> None:
    """
    Main function to start the daemon for a blockchain.
    """
    chain_name = os.getenv("CHAIN_NAME")
    if chain_name is None:
        logger.error("CHAIN_NAME environment variable is not set.")
        return
    process_transactions(chain_name)


if __name__ == "__main__":
    main()
