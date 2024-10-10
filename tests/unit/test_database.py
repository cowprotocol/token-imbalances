from datetime import datetime

from hexbytes import HexBytes
from sqlalchemy import create_engine, text

from src.helpers.database import Database


def tests_write_transaction_timestamp():
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


def tests_write_transaction_tokens():
    # import has to happen after patching environment variable

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


def tests_write_prices():
    engine = create_engine(
        f"postgresql+psycopg2://postgres:postgres@localhost:5432/mainnet"
    )
    db = Database(engine, "mainnet")
    token_prices = [
        (
            "0xA0B86991C6218B36C1D19D4A2E9EB0CE3606EB48",
            int(datetime.fromisoformat("2024-10-10 16:48:47.000000").timestamp()),
            0.000420454193230350,
            "coingecko",
        ),
        (
            "0x68BBED6A47194EFF1CF514B50EA91895597FC91E",
            int(datetime.fromisoformat("2024-10-10 16:49:47.000000").timestamp()),
            0.000000050569218629,
            "moralis",
        ),
    ]
    # truncate table
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE prices"))
        conn.commit()
    # write data
    db.write_prices_new(token_prices)
    # read data
    with engine.connect() as conn:
        res = conn.execute(
            text("SELECT token_address, time, price, source FROM prices")
        ).all()
    for i, (token_address, time, price, source) in enumerate(token_prices):
        assert HexBytes(res[i][0]) == HexBytes(token_address)
        assert res[i][1].timestamp() == time
        assert float(res[i][2]) == price
        assert res[i][3] == source


def test_get_latest_transaction():
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
