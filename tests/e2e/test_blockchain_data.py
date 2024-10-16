from os import getenv

from web3 import Web3

from src.helpers.blockchain_data import BlockchainData
from src.raw_imbalances import RawTokenImbalances


def tests_get_tx_hashes_blocks():
    web3 = Web3(Web3.HTTPProvider(getenv("NODE_URL")))
    blockchain = BlockchainData(web3)
    start_block = 20892118
    end_block = start_block
    res = blockchain.get_tx_hashes_blocks(start_block, end_block)
    assert res[0] == (
        "0xb75e03b63d4f06c56549effd503e1e37f3ccfc3c00e6985a5aacc9b0534d7c5c",
        20892118,
    )


def test_get_transaction_timestamp():
    web3 = Web3(Web3.HTTPProvider(getenv("NODE_URL")))
    blockchain = BlockchainData(web3)
    tx_hash = "0xb75e03b63d4f06c56549effd503e1e37f3ccfc3c00e6985a5aacc9b0534d7c5c"

    transaction_timestamp = blockchain.get_transaction_timestamp(tx_hash)

    assert transaction_timestamp == (tx_hash, 1728044411)


def test_get_transaction_tokens():
    web3 = Web3(Web3.HTTPProvider(getenv("NODE_URL")))
    imbalances = RawTokenImbalances(web3, "mainnet")
    tx_hash = "0xb75e03b63d4f06c56549effd503e1e37f3ccfc3c00e6985a5aacc9b0534d7c5c"

    transaction_tokens = imbalances.get_transaction_tokens(tx_hash)

    assert all(h == tx_hash for h, _ in transaction_tokens)
    assert set(token_address for _, token_address in transaction_tokens) == {
        "0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9",
        "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "0x812Ba41e071C7b7fA4EBcFB62dF5F45f6fA853Ee",
        "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "0xdAC17F958D2ee523a2206206994597C13D831ec7",
        "0xEE2a03Aa6Dacf51C18679C516ad5283d8E7C2637",
        "0x72e4f9F808C49A2a61dE9C5896298920Dc4EEEa9",
    }
