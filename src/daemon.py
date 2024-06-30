import os
import time
import pandas as pd
from web3 import Web3
from typing import List
from threading import Thread
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from src.imbalances_script import RawTokenImbalances
from src.config import CHAIN_RPC_ENDPOINTS, CHAIN_SLEEP_TIMES

def get_web3_instance(chain_name: str) -> Web3:
    return Web3(Web3.HTTPProvider(CHAIN_RPC_ENDPOINTS[chain_name]))

def get_finalized_block_number(web3: Web3) -> int:
    return web3.eth.block_number - 64

def create_db_connection(chain_name: str):
    """function that creates a connection to the CoW db.""" 
    if chain_name == 'Ethereum':
        prod_url = os.getenv("ETHEREUM_DB_URL")
    elif chain_name == 'Gnosis':
        prod_url = os.getenv("GNOSIS_DB_URL")

    return create_engine(f"postgresql+psycopg2://{prod_url}")

def fetch_transaction_hashes(db_connection: Engine, start_block: int, end_block: int) -> List[str]:
    """Fetch transaction hashes beginning start_block."""
    query = f"""
    SELECT tx_hash 
    FROM settlements 
    WHERE block_number >= {start_block}
    AND block_number <= {end_block}
    """

    prod_hashes = pd.read_sql(query, db_connection)
    # converts hashes at memory location to hex 
    prod_hashes['tx_hash'] = prod_hashes['tx_hash'].apply(lambda x: f"0x{x.hex()}")
    
    return prod_hashes['tx_hash'].tolist()

def process_transactions(chain_name: str) -> None:
    web3 = get_web3_instance(chain_name)
    rt = RawTokenImbalances(web3, chain_name)
    sleep_time = CHAIN_SLEEP_TIMES.get(chain_name)
    db_connection = create_db_connection(chain_name)

    previous_block = get_finalized_block_number(web3)
    unprocessed_txs = []

    print(f"{chain_name} Daemon started.")
    
    while True:
        try:
            latest_block = get_finalized_block_number(web3)
            new_txs = fetch_transaction_hashes(db_connection, previous_block, latest_block)
            # add any unprocessed hashes for processing, then clear list of unprocessed
            all_txs = new_txs + unprocessed_txs
            unprocessed_txs.clear()

            for tx in all_txs:
                print(f'Processing transaction on {chain_name}: {tx}')
                try:
                    imbalances = rt.compute_imbalances(tx)
                    print(f"Token Imbalances on {chain_name}:")
                    for token_address, imbalance in imbalances.items():
                        print(f"Token: {token_address}, Imbalance: {imbalance}")
                except ValueError as e:
                    print(e)
                    unprocessed_txs.append(tx)
                  
            print("Done checks..")
            previous_block = latest_block + 1
        except ConnectionError as e:
            print(f"Connection error processing transactions on {chain_name}: {e}")
        except Exception as e:
            print(f"Error processing transactions on {chain_name}: {e}")

        time.sleep(sleep_time)

def main() -> None:
    threads = []
    
    for chain_name in CHAIN_RPC_ENDPOINTS.keys():
        thread = Thread(target=process_transactions, args=(chain_name,), daemon=True)
        thread.start()
        threads.append(thread)
    
    for thread in threads:
        thread.join()

if __name__ == "__main__":
    main()
