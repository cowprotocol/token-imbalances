import os
from typing import Optional
import requests
import json
from web3 import Web3
from src.config import logger
from src.helper_functions import get_finalized_block_number
from src.constants import NATIVE_ETH_TOKEN_ADDRESS, WETH_TOKEN_ADDRESS

coingecko_api_key = os.getenv("COINGECKO_API_KEY")

# Load the coingecko token list
cleaned_token_list_path = "src/coingecko_tokens_list/filtered_coingecko_list.json"
with open(cleaned_token_list_path, "r") as f:
    cleaned_token_list = json.load(f)


def get_token_id_by_address(cleaned_token_list, token_address):
    for token in cleaned_token_list:
        if token["platforms"].get("ethereum") == token_address:
            return token["id"]
    return None


def fetch_api_price(
    token_id: str, start_timestamp: int, end_timestamp: int
) -> Optional[float]:
    """
    Makes call to Coingecko API to fetch price, between a start and end timestamp.
    """
    if not coingecko_api_key:
        logger.warning("Coingecko API key is not set.")
        return None
    # price of token is returned in ETH
    url = (
        f"https://pro-api.coingecko.com/api/v3/coins/{token_id}/market_chart/range"
        f"?vs_currency=eth&from={start_timestamp}&to={end_timestamp}"
    )
    headers = {
        "accept": "application/json",
        "x-cg-pro-api-key": coingecko_api_key,
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        # return available coingecko price, which is the closest to the block timestamp
        if len(data["prices"]) != 0:
            price = data["prices"][0][1]
            return price
        return None
    except requests.RequestException as e:
        logger.warning(f"Error fetching price from Coingecko API: {e}")
        return None


def price_not_retrievable(web3: Web3, block_start_timestamp: int) -> bool:
    """
    This function checks if the time elapsed between the latest block and block being processed
    is less than 2 days, which is coingecko's time frame for fetching 5-minutely data.
    """
    # Time in seconds of 45 hours.
    COINGECKO_TIME_LIMIT = 162000
    newest_block_timestamp = web3.eth.get_block(get_finalized_block_number(web3))[
        "timestamp"
    ]
    return (newest_block_timestamp - block_start_timestamp) > COINGECKO_TIME_LIMIT


def get_price(web3: Web3, block_number: int, token_address: str, tx_hash: str):
    """
    Function returns coingecko price for a token address,
    closest to and at least as large as the block timestamp for a given tx hash.
    """

    block_start_timestamp = web3.eth.get_block(block_number)["timestamp"]
    if price_not_retrievable(web3, block_start_timestamp):
        return None

    # Coingecko doesn't store ETH address, which occurs commonly in imbalances.
    # Approximate WETH price as equal to ETH.
    if Web3.to_checksum_address(token_address) in (
        NATIVE_ETH_TOKEN_ADDRESS,
        WETH_TOKEN_ADDRESS,
    ):
        return 1.0

    # We need to provide a sufficient buffer time for fetching 5-minutely prices from coingecko.
    # If too short, it's possible that no price may be returned. We use the first value returned,
    # which would be closest to block timestamp
    BUFFER_TIME = 600
    block_end_timestamp = block_start_timestamp + BUFFER_TIME

    token_address = token_address.lower()
    token_id = get_token_id_by_address(cleaned_token_list, token_address)
    if not token_id:
        logger.warning(f"Token ID not found for the given address: {token_address}")
        return None
    try:
        api_price = fetch_api_price(
            token_id, block_start_timestamp, block_end_timestamp
        )
        if api_price is None:
            logger.warning(f"API returned None for token ID: {token_id}")
            return None
    except requests.RequestException as e:
        logger.error(f"Error fetching price from API: {e}")
        return None

    return api_price
