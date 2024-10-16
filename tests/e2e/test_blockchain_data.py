from os import getenv

from web3 import Web3

from src.helpers.blockchain_data import BlockchainData


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
