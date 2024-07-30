import os
import requests
import json
from dotenv import load_dotenv
from web3 import Web3
from src.helper_functions import get_web3_instance
from src.config import check_db_connection, logger
from src.constants import NATIVE_ETH_TOKEN_ADDRESS
from src.config import create_db_connection

load_dotenv()

solver_slippage_db_connection = create_db_connection("solver_slippage")
backend_db_connection = create_db_connection("backend")


def load_cleaned_token_list(file_path):
    with open(file_path, "r") as f:
        return json.load(f)


def get_token_id_by_address(cleaned_token_list, token_address):
    for token in cleaned_token_list:
        if token["platforms"].get("ethereum") == token_address:
            return token["id"]
    return None


def get_api_price(token_id: str, start_timestamp: int, end_timestamp: int):
    """
    Makes call to Coingecko API to fetch price, between a start and end timestamp.
    """
    url = f"https://pro-api.coingecko.com/api/v3/coins/{token_id}/market_chart/range?vs_currency=eth&from={start_timestamp}&to={end_timestamp}"
    headers = {
        "accept": "application/json",
        "x-cg-pro-api-key": os.getenv("COINGECKO_API_KEY"),
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    if len(data["prices"]) != 0:
        price = data["prices"][0][1]
        return price
    return None


def get_price(web3: Web3, block_number: int, token_address: str, tx_hash: str):
    """
    Function returns coingecko price for a token address,
    closest to block timestamp for a given tx hash.
    """
    cleaned_token_list = load_cleaned_token_list(
        "src/coingecko_tokens_list/filtered_coingecko_list.json"
    )
    token_address = token_address.lower()

    data = web3.eth.get_block(block_number)
    start_timestamp = data["timestamp"]
    # We need to provide a sufficient buffer time for fetching 5-minutely prices from coingecko.
    # If too short, it's possible that no price may be returned. We use the first value returned,
    # which would be closest to block timestamp
    BUFFER_TIME = 600
    end_timestamp = start_timestamp + BUFFER_TIME

    token_id = get_token_id_by_address(cleaned_token_list, token_address)
    if not token_id:
        logger.warning(f"Token ID not found for the given address: {token_address}")
        return None
    try:
        api_price = get_api_price(token_id, start_timestamp, end_timestamp)
        if api_price is None:
            logger.warning(f"API returned None for token ID: {token_id}")
            return None
    except requests.RequestException as e:
        logger.error(f"Error fetching price from API: {e}")
        return None

    return api_price
