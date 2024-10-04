from os import getenv, environ
from unittest.mock import patch

from dotenv import load_dotenv
import pytest
from web3 import Web3

load_dotenv()


@pytest.fixture()
def set_env_variables(monkeypatch):
    """Set `REMOVE_SOLVER_PK` to a string so that blacklisting can be called."""
    with patch.dict(environ, clear=True):
        envvars = {
            "CHAIN_SLEEP_TIME": "1",
        }
        for k, v in envvars.items():
            monkeypatch.setenv(k, v)
        yield  # This is the magical bit which restore the environment after


def tests_get_tx_hashes_blocks(set_env_variables):
    # import has to happen after patching environment variable
    from src.helpers.blockchain_data import BlockchainData

    web3 = Web3(Web3.HTTPProvider(getenv("NODE_URL")))
    blockchain = BlockchainData(web3)
    start_block = 20892118
    end_block = start_block
    res = blockchain.get_tx_hashes_blocks(start_block, end_block)
    assert res[0] == (
        "0xb75e03b63d4f06c56549effd503e1e37f3ccfc3c00e6985a5aacc9b0534d7c5c",
        20892118,
    )
