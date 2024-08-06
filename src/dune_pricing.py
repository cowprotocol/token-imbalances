import os
from typing import Optional
import requests
import json
from web3 import Web3
from src.config import logger
from src.helper_functions import get_finalized_block_number
from src.constants import NATIVE_ETH_TOKEN_ADDRESS, WETH_TOKEN_ADDRESS

dune_api_key = os.getenv("DUNE_API_KEY")

def get_dune_price(token_address, start_timestamp, end_timestamp):
    query = QueryBase(
        name="ERC20 Prices",
        query_id=3935228,
        params=[
            QueryParameter.text_type(name="token_address", value=token_address),
            QueryParameter.number_type(name="start_timestamp", value=start_timestamp),
            QueryParameter.number_type(name="end_timestamp", value=end_timestamp),
        ],
    )
    result = dune.run_query(query=query)
    for row in result.result.rows:
        print(row["price"])


token_address = "0x00380d12a12acf6f47481E8CA8BE777931395200"
get_dune_price(token_address.lower(), 1721165100, 1721168700)
