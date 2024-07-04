"""
Running this daemon computes raw imbalances for finalized blocks by calling imbalances_script.py.
"""
import time
from typing import List, Tuple
from threading import Thread
import psycopg2
import pandas as pd
from web3 import Web3
from sqlalchemy.engine import Engine
from src.imbalances_script import RawTokenImbalances
from src.config import (
    CHAIN_RPC_ENDPOINTS,
    CHAIN_SLEEP_TIMES,
    create_read_db_connection,
    create_write_db_connection,
    logger,
)


def write_token_imbalances_to_db(
    chain_name: str,
    write_db_connection,
    auction_id: int,
    tx_hash: str,
    token_address: str,
    imbalance,
):
    """
    Write token imbalances to the database.
    """
    try:
        cursor = write_db_connection.cursor()
        # Remove '0x' and then convert hex strings to bytes
        tx_hash_bytes = bytes.fromhex(tx_hash[2:])
        token_address_bytes = bytes.fromhex(token_address[2:])

        insert_sql = """
            INSERT INTO raw_token_imbalances (auction_id, chain_name, tx_hash, token_address, imbalance)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(
            insert_sql,
            (
                auction_id,
                chain_name,
                psycopg2.Binary(tx_hash_bytes),
                psycopg2.Binary(token_address_bytes),
                imbalance,
            ),
        )
        write_db_connection.commit()

        logger.info("Record inserted successfully.")
    except psycopg2.Error as e:
        logger.error("Error inserting record: %s", e)
    finally:
        cursor.close()


def get_web3_instance(chain_name: str) -> Web3:
    """
    returns a Web3 instance for the given blockchain via chain name.
    """
    return Web3(Web3.HTTPProvider(CHAIN_RPC_ENDPOINTS[chain_name]))


def get_finalized_block_number(web3: Web3) -> int:
    """
    Get the number of the most recent finalized block.
    """
    return web3.eth.block_number - 64


def fetch_transaction_hashes(
    read_db_connection: Engine, start_block: int, end_block: int
) -> List[str]:
    """Fetch transaction hashes beginning from start_block to end_block."""
    query = f"""
    SELECT tx_hash, auction_id
    FROM settlements 
    WHERE block_number >= {start_block}
    AND block_number <= {end_block}
    """

    db_data = pd.read_sql(query, read_db_connection)
    # converts hashes at memory location to hex
    db_data["tx_hash"] = db_data["tx_hash"].apply(lambda x: f"0x{x.hex()}")

    # return db_hashes['tx_hash'].tolist(), db_hashes['auction_id'].tolist()
    tx_hashes_auction_ids = [
        (row["tx_hash"], row["auction_id"]) for index, row in db_data.iterrows()
    ]
    return tx_hashes_auction_ids


def process_transactions(chain_name: str) -> None:
    """
    Process transactions to compute imbalances for a given blockchain via chain name.
    """
    web3 = get_web3_instance(chain_name)
    rt = RawTokenImbalances(web3, chain_name)
    sleep_time = CHAIN_SLEEP_TIMES.get(chain_name)
    read_db_connection = create_read_db_connection(chain_name)
    write_db_connection = create_write_db_connection()
    previous_block = get_finalized_block_number(web3)
    unprocessed_txs = []

    logger.info("%s Daemon started.", chain_name)

    while True:
        try:
            latest_block = get_finalized_block_number(web3)
            new_txs = fetch_transaction_hashes(
                read_db_connection, previous_block, latest_block
            )
            # add any unprocessed hashes for processing, then clear list of unprocessed
            all_txs = new_txs + unprocessed_txs
            unprocessed_txs.clear()

            for tx, auction_id in all_txs:
                logger.info("Processing transaction on %s: %s", chain_name, tx)
                try:
                    imbalances = rt.compute_imbalances(tx)
                    logger.info("Token Imbalances on %s:", chain_name)
                    for token_address, imbalance in imbalances.items():
                        write_token_imbalances_to_db(
                            chain_name,
                            write_db_connection,
                            auction_id,
                            tx,
                            token_address,
                            imbalance,
                        )
                        logger.info(
                            "Token: %s, Imbalance: %s", token_address, imbalance
                        )
                except ValueError as e:
                    logger.error("ValueError: %s", e)
                    unprocessed_txs.append(tx)

            previous_block = latest_block + 1
        except ConnectionError as e:
            logger.error(
                "Connection error processing transactions on %s: %s", chain_name, e
            )
        except Exception as e:
            logger.error("Error processing transactions on %s: %s", chain_name, e)

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
