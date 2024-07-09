"""
Running this daemon computes raw imbalances for finalized blocks by calling imbalances_script.py.
"""

import time
from typing import List, Tuple, Any
from threading import Thread
import psycopg2
import pandas as pd
from web3 import Web3
from sqlalchemy.engine import Engine
from src.imbalances_script import RawTokenImbalances
from src.config import (
    CHAIN_RPC_ENDPOINTS,
    CHAIN_SLEEP_TIMES,
    create_backend_db_connection,
    create_solver_slippage_db_connection,
    check_db_connection,
    logger,
)


def get_web3_instance(chain_name: str) -> Web3:
    """
    returns a Web3 instance for the given blockchain via chain name.
    """
    return Web3(Web3.HTTPProvider(CHAIN_RPC_ENDPOINTS[chain_name]))


def get_finalized_block_number(web3: Web3) -> int:
    """
    Get the number of the most recent finalized block.
    """
    return web3.eth.block_number - 67


def fetch_tx_data(
    backend_db_connection: Engine, chain_name: str, start_block: int, end_block: int
) -> List[Tuple[str, int, int]]:
    """Fetch transaction hashes beginning from start_block to end_block."""
    backend_db_connection = check_db_connection(backend_db_connection, chain_name)
    query = f"""
    SELECT tx_hash, auction_id, block_number
    FROM settlements
    WHERE block_number >= {start_block}
    AND block_number <= {end_block}
    """
    db_data = pd.read_sql(query, backend_db_connection)
    # converts hashes at memory location to hex
    db_data["tx_hash"] = db_data["tx_hash"].apply(lambda x: f"0x{x.hex()}")

    # return (tx hash, auction id) as tx_data
    tx_data = [
        (row["tx_hash"], row["auction_id"], row["block_number"])
        for index, row in db_data.iterrows()
    ]
    return tx_data


def record_exists(
    solver_slippage_db_connection: Any,
    tx_hash_bytes: bytes,
    token_address_bytes: bytes,
) -> bool:
    """
    Check if a record with the given (tx_hash, token_address) already exists in the database.
    """
    solver_slippage_db_connection = check_db_connection(solver_slippage_db_connection)
    try:
        cursor = solver_slippage_db_connection.cursor()
        # check if the record exists
        check_sql = """
            SELECT 1 FROM raw_token_imbalances
            WHERE tx_hash = %s AND token_address = %s
        """
        cursor.execute(
            check_sql,
            (psycopg2.Binary(tx_hash_bytes), psycopg2.Binary(token_address_bytes)),
        )
        record_exists = cursor.fetchone()
        return record_exists is not None
    except psycopg2.Error as e:
        logger.error("Error checking record existence: %s", e)
        return False
    finally:
        cursor.close()


def write_token_imbalances_to_db(
    chain_name: str,
    solver_slippage_db_connection: Any,
    auction_id: int,
    block_number: int,
    tx_hash: str,
    token_address: str,
    imbalance: float,
) -> None:
    """
    Write token imbalances to the database if the (tx_hash, token_address) combination does not already exist.
    """
    solver_slippage_db_connection = check_db_connection(solver_slippage_db_connection)
    tx_hash_bytes = bytes.fromhex(tx_hash[2:])
    token_address_bytes = bytes.fromhex(token_address[2:])
    if not record_exists(
        solver_slippage_db_connection, tx_hash_bytes, token_address_bytes
    ):
        try:
            cursor = solver_slippage_db_connection.cursor()
            insert_sql = """
                INSERT INTO raw_token_imbalances (auction_id, chain_name, block_number, tx_hash, token_address, imbalance)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(
                insert_sql,
                (
                    auction_id,
                    chain_name,
                    block_number,
                    psycopg2.Binary(tx_hash_bytes),
                    psycopg2.Binary(token_address_bytes),
                    imbalance,
                ),
            )
            solver_slippage_db_connection.commit()
            logger.debug("Record inserted successfully.")
        except psycopg2.Error as e:
            logger.error("Error inserting record: %s", e)
        finally:
            cursor.close()
    else:
        logger.info(
            "Record with tx_hash %s and token_address %s already exists.",
            tx_hash,
            token_address,
        )


def get_start_block(
    chain_name: str, solver_slippage_db_connection: Any, web3: Web3
) -> int:
    """
    Retrieve the most recent block already present in raw_token_imbalances table,
    delete entries for that block, and return this block number as start_block.
    If no entries are present, fallback to get_finalized_block_number().
    """
    try:
        solver_slippage_db_connection = check_db_connection(
            solver_slippage_db_connection
        )

        # query to get the maximum block number present in the table for the given chain_name
        query_max_block = """
            SELECT MAX(block_number) FROM raw_token_imbalances
            WHERE chain_name = %s
        """

        cursor = solver_slippage_db_connection.cursor()
        cursor.execute(query_max_block, (chain_name,))
        max_block = cursor.fetchone()[0]  # Fetch the maximum block number
        if max_block is not None:
            logger.debug(f"Fetched max block number from database: {max_block}")
        # If no entries present, fallback to get_finalized_block_number()
        if max_block is None:
            cursor.close()
            return get_finalized_block_number(web3)

        # delete entries for the max block from the table
        delete_sql = """
            DELETE FROM raw_token_imbalances WHERE chain_name = %s AND block_number = %s
        """
        try:
            cursor.execute(delete_sql, (chain_name, max_block))
            solver_slippage_db_connection.commit()
            logger.debug(f"Successfully deleted entries for block number: {max_block}")
        except Exception as e:
            logger.debug(f"Failed to delete entries for block number {max_block}: {e}")

        cursor.close()
        return max_block

    except psycopg2.Error as e:
        logger.error("Error accessing database: %s", e)
        # Fallback to get_finalized_block_number() in case of any error
        return get_finalized_block_number(web3)
    finally:
        solver_slippage_db_connection.close()  # Close the database connection


def process_transactions(chain_name: str) -> None:
    """
    Process transactions to compute imbalances for a given blockchain via chain name.
    """
    web3 = get_web3_instance(chain_name)
    rt = RawTokenImbalances(web3, chain_name)
    sleep_time = CHAIN_SLEEP_TIMES.get(chain_name)
    backend_db_connection = create_backend_db_connection(chain_name)
    solver_slippage_db_connection = create_solver_slippage_db_connection()
    start_block = get_start_block(chain_name, solver_slippage_db_connection, web3)
    previous_block = start_block
    unprocessed_txs: List[Tuple[str, int, int]] = []

    logger.info("%s Daemon started. Start block: %d", chain_name, start_block)
    while True:
        try:
            latest_block = get_finalized_block_number(web3)
            new_txs = fetch_tx_data(
                backend_db_connection, chain_name, previous_block, latest_block
            )
            # add any unprocessed txs for processing, then clear list of unprocessed
            all_txs = new_txs + unprocessed_txs
            unprocessed_txs.clear()

            for tx, auction_id, block_number in all_txs:
                logger.info("Processing transaction on %s: %s", chain_name, tx)
                try:
                    imbalances = rt.compute_imbalances(tx)
                    # append imbalances to a single log message
                    log_message = [f"Token Imbalances on {chain_name} for tx {tx}:"]
                    for token_address, imbalance in imbalances.items():
                        # ignore tokens that have null imbalances
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
        if sleep_time is not None:
            time.sleep(sleep_time)


def main() -> None:
    """
    Main function to start the daemon threads for each blockchain.
    """
    threads = []

    for chain_name in CHAIN_RPC_ENDPOINTS.keys():
        thread = Thread(target=process_transactions, args=(chain_name,), daemon=True)
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()


if __name__ == "__main__":
    main()
