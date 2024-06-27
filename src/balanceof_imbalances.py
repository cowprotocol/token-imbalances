from web3 import Web3
from src.config import INFURA_KEY
from src.constants import (SETTLEMENT_CONTRACT_ADDRESS, NATIVE_ETH_TOKEN_ADDRESS)
from contracts.erc20_abi import erc20_abi

infura_url = f'https://mainnet.infura.io/v3/{INFURA_KEY}'
web3 = Web3(Web3.HTTPProvider(infura_url))

def get_token_balance(token_address, account, block_identifier):
    token_contract = web3.eth.contract(address=token_address, abi=erc20_abi)
    try:
        token_balance = token_contract.functions.balanceOf(account).call(block_identifier=block_identifier)
        return token_balance
    except Exception as e:
        # print(f"Error fetching balance for token {token_address}: {e}")
        return None

def get_eth_balance(account, block_identifier):
    """Get the ETH balance for a given account and block number."""
    try:
        return web3.eth.get_balance(account, block_identifier=block_identifier)
    except Exception as e:
        print(f"Error fetching ETH balance: {e}")
        return None

def extract_token_addresses(tx_receipt):
    token_addresses = set()
    for log in tx_receipt['logs']:
        # check for transfer events
        if log['topics'][0].hex() == web3.keccak(text="Transfer(address,address,uint256)").hex()  or web3.keccak(text="ERC20Transfer(address,address,uint256)").hex():
            token_addresses.add(log['address'])
    return token_addresses

def get_transaction_receipt(tx_hash):
    """Fetch the transaction receipt for the given hash."""
    try:
        return web3.eth.get_transaction_receipt(tx_hash)
    except Exception as e:
        print(f"Error fetching transaction receipt for hash {tx_hash}: {e}")
        return None

def get_balances(token_addresses, block_number):
    """Get balances for all tokens at the given block number."""
    balances = {}
    balances[NATIVE_ETH_TOKEN_ADDRESS] = get_eth_balance(SETTLEMENT_CONTRACT_ADDRESS, block_number)
    
    for token_address in token_addresses:
        balances[token_address] = get_token_balance(token_address, SETTLEMENT_CONTRACT_ADDRESS, block_number)
    
    return balances

def calculate_imbalances(prev_balances, final_balances):
    """Calculate imbalances between previous and final balances."""
    imbalances = {}
    for token_address in prev_balances:
        if prev_balances[token_address] is not None and final_balances[token_address] is not None:
            imbalance = final_balances[token_address] - prev_balances[token_address]
            imbalances[token_address] = imbalance
    return imbalances

def compute_imbalances(tx_hash):
    """Compute token imbalances before and after a transaction."""
    tx_receipt = get_transaction_receipt(tx_hash)
    if tx_receipt is None:
        return {}

    token_addresses = extract_token_addresses(tx_receipt)

    if not token_addresses:
        print("No tokens involved in this transaction.")
        return {}

    prev_block = tx_receipt['blockNumber'] - 1
    final_block = tx_receipt['blockNumber']

    prev_balances = get_balances(token_addresses, prev_block)
    final_balances = get_balances(token_addresses, final_block)

    imbalances = calculate_imbalances(prev_balances, final_balances)
    
    return imbalances

def main():
    tx_hash = input("Tx hash: ")
    imbalances = compute_imbalances(tx_hash)
    print(imbalances)

if __name__ == "__main__":
    main()
