import dotenv, os
from dune_client.types import QueryParameter
from dune_client.client import DuneClient
from dune_client.query import QueryBase
from src.config import get_web3_instance

dotenv.load_dotenv()
dune_api_key = os.getenv("DUNE_API_KEY")
dune = DuneClient.from_env()

# Query is set to LIMIT 1, i.e. it will return a single price
fetch_price_query_id = 3935228


class DunePriceProvider:
    def __init__(self):
        self.web3 = get_web3_instance()

    def get_price(self, block_number: int, token_address):
        # Query uses an end_timestamp to limit results
        BUFFER_TIME = 100
        start_timestamp = self.web3.eth.get_block(block_number)["timestamp"]
        end_timestamp = start_timestamp + BUFFER_TIME
        query = QueryBase(
            name="ERC20 Prices",
            query_id=fetch_price_query_id,
            params=[
                QueryParameter.text_type(name="token_address", value=token_address),
                QueryParameter.number_type(
                    name="start_timestamp", value=start_timestamp
                ),
                QueryParameter.number_type(name="end_timestamp", value=end_timestamp),
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
