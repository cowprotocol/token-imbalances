import pytest
from src.price_providers.price_feed import PriceFeed


@pytest.fixture
def price_feed():
    return PriceFeed()


def test_get_price_real(price_feed):
    """Test with legitimate parameters."""

    # Test parameters
    tx_hash = "0x94af3d98b0af4ca6bf41e85c05ed42fccd71d5aaa04cbe01fab00d1b2268c4e1"
    token_address = "0xd1d2Eb1B1e90B638588728b4130137D262C87cae"
    block_number = 20630508
    price_params = {
        "tx_hash": tx_hash,
        "token_address": token_address,
        "block_number": block_number,
    }

    # Get the price
    result = price_feed.get_price(price_params)
    assert result is not None

    price, source = result
    # Assert that the price is a positive float
    assert isinstance(price, float)
    assert price > 0
    assert source in ["Coingecko", "Dune", "Moralis", "AuctionPrices"]


def test_get_price_unknown_token(price_feed):
    """Test with an unknown token address."""

    tx_hash = "0x94af3d98b0af4ca6bf41e85c05ed42fccd71d5aaa04cbe01fab00d1b2268c4e1"
    unknown_token = "0xd1d2Eb1B1e90B638588728b4130137D262C87cad"
    price_params = {
        "tx_hash": tx_hash,
        "token_address": unknown_token,
        "block_number": 20630508,
    }
    result = price_feed.get_price(price_params)

    #  expect None for an unknown token
    assert result is None


def test_get_price_future_block(price_feed):
    """Test with a block number in the future."""
    future_block = 99999999
    price_params = {
        "token_address": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
        "block_number": future_block,
    }

    result = price_feed.get_price(price_params)

    # expect None for a future block
    assert result is None


if __name__ == "__main__":
    pytest.main()
