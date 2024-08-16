from moralis import evm_api
from src.helpers.config import get_logger
import os, dotenv
from src.price_providers.pricing_model import AbstractPriceProvider
from src.helpers.helper_functions import extract_params


dotenv.load_dotenv()


class MoralisPriceProvider(AbstractPriceProvider):
    """
    Purpose of this class is to fetch historical token prices using the Moralis API.
    """

    def __init__(self) -> None:
        self.logger = get_logger()

    @property
    def name(self) -> str:
        return "Moralis"

    @staticmethod
    def wei_to_eth(price: str) -> float | None:
        """Function to convert string price to float price in ETH."""
        float_price = float(price) if isinstance(price, str) else None
        if isinstance(float_price, float):
            return float_price / 10**18
        return None

    def get_price(self, price_params: dict) -> float | None:
        """
        Function returns Moralis price given a block number and token_address.
        Price returned is closest to and at least as large as block timestamp.
        """
        try:
            token_address, block_number = extract_params(price_params, is_block=True)
            params = {
                "chain": "eth",
                "address": token_address,
                "to_block": block_number,
            }
            result = evm_api.token.get_token_price(
                api_key=os.getenv("MORALIS_KEY"),
                params=params,
            )
            if "nativePrice" in result and "value" in result["nativePrice"]:
                # return price in ETH
                return self.wei_to_eth(result["nativePrice"]["value"])
            else:
                raise KeyError(" 'nativePrice' or 'value' not found in the result.")
        except KeyError as e:
            self.logger.warning(f"Error: {e}")
        except Exception as e:
            self.logger.warning(
                f"Error: {e}, Likely the token: {token_address} was not found or API limit reached."
            )
        return None
