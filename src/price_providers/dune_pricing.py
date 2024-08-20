from typing import cast
import dotenv, os
from src.price_providers.pricing_model import AbstractPriceProvider
from dune_client.types import QueryParameter
from dune_client.client import DuneClient
from dune_client.query import QueryBase
from src.helpers.config import get_web3_instance, get_logger
from src.helpers.helper_functions import extract_params
from src.constants import DUNE_PRICE_QUERY_ID, DUNE_QUERY_BUFFER_TIME

dotenv.load_dotenv()


class DunePriceProvider(AbstractPriceProvider):
    """
    Purpose of this class is to fetch historical token prices from Dune.
    """

    def __init__(self) -> None:
        self.web3 = get_web3_instance()
        self.logger = get_logger()
        self.dune = self.initialize_dune_client()

    @property
    def name(self) -> str:
        return "Dune"

    def initialize_dune_client(self) -> DuneClient | None:
        """
        Initializes the Dune client and returns None if API key is not set.
        """
        dune_api_key = os.getenv("DUNE_API_KEY")
        if not dune_api_key:
            self.logger.warning("DUNE_API_KEY is not set.")
            return None
        return cast(DuneClient, DuneClient.from_env())

    def get_price(self, price_params: dict) -> float | None:
        """
        Function returns Dune price for a token address,
        closest to and at least as large as the block timestamp for a given tx hash.
        """
        try:
            if not self.dune:
                return None
            token_address, block_number = extract_params(price_params, is_block=True)
            start_timestamp = getattr(
                self.web3.eth.get_block(block_number), "timestamp", None
            )
            if start_timestamp is None:
                raise KeyError("Timestamp not found in block data.")
            end_timestamp = start_timestamp + DUNE_QUERY_BUFFER_TIME
            query = QueryBase(
                name="ERC20 Prices",
                query_id=DUNE_PRICE_QUERY_ID,
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
            result = self.dune.run_query(query=query)  # type: ignore[attr-defined]
            if result and result.result and result.result.rows:
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
