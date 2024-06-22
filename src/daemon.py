import os
import time
from web3 import Web3
from multiprocessing import Process
from dotenv import load_dotenv
from src.constants import SETTLEMENT_CONTRACT_ADDRESS
from src.imbalances_script import RawTokenImbalances

load_dotenv()
INFURA_KEY = os.getenv('INFURA_KEY')

CHAIN_RPC_ENDPOINTS = {
    'Ethereum': f'https://mainnet.infura.io/v3/{INFURA_KEY}',
    'Gnosis': 'https://rpc.gnosischain.com'
}

# Sleep times for each chain in seconds
CHAIN_SLEEP_TIMES = {
    'Ethereum': 30,
    'Gnosis': 60
}

def get_web3_instance(chain_name):
    return Web3(Web3.HTTPProvider(CHAIN_RPC_ENDPOINTS[chain_name]))

def get_transactions_involving_contract(web3, from_block, to_block, contract_address):
    transactions = []
    for block_number in range(from_block, to_block + 1):
        block = web3.eth.get_block(block_number, full_transactions=True)
        for tx in block.transactions:
            if tx.to and Web3.to_checksum_address(tx.to) == contract_address:
                transactions.append(tx)
    return transactions

def process_transactions(chain_name):
    web3 = get_web3_instance(chain_name)
    previous_block = web3.eth.block_number
    sleep_time = CHAIN_SLEEP_TIMES.get(chain_name, 30)

    print(f"{chain_name} Daemon started, sleeping for {sleep_time} seconds between checks.")
    
    rt = RawTokenImbalances()

    while True:
        latest_block = web3.eth.block_number
        if previous_block == latest_block:
            print(f'No new blocks on {chain_name}.')
            time.sleep(sleep_time)
            continue
        try:
            transactions = get_transactions_involving_contract(web3, previous_block + 1, latest_block, SETTLEMENT_CONTRACT_ADDRESS)
        except Exception as e:
            print(f"Error fetching transactions on {chain_name}: {e}")
            break

        if not transactions:
            print(f'No relevant transactions found on {chain_name}.')
        else:
            for tx in transactions:
                print(f'Processing transaction on {chain_name}: {tx.hash.hex()}')
                try:
                    imbalances, _ = rt.compute_imbalances(tx.hash.hex())
                    print(f"Token Imbalances on {chain_name}:")
                    for token_address, imbalance in imbalances.items():
                        print(f"Token: {token_address}, Imbalance: {imbalance}")
                except ValueError as e:
                    print(e)

        previous_block = latest_block
        time.sleep(sleep_time)

def main():
    processes = []
    
    for chain_name in CHAIN_RPC_ENDPOINTS.keys():
        process = Process(target=process_transactions, args=(chain_name,), daemon=True)
        process.start()
        processes.append(process)
    
    for process in processes:
        process.join()

if __name__ == "__main__":
    main()
