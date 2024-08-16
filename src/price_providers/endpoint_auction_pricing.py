import requests
from src.price_providers.pricing_model import AbstractPriceProvider
from src.helpers.config import logger
from src.helpers.helper_functions import extract_params


class AuctionPriceProvider(AbstractPriceProvider):
    def __init__(self) -> None:
        self.endpoint_url = {
            "prod": f"https://api.cow.fi/mainnet/api/v1/solver_competition/by_tx_hash/"
        }

    @property
    def name(self) -> str:
        return "AuctionPrices"

    def get_price(self, price_params: dict):
        token_address, tx_hash = extract_params(price_params, is_block=False)
        url = self.endpoint_url["prod"] + tx_hash
        try:
            response = requests.get(url)
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

            price_in_eth = float(price) / 10**18
            return price_in_eth

        except requests.exceptions.RequestException as req_err:
            logger.error(f"Error occurred during request: {req_err}")
        except KeyError as key_err:
            logger.error(f"Key error: {key_err}")
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")

        return None


app = AuctionPriceProvider()
price_params = {
    "token_address": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
    "tx_hash": "0x7592828d4bdb7dd5414292761d581c58288b94b19991a8a706cbc0575c2afb2e",
}
app.get_price(price_params)
