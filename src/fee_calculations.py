import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv
from time import sleep
import requests


def create_db_connections():

    load_dotenv()
    barn_db_url = os.environ["BARN_DB_URL"]
    prod_db_url = os.environ["PROD_DB_URL"]
    barn_connection = create_engine(f"postgresql+psycopg2://{barn_db_url}")
    prod_connection = create_engine(f"postgresql+psycopg2://{prod_db_url}")

    return prod_connection, barn_connection


def fee_calculation_loop():
    prod_connection, barn_connection = create_db_connections()
    prod_query_file = open("src/queries/get_latest_auction_id.sql", "r").read()
    result = pd.read_sql(prod_query_file, prod_connection)
    latest_auction_id = int(result["id"][0])

    # main daemon that parses the db and the api for new settlements and updates db accordingly
    while True:
        sleep(5)
        new_auction_id = latest_auction_id
        while True:
            result = pd.read_sql(prod_query_file, prod_connection)
            new_auction_id = int(result["id"][0])
            if new_auction_id > latest_auction_id:
                break
            sleep(5)
        # we now have a new auction id, so we can process the auction id stored in latest_auction_id

        process_orders(latest_auction_id, prod_connection)

        latest_auction_id += 1

    return


def process_orders(auction_id, db_connection):
    url = f"https://api.cow.fi/mainnet/api/v1/solver_competition/{auction_id}"
    response = requests.get(url)
    if response.ok == False:
        return
    data = response.json()
    tx_hash = data["transactionHash"]
    solutions = data["solutions"]
    for s in solutions:
        if s["ranking"] == 1:
            winning_sol = s
    orders = winning_sol["orders"]
    clearing_prices = winning_sol["clearingPrices"]
    cow_amms = []

    # going over all executed orders and fetching necessary data
    for o in orders:
        uid = o["id"]
        url = f"https://api.cow.fi/mainnet/api/v1/orders/{uid}"
        response = requests.get(url)
        sleep(0.3)  # to avoid rate limits
        if response.ok == False:
            # jit CoW AMM detected
            cow_amms.append(uid)
            continue
        order_data = response.json()
        url = f"https://api.cow.fi/mainnet/api/v1/trades?orderUid={uid}"
        response = requests.get(url)
        sleep(0.3)  # to avoid rate limits
        trade_data_temp = response.json()
        if len(trade_data_temp) > 1:
            for t in trade_data_temp:
                if t["txHash"] == tx_hash:
                    trade_data = t
                    break
        else:
            trade_data = trade_data_temp[0]
        compute_protocol_fees(trade_data, order_data)


def compute_protocol_fees(trade_data, order_data):
    reversed_fee_policies = trade_data["feePolicies"]
    reversed_fee_policies.reverse()
    executed_sell_amount = int(trade_data["sellAmount"])
    executed_buy_amount = int(trade_data["buyAmount"])
    kind = order_data["kind"]

    # computing limit amounts
    if kind == "sell":
        limit_sell_amount = executed_sell_amount
        limit_buy_amount = (limit_sell_amount * int(order_data["buyAmount"])) // int(
            order_data["sellAmount"]
        )
        # we want to round up in order to not violate the limit price
        if (limit_sell_amount * int(order_data["buyAmount"])) % int(
            order_data["sellAmount"]
        ) > 0:
            limit_buy_amount += 1
    else:
        limit_buy_amount = executed_buy_amount
        # we want to round down in order to not violate the limit price
        limit_sell_amount = (limit_buy_amount * int(order_data["sellAmount"])) // int(
            order_data["buyAmount"]
        )

    if len(reversed_fee_policies) == 0:
        return
    for fp in reversed_fee_policies:
        type = list(fp.keys())[0]
        raw_sell_amount = executed_sell_amount
        raw_buy_amount = executed_buy_amount
        if type == "surplus":
            if kind == "sell":
                onchain_surplus = raw_buy_amount - limit_buy_amount
                factor_str = str(fp["surplus"]["factor"])
                protocol_fee_one = compute_surplus_protocol_fee(
                    onchain_surplus, factor_str, kind
                )
                max_volume_factor_str = str(fp["surplus"]["maxVolumeFactor"])
                protocol_fee_two = compute_volume_protocol_fee(
                    onchain_surplus, max_volume_factor_str, kind
                )


def compute_surplus_protocol_fee(onchain_surplus, factor_str, kind):
    num_decimals = len(factor_str) - 2
    numerator = int(factor_str[2:])
    denominator = 10**num_decimals
    if kind == "sell":
        raw_surplus = (onchain_surplus * denominator) // (denominator - numerator)
        if (onchain_surplus * denominator) % (denominator - numerator) > 0:
            raw_surplus += 1
        return (raw_surplus * numerator) // denominator
    else:
        return 0

def compute_volume_protocol_fee(onchain_surplus, factor_str, kind):
    num_decimals = len(factor_str) - 2
    numerator = int(factor_str[2:])
    denominator = 10**num_decimals
    if kind == "sell":
        raw_surplus = (onchain_surplus * denominator) // (denominator - numerator)
        if (onchain_surplus * denominator) % (denominator - numerator) > 0:
            raw_surplus += 1
        return (raw_surplus * numerator) // denominator
    else:
        return 0
        
