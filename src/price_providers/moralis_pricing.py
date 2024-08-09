from typing import Optional
from moralis import evm_api
from src.config import get_logger
import os, dotenv

dotenv.load_dotenv()


class MoralisPriceProvider:
    """
    Purpose of this class is to fetch historical token prices using the Moralis API.
    """

    def __init__(self) -> None:
        self.logger = get_logger()

    @staticmethod
    def wei_to_eth(price: str) -> Optional[float]:
        """Function to convert string price to float price in ETH."""
        float_price = float(price) if isinstance(price, str) else None
        if isinstance(float_price, float):
            return float_price / 10**18
        return None

    def get_price(self, block_number: int, token_address: str) -> Optional[float]:
        """
        Function returns Moralis price given a block number and token_address.
        Price returned is closest to and at least as large as block timestamp.
        """
        try:
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
                f"Error: Likely the token: {token_address} was not found."
            )
        return None
