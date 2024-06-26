import os
from dotenv import load_dotenv

load_dotenv()
INFURA_KEY = os.getenv('INFURA_KEY')

CHAIN_RPC_ENDPOINTS = {
    'Ethereum': f'https://mainnet.infura.io/v3/{INFURA_KEY}',
    'Gnosis': 'https://rpc.gnosis.gateway.fm'
}

CHAIN_SLEEP_TIMES = {
    'Ethereum': 60,
    'Gnosis': 120
}