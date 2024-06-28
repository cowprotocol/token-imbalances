import os
from dotenv import load_dotenv

load_dotenv()
ETHEREUM_NODE_URL = os.getenv('ETHEREUM_NODE_URL')
GNOSIS_NODE_URL = os.getenv('GNOSIS_NODE_URL')

CHAIN_RPC_ENDPOINTS = {
    'Ethereum': ETHEREUM_NODE_URL,
    'Gnosis': GNOSIS_NODE_URL
}

CHAIN_SLEEP_TIMES = {
    'Ethereum': 60,
    'Gnosis': 120
}