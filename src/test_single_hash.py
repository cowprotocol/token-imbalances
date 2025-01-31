from hexbytes import HexBytes
from web3 import Web3
from src.raw_imbalances import RawTokenImbalances
from src.price_providers.price_feed import PriceFeed
from src.fees.compute_fees import compute_all_fees_of_batch
from src.transaction_processor import calculate_slippage
from src.helpers.config import get_web3_instance, logger
from contracts.erc20_abi import erc20_abi


def log_token_data(title: str, data: dict, name: str):
    logger.info(title)
    for token, value in data.items():
        logger.info(f"Token Address: {token}, {name}: {value}")


class Compute:
    """
    Class that allows one to fetch imbalances, fees, final slippage via a tx hash.
    """

    def __init__(self):
        self.web3 = get_web3_instance()
        self.imbalances = RawTokenImbalances(self.web3, "mainnet")
        self.price_providers = PriceFeed()

    def compute_data(self, tx_hash: str):
        token_imbalances = self.imbalances.compute_token_imbalances(tx_hash)
        protocol_fees, partner_fees, network_fees = compute_all_fees_of_batch(
            HexBytes(tx_hash)
        )
        slippage = calculate_slippage(token_imbalances, protocol_fees, network_fees)
        eth_slippage = self.calculate_slippage_in_eth(slippage, tx_hash)

        self.log_results(
            token_imbalances, protocol_fees, network_fees, slippage, eth_slippage
        )

    def calculate_slippage_in_eth(self, slippage: dict, tx_hash: str) -> dict:
        """Calculate slippage in ETH."""
        eth_slippage = {}
        receipt = self.web3.eth.get_transaction_receipt(tx_hash)
        if receipt:
            block_number = receipt.blockNumber
            for token_address, amt in slippage.items():
                if amt != 0:
                    price_params = {
                        "block_number": block_number,
                        "token_address": token_address,
                        "tx_hash": tx_hash,
                    }
                    price_data = self.price_providers.get_price(price_params)
                    if price_data:
                        price, _ = price_data
                        decimals = self.get_token_decimals(token_address)
                        slippage_in_eth = price * (amt / (10**decimals))
                        eth_slippage[token_address] = slippage_in_eth
        return eth_slippage

    def get_token_decimals(self, token_address: str) -> int:
        contract = self.web3.eth.contract(
            address=Web3.to_checksum_address(token_address), abi=erc20_abi
        )
        return contract.functions.decimals().call()

    def log_results(
        self,
        token_imbalances: dict,
        protocol_fees: dict,
        network_fees: dict,
        slippage: dict,
        eth_slippage: dict,
    ):
        log_token_data("Raw Imbalances:", token_imbalances, "Raw Imbalance")
        log_token_data("Protocol Fees:", protocol_fees, "Protocol Fee")
        log_token_data("Network Fees:", network_fees, "Network Fee")
        log_token_data("Raw Slippage Calculation:", slippage, "Raw Slippage")
        log_token_data("Slippage in ETH", eth_slippage, "Slippage")


def main():
    compute = Compute()
    # e.g. input: 0x980fa3f8ff95c504ba61e054e5c3e50ea36b892f865703b8a665564ac0beb1f4
    compute.compute_data(input("tx hash: "))


if __name__ == "__main__":
    main()
