from os import getenv, environ
from unittest.mock import patch

from hexbytes import HexBytes
import pytest
from sqlalchemy import create_engine, text


@pytest.fixture()
def set_env_variables(monkeypatch):
    with patch.dict(environ, clear=True):
        envvars = {
            "CHAIN_SLEEP_TIME": "1",
        }
        for k, v in envvars.items():
            monkeypatch.setenv(k, v)
        yield  # This is the magical bit which restore the environment after


def tests_write_transaction_timestamp(set_env_variables):
    # import has to happen after patching environment variable
    from src.helpers.database import Database

    engine = create_engine(
        f"postgresql+psycopg2://postgres:postgres@localhost:5432/mainnet"
    )
    db = Database(engine, "mainnet")
    # write data
    db.write_transaction_timestamp(
        (
            "0xb75e03b63d4f06c56549effd503e1e37f3ccfc3c00e6985a5aacc9b0534d7c5c",
            1728044411,
        )
    )
    # read data
    with engine.connect() as conn:
        res = conn.execute(
            text("SELECT tx_hash, time FROM transaction_timestamps")
        ).one()
    assert (
        "0x" + bytes(res[0]).hex()
        == "0xb75e03b63d4f06c56549effd503e1e37f3ccfc3c00e6985a5aacc9b0534d7c5c"
    )
    assert res[1].timestamp() == 1728044411


def tests_write_transaction_tokens(set_env_variables):
    # import has to happen after patching environment variable
    from src.helpers.database import Database

    engine = create_engine(
        f"postgresql+psycopg2://postgres:postgres@localhost:5432/mainnet"
    )
    db = Database(engine, "mainnet")
    transaction_tokens = [
        (
            "0xb75e03b63d4f06c56549effd503e1e37f3ccfc3c00e6985a5aacc9b0534d7c5c",
            "0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9",
        ),
        (
            "0xb75e03b63d4f06c56549effd503e1e37f3ccfc3c00e6985a5aacc9b0534d7c5c",
            "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        ),
    ]
    # write data
    db.write_transaction_tokens(transaction_tokens)
    # read data
    with engine.connect() as conn:
        res = conn.execute(
            text("SELECT tx_hash, token_address FROM transaction_tokens")
        ).all()
    for i, (tx_hash, token_address) in enumerate(transaction_tokens):
        assert HexBytes(res[i][0]) == HexBytes(tx_hash)
        assert HexBytes(res[i][1]) == HexBytes(token_address)
