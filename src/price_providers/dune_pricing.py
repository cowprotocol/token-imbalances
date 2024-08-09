from typing import Optional
import dotenv, os
from dune_client.types import QueryParameter
from dune_client.client import DuneClient
from dune_client.query import QueryBase
from src.config import get_web3_instance, get_logger
from src.constants import FETCH_PRICE_QUERY_ID, QUERY_BUFFER_TIME

dotenv.load_dotenv()
dune_api_key = os.getenv("DUNE_API_KEY")
dune = DuneClient.from_env()


class DunePriceProvider:
    """
    Purpose of this class is to fetch historical token prices from Dune.
    """

    def __init__(self) -> None:
        self.web3 = get_web3_instance()
        self.logger = get_logger()

    def get_price(self, block_number: int, token_address: str) -> Optional[float]:
        """
        Function returns Dune price for a token address,
        closest to and at least as large as the block timestamp for a given tx hash.
        """
        try:
            start_timestamp = self.web3.eth.get_block(block_number)["timestamp"]
            end_timestamp = start_timestamp + QUERY_BUFFER_TIME
            query = QueryBase(
                name="ERC20 Prices",
                query_id=FETCH_PRICE_QUERY_ID,
                params=[
                    QueryParameter.text_type(name="token_address", value=token_address),
                    QueryParameter.number_type(
                        name="start_timestamp", value=start_timestamp
                    ),
                    QueryParameter.number_type(
                        name="end_timestamp", value=end_timestamp
                    ),
                ],
            )
            result = dune.run_query(query=query)
            if result.result.rows:
                row = result.result.rows[0]
                price = row.get("price")
                if price is not None:
                    return price
            # No valid price found
            return None
        except KeyError as e:
            self.logger.error(f"Key error occurred: {e}")
        except Exception as e:
            self.logger.error(f"Unknown error occurred: {e}")
        return None
