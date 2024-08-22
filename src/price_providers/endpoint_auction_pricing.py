import requests
from src.price_providers.pricing_model import AbstractPriceProvider
from src.helpers.config import logger
from src.helpers.helper_functions import extract_params, get_token_decimals


class AuctionPriceProvider(AbstractPriceProvider):
    """Fetch auction prices."""

    def __init__(self) -> None:
        self.endpoint_urls = {
            "prod": f"https://api.cow.fi/mainnet/api/v1/solver_competition/by_tx_hash/",
            "barn": f"https://barn.api.cow.fi/mainnet/api/v1/solver_competition/by_tx_hash/",
        }

    @property
    def name(self) -> str:
        return "AuctionPrices"

    def get_price(self, price_params: dict) -> float | None:
        """Function returns Auction price from endpoint for a token address."""
        token_address, tx_hash = extract_params(price_params, is_block=False)
        for environment, url in self.endpoint_urls.items():
            try:
                # append tx_hash to endpoint
                response = requests.get(url + tx_hash)
                response.raise_for_status()
                data = response.json()

                # Search for the token address in the auction prices
                auction_prices = data.get("auction", {}).get("prices", {})
                price = auction_prices.get(token_address.lower())

                if price is None:
                    logger.warning(
                        f"Price for token {token_address} not found in auction data."
                    )
                    return None
                # calculation for converting auction price from endpoint to ETH equivalent per token unit
                price_in_eth = (float(price) / 10**18) * (
                    10 ** get_token_decimals(token_address) / 10**18
                )
                return price_in_eth

            except requests.exceptions.HTTPError as err:
                if err.response.status_code == 404:
                    pass
            except requests.exceptions.RequestException as req_err:
                logger.error(f"Error occurred during request: {req_err}")
            except KeyError as key_err:
                logger.error(f"Key error: {key_err}")
            except Exception as e:
                logger.error(f"An unexpected error occurred: {e}")

        return None
