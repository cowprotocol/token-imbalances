from dotenv import load_dotenv
from web3 import Web3
from src.helper_functions import get_web3_instance
from contracts.erc20_abi import erc20_abi
import requests
import json


def load_cleaned_token_list(file_path):
    with open(file_path, "r") as f:
        return json.load(f)


def get_token_id_by_address(cleaned_token_list, token_address):
    for token in cleaned_token_list:
        if token["platforms"].get("ethereum") == token_address:
            return token["id"]
    return None


def get_api_price(token_id, start_timestamp, end_timestamp):
    url = f"https://pro-api.coingecko.com/api/v3/coins/{token_id}/market_chart/range?vs_currency=eth&from={start_timestamp}&to={end_timestamp}"
    headers = {
        "accept": "application/json",
        "x-cg-pro-api-key": "",
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    price = response.json()["prices"][0][1]
    return price


def get_price(block_number, token_address, imbalance):
    cleaned_token_list = load_cleaned_token_list("src/filtered_coingecko_list.json")
    token_address = token_address.lower()
    web3 = get_web3_instance()
    data = web3.eth.get_block(block_number)
    start_timestamp = data["timestamp"]
    end_timestamp = start_timestamp + 600
    print(start_timestamp, end_timestamp)

    token_id = get_token_id_by_address(cleaned_token_list, token_address)
    if not token_id:
        raise ValueError(f"Token ID not found for the given address: {token_address}")

    api_price = get_api_price(token_id, start_timestamp, end_timestamp)
    token_contract = web3.eth.contract(
        address=Web3.to_checksum_address(token_address), abi=erc20_abi
    )
    decimals = token_contract.functions.decimals().call()
    final_price = (imbalance / (10**decimals)) * api_price
    return final_price
