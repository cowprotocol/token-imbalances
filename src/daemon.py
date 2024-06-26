import os
import time
import pandas as pd
from web3 import Web3
from threading import Thread
from sqlalchemy import create_engine
from dotenv import load_dotenv
from src.imbalances_script import RawTokenImbalances

load_dotenv()
INFURA_KEY = os.getenv('INFURA_KEY')

CHAIN_RPC_ENDPOINTS = {
    'Ethereum': f'https://mainnet.infura.io/v3/{INFURA_KEY}',
    'Gnosis': 'https://rpc.gnosis.gateway.fm'
}

CHAIN_SLEEP_TIMES = {
    'Ethereum': 60,
    'Gnosis': 120
}

def get_web3_instance(chain_name):
    return Web3(Web3.HTTPProvider(CHAIN_RPC_ENDPOINTS[chain_name]))

def get_finalized_block_number(web3):
    return web3.eth.block_number - 64

def create_db_connection(chain_name):
    """Helper function that creates a connection to the prod db."""
    db_name = "mainnet" if chain_name == 'Ethereum' else "xdai"
    db_url = os.getenv("PROD_DB_URL").format(chain=db_name)
    
    return create_engine(f"postgresql+psycopg2://{db_url}")

def fetch_transaction_hashes(chain_name, start_block, end_block):
    """Fetch transaction hashes beginning start_block."""
    prod_connection = create_db_connection(chain_name)
    query = f"""
    SELECT tx_hash 
    FROM settlements 
    WHERE block_number >= {start_block} 
    AND block_number<={end_block}
    """

    res = pd.read_sql(query, prod_connection)
    
    # converts hashes at memory location to hex 
    res['tx_hash'] = res['tx_hash'].apply(lambda x: f"0x{x.hex()}")
    
    return res['tx_hash'].tolist()

def process_transactions(chain_name):
    web3 = get_web3_instance(chain_name)
    rt = RawTokenImbalances()
    sleep_time = CHAIN_SLEEP_TIMES.get(chain_name)

    previous_block = get_finalized_block_number(web3)
    unsuccessful_txs = []

    print(f"{chain_name} Daemon started.")
    
    while True:
        try:
            latest_block = get_finalized_block_number(web3)
            new_txs = fetch_transaction_hashes(chain_name, previous_block, latest_block)
            all_txs = new_txs + unsuccessful_txs

            for tx in all_txs:
                print(f'Processing transaction on {chain_name}: {tx}')
                try:
                    imbalances, _ = rt.compute_imbalances(tx)
                    print(f"Token Imbalances on {chain_name}:")
                    for token_address, imbalance in imbalances.items():
                        print(f"Token: {token_address}, Imbalance: {imbalance}")
                except ValueError as e:
                    print(e)
                    unsuccessful_txs.append(tx)
                  
            print("Done checks..")
            previous_block = latest_block + 1
        except ConnectionError as e:
            print(f"Connection error processing transactions on {chain_name}: {e}")
        except Exception as e:
            print(f"Error processing transactions on {chain_name}: {e}")

        time.sleep(sleep_time)

def main():
    threads = []
    
    for chain_name in CHAIN_RPC_ENDPOINTS.keys():
        thread = Thread(target=process_transactions, args=(chain_name,), daemon=True)
        thread.start()
        threads.append(thread)
    
    for thread in threads:
        thread.join()

if __name__ == "__main__":
    main()
