import os
import requests
import json
from typing import Dict, List, Optional, Tuple
from web3 import Web3
from dotenv import load_dotenv

from src.constants import (SETTLEMENT_CONTRACT_ADDRESS, NATIVE_ETH_TOKEN_ADDRESS, 
                           WETH_TOKEN_ADDRESS, SDAI_TOKEN_ADDRESS)

EVENT_TOPICS = {
    'Transfer': 'Transfer(address,address,uint256)',
    'ERC20Transfer': 'ERC20Transfer(address,address,uint256)',
    'WithdrawalWETH': 'Withdrawal(address,uint256)',
    'DepositSDAI': 'Deposit(address,address,uint256,uint256)',
    'WithdrawSDAI': 'Withdraw(address,address,address,uint256,uint256)',
}

class RawTokenImbalances:
    def __init__(self):
        load_dotenv()
        self.INFURA_KEY = os.getenv('INFURA_KEY')
        self.CHAIN_RPC_ENDPOINTS = {
            'Ethereum': f'https://mainnet.infura.io/v3/{self.INFURA_KEY}',
            'Arbitrum': f'https://arbitrum-mainnet.infura.io/v3/{self.INFURA_KEY}',
            'Gnosis': 'https://rpc.gnosis.gateway.fm'
        }
        self.WEB3_INSTANCES = {chain: Web3(Web3.HTTPProvider(url)) for chain, url in self.CHAIN_RPC_ENDPOINTS.items()}

    def get_web3_instance(self, chain_name: str) -> Web3:
        """Get the Web3 instance for a specific chain."""
        return self.WEB3_INSTANCES[chain_name]

    def get_transaction_trace(self, transaction_hash: str, chain_url: str) -> list[dict] | None:
        """Fetch transaction trace from the RPC endpoint."""
        payload = {
            "jsonrpc": "2.0",
            "method": "trace_transaction",
            "params": [transaction_hash],
            "id": 1
        }
        headers = {"Content-Type": "application/json"}
        response = requests.post(chain_url, headers=headers, data=json.dumps(payload))
        try:
            response.raise_for_status()
            return response.json().get('result', [])
        except requests.exceptions.HTTPError as err:
                print(f"HTTP error occurred: {err}")
        except requests.exceptions.RequestException as err:
                print(f"Error occurred: {err}")
        return None

    def extract_actions(self, traces: List[Dict], address: str, input_field: str = "0x") -> List[Dict]:
        """Identify transfer events in trace involving the specified contract."""
        normalized_address = Web3.to_checksum_address(address)
        return [
            trace.get('action', {}) for trace in traces
            if trace.get('action', {}).get('input') == input_field and (
                Web3.to_checksum_address(trace.get('action', {}).get('from', '')) == normalized_address or
                Web3.to_checksum_address(trace.get('action', {}).get('to', '')) == normalized_address
            )
        ]

    def calculate_native_eth_imbalance(self, actions: List[Dict], address: str) -> int:
        """Extract ETH imbalance from transfer actions."""
        inflow = sum(Web3.to_int(hexstr=action.get('value', '0x0')) for action in actions if Web3.to_checksum_address(action.get('to', '')) == address)
        outflow = sum(Web3.to_int(hexstr=action.get('value', '0x0')) for action in actions if Web3.to_checksum_address(action.get('from', '')) == address)
        return inflow - outflow

    def extract_events(self, tx_receipt: Dict, web3: Web3) -> Dict[str, List[Dict]]:
        """Extract relevant events from the transaction receipt."""
        event_topics = compute_event_topics(web3)
        transfer_topics = {k: v for k, v in event_topics.items() if k in ['Transfer', 'ERC20Transfer']}
        other_topics = {k: v for k, v in event_topics.items() if k not in transfer_topics}

        events = {name: [] for name in EVENT_TOPICS}

        for log in tx_receipt['logs']:
            log_topic = log['topics'][0].hex()
            if log_topic in transfer_topics.values():
                events['Transfer'].append(log)
            else:
                for event_name, topic in other_topics.items():
                    if log_topic == topic:
                        events[event_name].append(log)
                        break
        return events

    def decode_event(self, event: Dict) -> Tuple[Optional[str], Optional[str], Optional[int]]:
        """
        Decode transfer and withdrawal events.
        Returns from_address, to_address (for transfer), and value.
        """
        try:
            from_address = Web3.to_checksum_address("0x" + event['topics'][1].hex()[-40:])
            value_hex = event['data']
            
            if isinstance(value_hex, bytes):
                value = int.from_bytes(value_hex, byteorder='big')
            else:
                value = int(value_hex, 16)

            if len(event['topics']) > 2:  # Transfer event
                to_address = Web3.to_checksum_address("0x" + event['topics'][2].hex()[-40:])
                return from_address, to_address, value
            else:  # Withdrawal event
                return from_address, None, value
        except Exception as e:
            print(f"Error decoding event: {str(e)}")
            return None, None, None

    def decode_sdai_event(self, event: Dict) -> int | None:
        """Decode sDAI event."""
        try:
            value_hex = event['data'][-30:]
            
            if isinstance(value_hex, bytes):
                value = int.from_bytes(value_hex, byteorder='big')
            else:
                value = int(value_hex, 16)
            return value
        except Exception as e:
            print(f"Error decoding sDAI event: {str(e)}")
            return None

    def find_chain_with_tx(self, tx_hash: str) -> Tuple[str, Web3]:
        """
        Find the chain where the transaction is present.
        Returns the chain name and the web3 instance.
        """
        for chain_name, web3 in self.WEB3_INSTANCES.items():
            if not web3.is_connected():
                print(f"Could not connect to {chain_name}.")
                continue
            try:
                web3.eth.get_transaction_receipt(tx_hash)
                print(f"Transaction found on {chain_name}.")
                return chain_name, web3
            except Exception as e:
                print(f"Transaction not found on {chain_name}: {e}")
        raise ValueError(f"Transaction hash {tx_hash} not found on any chain.")

    def get_transaction_receipt(self, tx_hash: str, web3: Web3) -> Optional[Dict]:
        """
        Get the transaction receipt from the provided web3 instance.
        """
        try:
            return web3.eth.get_transaction_receipt(tx_hash)
        except Exception as e:
            print(f"Error getting transaction receipt: {e}")
            return None

    def process_event(self, event: Dict, inflows: Dict[str, int], outflows: Dict[str, int], address: str) -> None:
        """Process a single event to update inflows and outflows."""
        from_address, to_address, value = self.decode_event(event)
        if from_address is None or to_address is None:
            return
        if to_address == address:
            inflows[event['address']] = inflows.get(event['address'], 0) + value
        if from_address == address:
            outflows[event['address']] = outflows.get(event['address'], 0) + value

    def process_sdai_event(self, event: Dict, imbalances: Dict[str, int], is_deposit: bool) -> None:
        """Process an sDAI deposit or withdrawal event to update imbalances."""
        decoded_event_value = self.decode_sdai_event(event)
        if decoded_event_value is None:
            return
        if is_deposit:
            imbalances[SDAI_TOKEN_ADDRESS] = imbalances.get(SDAI_TOKEN_ADDRESS, 0) + decoded_event_value
        else:
            imbalances[SDAI_TOKEN_ADDRESS] = imbalances.get(SDAI_TOKEN_ADDRESS, 0) - decoded_event_value

    def calculate_imbalances(self, events: Dict[str, List[Dict]], address: str) -> Dict[str, int]:
        """Calculate token imbalances from events."""
        inflows, outflows = {}, {}
        for event in events['Transfer']:
            self.process_event(event, inflows, outflows, address)

        imbalances = {
            token_address: inflows.get(token_address, 0) - outflows.get(token_address, 0)
            for token_address in set(inflows.keys()).union(outflows.keys())
        }
        return imbalances

    def update_weth_imbalance(self, events: Dict[str, List[Dict]], actions: List[Dict], imbalances: Dict[str, int], address: str) -> None:
        """Update the WETH imbalance in imbalances."""
        weth_inflow = imbalances.get(WETH_TOKEN_ADDRESS, 0)
        weth_outflow = 0
        weth_withdrawals = 0
        for event in events['WithdrawalWETH']:
            from_address, _, value = self.decode_event(event)
            if from_address == address:
                weth_withdrawals += value
        imbalances[WETH_TOKEN_ADDRESS] = weth_inflow - weth_outflow - weth_withdrawals

    def update_native_eth_imbalance(self, imbalances: Dict[str, int], native_eth_imbalance: Optional[int]) -> None:
        """Update the native ETH imbalance in imbalances."""
        if native_eth_imbalance is not None:
            imbalances[NATIVE_ETH_TOKEN_ADDRESS] = native_eth_imbalance

    def update_sdai_imbalance(self, events: Dict[str, List[Dict]], imbalances: Dict[str, int]) -> None:
        """Update the sDAI imbalance in imbalances."""
        for event in events['DepositSDAI']:
            if event['address'] == SDAI_TOKEN_ADDRESS:
                self.process_sdai_event(event, imbalances, is_deposit=True)
        for event in events['WithdrawSDAI']:
            if event['address'] == SDAI_TOKEN_ADDRESS:
                self.process_sdai_event(event, imbalances, is_deposit=False)

    def compute_imbalances(self, tx_hash: str) -> Tuple[Dict[str, int], str]:
        """Compute token imbalances for a given transaction hash."""
        chain_name, web3 = self.find_chain_with_tx(tx_hash)
        tx_receipt = self.get_transaction_receipt(tx_hash, web3)
        if tx_receipt is None:
            raise ValueError(f"Transaction hash {tx_hash} not found on chain {chain_name}.")

        traces = self.get_transaction_trace(tx_hash, self.CHAIN_RPC_ENDPOINTS[chain_name])
        native_eth_imbalance = None
        actions = []
        if traces is not None:
            actions = self.extract_actions(traces, SETTLEMENT_CONTRACT_ADDRESS)
            native_eth_imbalance = self.calculate_native_eth_imbalance(actions, SETTLEMENT_CONTRACT_ADDRESS)

        events = self.extract_events(tx_receipt, web3)
        imbalances = self.calculate_imbalances(events, SETTLEMENT_CONTRACT_ADDRESS)

        if actions:
            self.update_weth_imbalance(events, actions, imbalances, SETTLEMENT_CONTRACT_ADDRESS)
            self.update_native_eth_imbalance(imbalances, native_eth_imbalance)

        self.update_sdai_imbalance(events, imbalances)

        return imbalances, chain_name

def compute_event_topics(web3: Web3) -> Dict[str, str]:
    """Compute the event topics for all relevant events."""
    return {name: web3.keccak(text=text).hex() for name, text in EVENT_TOPICS.items()}

def main() -> None:
    rt = RawTokenImbalances()
    tx_hash = input("Enter transaction hash: ")
    try:
        imbalances, chain_name = rt.compute_imbalances(tx_hash)
        print(f"Token Imbalances on {chain_name}:")
        for token_address, imbalance in imbalances.items():
            print(f"Token: {token_address}, Imbalance: {imbalance}")
    except ValueError as e:
        print(e)

if __name__ == "__main__":
    main()
