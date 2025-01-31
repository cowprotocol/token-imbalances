"""
Script can be used as a sanity test to compare raw imbalances via RawTokenImbalances class
and the BalanceOfImbalances class.
"""

import time
from web3 import Web3
from src.helpers.config import ETHEREUM_NODE_URL
from src.raw_imbalances import RawTokenImbalances
from src.balanceof_imbalances import BalanceOfImbalances
from src.daemon import get_web3_instance, create_db_connection, fetch_transaction_hashes

RED_COLOR = "\033[91m"
RESET_COLOR = "\033[0m"


def remove_zero_balances(balances: dict) -> dict:
    """Remove entries with zero balance for all tokens."""
    return {token: balance for token, balance in balances.items() if balance != 0}


def compare_imbalances(tx_hash: str, web3: Web3) -> None:
    """Compare imbalances computed by RawTokenImbalances and BalanceOfImbalances."""
    raw_imbalances = RawTokenImbalances(web3, "Ethereum")
    balanceof_imbalances = BalanceOfImbalances(ETHEREUM_NODE_URL)

    raw_result = raw_imbalances.compute_imbalances(tx_hash)
    balanceof_result = balanceof_imbalances.compute_imbalances(tx_hash)

    # Remove entries for native ETH with balance 0
    raw_result = remove_zero_balances(raw_result)
    balanceof_result = remove_zero_balances(balanceof_result)

    if raw_result != balanceof_result:
        print(
            f"{RED_COLOR}Imbalances do not match for tx: {tx_hash}.\nRaw: {raw_result}\nBalanceOf: {balanceof_result}{RESET_COLOR}"
        )
    else:
        print(f"Imbalances match for transaction {tx_hash}.")


def main() -> None:
    start_block = int(input("Enter start block number: "))
    end_block = int(input("Enter end block number: "))

    web3 = get_web3_instance("Ethereum")
    db_connection = create_db_connection("Ethereum")
    tx_hashes = fetch_transaction_hashes(db_connection, start_block, end_block)

    for tx_hash in tx_hashes:
        try:
            compare_imbalances(tx_hash, web3)
            time.sleep(1)  # Delay to avoid rate limits

        except Exception as e:
            print(f"Error comparing imbalances for tx {tx_hash}: {e}")


if __name__ == "__main__":
    main()
