from web3.types import HexStr

from src.price_providers.coingecko_pricing import CoingeckoPriceProvider
from src.price_providers.dune_pricing import DunePriceProvider
from src.price_providers.moralis_pricing import MoralisPriceProvider
from src.price_providers.endpoint_auction_pricing import AuctionPriceProvider
from src.helpers.config import logger

NATIVE_TOKEN = HexStr("0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE")

# pylint: disable=logging-fstring-interpolation


class PriceFeed:
    """Class encapsulating the different price providers."""

    # pylint: disable=too-few-public-methods

    def __init__(self, activate: bool):
        if activate:
            self.providers = [
                CoingeckoPriceProvider(),
                MoralisPriceProvider(),
                AuctionPriceProvider(),
            ]
        else:
            self.providers = []

    def get_price(self, price_params: dict) -> list[tuple[float, str]]:
        """Function iterates over list of price provider objects and attempts to get a price."""
        prices: list[tuple[float, str]] = []
        for provider in self.providers:
            try:
                if HexStr(price_params["token_address"]) == NATIVE_TOKEN:
                    price: float | None = 1.0
                else:
                    price = provider.get_price(price_params)
                if price is not None:
                    prices.append((price, provider.name))
            except Exception as e:
                logger.error(f"Error getting price from provider {provider.name}: {e}")
        return prices
