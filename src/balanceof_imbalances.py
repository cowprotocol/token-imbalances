from web3 import Web3
from web3.types import TxReceipt, HexStr
from eth_typing import ChecksumAddress
from typing import Dict, Optional, Set
from src.helpers.config import NODE_URL
from src.constants import SETTLEMENT_CONTRACT_ADDRESS, NATIVE_ETH_TOKEN_ADDRESS
from contracts.erc20_abi import erc20_abi

# conducting sanity test only for ethereum mainnet transactions


class BalanceOfImbalances:
    def __init__(self, NODE_URL: str):
        self.web3 = Web3(Web3.HTTPProvider(NODE_URL))

    def get_token_balance(
        self,
        token_address: ChecksumAddress,
        account: ChecksumAddress,
        block_identifier: int,
    ) -> Optional[int]:
        """Retrieve the ERC-20 token balance of an account at a given block."""
        token_contract = self.web3.eth.contract(address=token_address, abi=erc20_abi)
        try:
            return token_contract.functions.balanceOf(account).call(
                block_identifier=block_identifier
            )
        except Exception as e:
            print(f"Error fetching balance for token {token_address}: {e}")
            return None

    def get_eth_balance(
        self, account: ChecksumAddress, block_identifier: int
    ) -> Optional[int]:
        """Get the ETH balance for a given account and block number."""
        try:
            return self.web3.eth.get_balance(account, block_identifier=block_identifier)
        except Exception as e:
            print(f"Error fetching ETH balance: {e}")
            return None

    def extract_token_addresses(self, tx_receipt: TxReceipt) -> Set[ChecksumAddress]:
        """Extract unique token addresses from 'Transfer' events in a transaction receipt."""
        token_addresses: Set[ChecksumAddress] = set()
        transfer_topics = {
            self.web3.keccak(text="Transfer(address,address,uint256)").hex(),
            self.web3.keccak(text="ERC20Transfer(address,address,uint256)").hex(),
            self.web3.keccak(text="Withdrawal(address,uint256)").hex(),
        }
        for log in tx_receipt["logs"]:
            if log["topics"][0].hex() in transfer_topics:
                token_addresses.add(self.web3.to_checksum_address(log["address"]))
        return token_addresses

    def get_transaction_receipt(self, tx_hash: HexStr) -> Optional[TxReceipt]:
        """Fetch the transaction receipt for the given hash."""
        try:
            return self.web3.eth.get_transaction_receipt(tx_hash)
        except Exception as e:
            print(f"Error fetching transaction receipt for hash {tx_hash}: {e}")
            return None

    def get_balances(
        self, token_addresses: Set[ChecksumAddress], block_number: int
    ) -> Dict[ChecksumAddress, Optional[int]]:
        """Get balances for all tokens at the given block number."""
        balances: Dict[ChecksumAddress, Optional[int]] = {}
        balances[
            self.web3.to_checksum_address(NATIVE_ETH_TOKEN_ADDRESS)
        ] = self.get_eth_balance(
            self.web3.to_checksum_address(SETTLEMENT_CONTRACT_ADDRESS), block_number
        )

        for token_address in token_addresses:
            balances[token_address] = self.get_token_balance(
                token_address,
                self.web3.to_checksum_address(SETTLEMENT_CONTRACT_ADDRESS),
                block_number,
            )

        return balances

    def calculate_imbalances(
        self,
        prev_balances: Dict[ChecksumAddress, Optional[int]],
        final_balances: Dict[ChecksumAddress, Optional[int]],
    ) -> Dict[ChecksumAddress, int]:
        """Calculate imbalances between previous and final balances."""
        imbalances: Dict[ChecksumAddress, int] = {}
        for token_address in prev_balances:
            if (
                prev_balances[token_address] is not None
                and final_balances[token_address] is not None
            ):
                # need to ensure prev_balance and final_balance contain values
                # to prevent subtraction from None
                prev_balance = prev_balances[token_address]
                assert prev_balance is not None
                final_balance = final_balances[token_address]
                assert final_balance is not None
                imbalance = final_balance - prev_balance
                imbalances[token_address] = imbalance
        return imbalances

    def compute_imbalances(self, tx_hash: HexStr) -> Dict[ChecksumAddress, int]:
        """Compute token imbalances before and after a transaction."""
        tx_receipt = self.get_transaction_receipt(tx_hash)
        if tx_receipt is None:
            return {}

        token_addresses = self.extract_token_addresses(tx_receipt)
        if not token_addresses:
            print("No tokens involved in this transaction.")
            return {}

        prev_block = tx_receipt["blockNumber"] - 1
        final_block = tx_receipt["blockNumber"]

        prev_balances = self.get_balances(token_addresses, prev_block)
        final_balances = self.get_balances(token_addresses, final_block)

        return self.calculate_imbalances(prev_balances, final_balances)


def main():
    tx_hash = input("Enter transaction hash: ")
    bo = BalanceOfImbalances(NODE_URL)
    imbalances = bo.compute_imbalances(tx_hash)
    print("Token Imbalances:")
    for token_address, imbalance in imbalances.items():
        print(f"Token: {token_address}, Imbalance: {imbalance}")


if __name__ == "__main__":
    main()
