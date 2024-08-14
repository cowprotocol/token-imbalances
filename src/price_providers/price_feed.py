from src.price_providers.coingecko_pricing import CoingeckoPriceProvider
from src.price_providers.dune_pricing import DunePriceProvider
from src.price_providers.moralis_pricing import MoralisPriceProvider
from src.helpers.config import logger


class PriceFeed:
    """Class encapsulating the different price providers."""

    def __init__(self):
        self.providers = [
            CoingeckoPriceProvider(),
            DunePriceProvider(),
            MoralisPriceProvider(),
        ]

    def get_price(
        self, block_number: int, token_address: str
    ) -> tuple[float, str] | None:
        """Function iterates over list of price provider objects and attempts to get a price."""
        for provider in self.providers:
            try:
                price = provider.get_price(block_number, token_address)
                if price is not None:
                    return price, provider.name
            except Exception as e:
                logger.error(f"Error getting price from provider {provider.name}: {e}")
        return None
