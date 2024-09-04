""" Constants used for the token imbalances project """
from web3 import Web3

SETTLEMENT_CONTRACT_ADDRESS = Web3.to_checksum_address(
    "0x9008D19f58AAbD9eD0D60971565AA8510560ab41"
)
NATIVE_ETH_TOKEN_ADDRESS = Web3.to_checksum_address(
    "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
)
WETH_TOKEN_ADDRESS = Web3.to_checksum_address(
    "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
)
SDAI_TOKEN_ADDRESS = Web3.to_checksum_address(
    "0x83F20F44975D03b1b09e64809B757c47f942BEeA"
)

INVALIDATED_ORDER_TOPIC = (
    "0x875b6cb035bbd4ac6500fabc6d1e4ca5bdc58a3e2b424ccb5c24cdbebeb009a9"
)

NULL_ADDRESS =  Web3.to_checksum_address(
    "0x0000000000000000000000000000000000000000"
)

REQUEST_TIMEOUT = 5

# Time limit, currently set to 1 full day, after which Coingecko Token List is re-fetched (in seconds)
COINGECKO_TOKEN_LIST_RELOAD_TIME = 86400

# Time in seconds of 45 hours. Time limit after which 5-minute prices become unavailable.
COINGECKO_TIME_LIMIT = 162000

# Buffer time interval to allow 5-minutely Coingecko prices to be fetched
COINGECKO_BUFFER_TIME = 600

# Dune query for fetching prices is set to LIMIT 1, i.e. it will return a single price
DUNE_PRICE_QUERY_ID = 3935228

# Dune Query 3935228 uses an end_timestamp to limit results
# (Buffer time to return results between start_timstamp and end_timestamp only)
DUNE_QUERY_BUFFER_TIME = 100
