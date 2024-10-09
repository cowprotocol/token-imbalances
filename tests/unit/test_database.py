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
    # truncate table
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE transaction_timestamps"))
        conn.commit()
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
    # truncate table
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE transaction_tokens"))
        conn.commit()
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


def test_get_latest_transaction(set_env_variables):
    # import has to happen after patching environment variable
    from src.helpers.database import Database

    engine = create_engine(
        f"postgresql+psycopg2://postgres:postgres@localhost:5432/mainnet"
    )
    db = Database(engine, "mainnet")
    # truncate table
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE transaction_timestamps"))
        conn.commit()
    # check that empty table returns None
    assert db.get_latest_transaction() is None
    # write data
    db.write_transaction_timestamp(
        (
            "0x99F10B2DE2B04DFC729B6C46FC5510C44424C213106ED77C80691FA0DD08F3CF",
            1728459935,
        )
    )
    db.write_transaction_timestamp(
        (
            "0xDFBB14E8F0E47FFC105A16043B2ECF536B323AC3B3B1D319A2D635E392E75BB9",
            1728459995,  # latest time stamp
        )
    )
    db.write_transaction_timestamp(
        (
            "0xF153C9EF2D54C656182B9BD0484B4C1C1A317781656EAF615FA0A92D7C3AFDF7",
            1728459959,
        )
    )
    # read data
    tx_hash = db.get_latest_transaction()
    assert (
        tx_hash
        == HexBytes(
            "0xDFBB14E8F0E47FFC105A16043B2ECF536B323AC3B3B1D319A2D635E392E75BB9"
        ).to_0x_hex()
    )
