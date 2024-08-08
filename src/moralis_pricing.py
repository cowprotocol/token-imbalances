from moralis import evm_api
import os, dotenv

dotenv.load_dotenv()


def wei_to_eth(price: str):
    """Function to convert string price to float price in ETH."""
    if isinstance(price, str):
        price = float(price)
    if isinstance(price, (int, float)):
        return price / 10**18


class MoralisPriceProvider:
    def get_price(self, block_number: int, token_address):
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
                return wei_to_eth(result["nativePrice"]["value"])
            else:
                raise KeyError(" 'nativePrice' or 'value' not found in the result.")
        except Exception as e:
            return None
