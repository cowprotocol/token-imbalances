# mypy: disable-error-code="arg-type, operator, return, attr-defined"
"""
Steps for computing token imbalances:

1. Get transaction receipt via tx hash -> get_transaction_receipt()
2. Obtain the transaction trace and extract actions from trace to identify actions 
   related to native ETH transfers -> get_transaction_trace() and extract_actions()
3. Calculate ETH imbalance via actions by identifying transfers in 
   and out of a contract address -> calculate_native_eth_imbalance()
4. Extract and categorize relevant events (such as ERC20 transfers, WETH withdrawals, 
   and sDAI transactions) from the transaction receipt. -> extract_events()
5. Process each event by first decoding it to retrieve event details, i.e. to_address, from_address
   and transfer value -> decode_event()
6. If to_address or from_address match the contract address parameter, update inflows/outflows by 
   adding the transfer value to existing inflow/outflow for the token addresses.
7. Returning to calculate_imbalances(), which finds the imbalance for all token addresses using
   inflow-outflow.
8. If actions are not None, it denotes an ETH transfer event, which involves reducing WETH 
   withdrawal amount- > update_weth_imbalance(). The ETH imbalance is also calculated 
   via -> update_native_eth_imbalance().
9. update_sdai_imbalance() is called in each iteration and only completes if there is an SDAI 
   transfer involved which has special handling for its events.
"""

from web3 import Web3
from web3.datastructures import AttributeDict
from web3.types import HexStr, TxReceipt
from src.helpers.config import CHAIN_RPC_ENDPOINTS, logger
from src.constants import (
    SETTLEMENT_CONTRACT_ADDRESS,
    NATIVE_ETH_TOKEN_ADDRESS,
    WETH_TOKEN_ADDRESS,
    SDAI_TOKEN_ADDRESS,
)

EVENT_TOPICS = {
    "Transfer": "Transfer(address,address,uint256)",
    "ERC20Transfer": "ERC20Transfer(address,address,uint256)",
    "WithdrawalWETH": "Withdrawal(address,uint256)",
    "DepositWETH": "Deposit(address,uint256)",
    "DepositSDAI": "Deposit(address,address,uint256,uint256)",
    "WithdrawSDAI": "Withdraw(address,address,address,uint256,uint256)",
}


def compute_event_topics(web3: Web3) -> dict[str, str]:
    """Compute the event topics for all relevant events."""
    return {name: web3.keccak(text=text).hex() for name, text in EVENT_TOPICS.items()}


def find_chain_with_tx(tx_hash: str) -> tuple[str, Web3]:
    """
    Find the chain where the transaction is present.
    Returns the chain name and the web3 instance. Used for checking single tx hashes.
    """
    for chain_name, url in CHAIN_RPC_ENDPOINTS.items():
        web3 = Web3(Web3.HTTPProvider(url))
        if not web3.is_connected():
            logger.warning("Could not connect to %s.", chain_name)
            continue
        try:
            web3.eth.get_transaction_receipt(tx_hash)
            logger.info("Transaction found on %s.", chain_name)
            return chain_name, web3
        except Exception as ex:
            logger.debug("Transaction not found on %s: %s", chain_name, ex)
    raise ValueError(f"Transaction hash {tx_hash} not found on any chain.")


def _to_int(value: str | int) -> int:
    """Convert hex string or integer to integer."""
    try:
        return (
            int(value, 16)
            if isinstance(value, str) and value.startswith("0x")
            else int(value)
        )
    except ValueError:
        logger.error("Error converting value %s to integer.", value)


class RawTokenImbalances:
    """Class for computing token imbalances."""

    def __init__(self, web3: Web3, chain_name: str):
        self.web3 = web3
        self.chain_name = chain_name

    def get_transaction_receipt(self, tx_hash: str) -> TxReceipt | None:
        """
        Get the transaction receipt from the provided web3 instance.
        """
        try:
            return self.web3.eth.get_transaction_receipt(tx_hash)
        except Exception as ex:
            logger.error("Error getting transaction receipt: %s", ex)
            return None

    def get_transaction_trace(self, tx_hash: str) -> list[dict] | None:
        """Function used for retreiving trace to identify native ETH transfers."""
        try:
            res = self.web3.tracing.trace_transaction(tx_hash)
            return res
        except Exception as err:
            logger.error("Error occurred while fetching transaction trace: %s", err)
            return None

    def extract_actions(self, traces: list[AttributeDict], address: str) -> list[dict]:
        """Identify transfer events in trace involving the specified contract."""
        normalized_address = Web3.to_checksum_address(address)
        actions = []
        for trace in traces:
            if isinstance(trace, AttributeDict):
                action = trace.get("action", {})
                if (
                    Web3.to_checksum_address(action.get("from", ""))
                    == normalized_address
                    or Web3.to_checksum_address(action.get("to", ""))
                    == normalized_address
                ):
                    actions.append(dict(action))
        return actions

    def calculate_native_eth_imbalance(self, actions: list[dict], address: str) -> int:
        """Extract ETH imbalance from transfer actions."""
        # inflow is the total value transferred to address param
        inflow = sum(
            _to_int(action["value"])
            for action in actions
            if Web3.to_checksum_address(action.get("to", "")) == address
        )
        # outflow is the total value transferred out of address param
        outflow = sum(
            _to_int(action["value"])
            for action in actions
            if Web3.to_checksum_address(action.get("from", "")) == address
        )
        return inflow - outflow

    def extract_events(self, tx_receipt: dict) -> dict[str, list[dict]]:
        """Extract relevant events from the transaction receipt."""
        event_topics = compute_event_topics(self.web3)
        # transfer_topics are filtered to find imbalances for most ERC-20 tokens
        transfer_topics = {
            k: v for k, v in event_topics.items() if k in ["Transfer", "ERC20Transfer"]
        }
        # other_topics is used to find imbalances for SDAI, ETH transactions
        other_topics = {
            k: v for k, v in event_topics.items() if k not in transfer_topics
        }

        events: dict[str, list[dict]] = {name: [] for name in EVENT_TOPICS}
        for log in tx_receipt["logs"]:
            if log["topics"]:
                log_topic = log["topics"][0].hex()
                if log_topic in transfer_topics.values():
                    events["Transfer"].append(log)
                else:
                    for event_name, topic in other_topics.items():
                        if log_topic == topic:
                            events[event_name].append(log)
                            break
        return events

    def decode_event(self, event: dict) -> tuple[str | None, str | None, int | None]:
        """
        Decode transfer and withdrawal events.
        Returns from_address, to_address (for transfer), and value.
        """
        try:
            from_address = Web3.to_checksum_address(
                "0x" + event["topics"][1].hex()[-40:]
            )
            value_hex = event["data"]

            if isinstance(value_hex, bytes):
                value = int.from_bytes(value_hex, byteorder="big")
            else:
                value = int(value_hex, 16)

            if len(event["topics"]) > 2:  # Transfer event
                to_address = Web3.to_checksum_address(
                    "0x" + event["topics"][2].hex()[-40:]
                )
                return from_address, to_address, value
            else:  # Withdrawal or Deposit event for our purpose
                return from_address, None, value
        except Exception as e:
            logger.error("Error decoding event: %s", str(e))
            return None, None, None

    def process_event(
        self,
        event: dict,
        inflows: dict[str, int],
        outflows: dict[str, int],
        address: str,
    ) -> None:
        """Process a single event to update inflows and outflows."""
        from_address, to_address, value = self.decode_event(event)
        if from_address is None or to_address is None:
            return
        if to_address == from_address == address:
            # adds a positive amount of sell token entering the contract (fee withdrawal txs)
            inflows[event["address"]] = inflows.get(event["address"], 0) + value
            return
        if to_address == address:
            inflows[event["address"]] = inflows.get(event["address"], 0) + value
        if from_address == address:
            outflows[event["address"]] = outflows.get(event["address"], 0) + value

    def calculate_imbalances(
        self, events: dict[str, list[dict]], address: str
    ) -> dict[str, int]:
        """Calculate token imbalances from events."""
        inflows, outflows = {}, {}  # type: (dict, dict)
        for event in events["Transfer"]:
            self.process_event(event, inflows, outflows, address)

        imbalances = {
            token_address: inflows.get(token_address, 0)
            - outflows.get(token_address, 0)
            for token_address in set(inflows.keys()).union(outflows.keys())
        }
        return imbalances

    def update_weth_imbalance(
        self,
        events: dict[str, list[dict]],
        imbalances: dict[str, int],
        address: str,
    ) -> None:
        """Update the WETH imbalance in imbalances."""
        weth_imbalance = imbalances.get(WETH_TOKEN_ADDRESS, 0)
        for event in events["WithdrawalWETH"] + events["DepositWETH"]:
            from_address, _, value = self.decode_event(event)
            if from_address == address:
                if event in events["WithdrawalWETH"]:
                    weth_imbalance -= value
                elif event in events["DepositWETH"]:
                    weth_imbalance += value
        imbalances[WETH_TOKEN_ADDRESS] = weth_imbalance

    def update_native_eth_imbalance(
        self, imbalances: dict[str, int], native_eth_imbalance: int | None
    ) -> None:
        """Update the native ETH imbalance in imbalances."""
        if native_eth_imbalance is not None:
            imbalances[NATIVE_ETH_TOKEN_ADDRESS] = native_eth_imbalance

    def decode_sdai_event(self, event: dict) -> int | None:
        """Decode sDAI event."""
        try:
            # SDAI event has hex value at the end, which needs to be extracted
            value_hex = event["data"][-30:]
            if isinstance(value_hex, bytes):
                value = int.from_bytes(value_hex, byteorder="big")
            else:
                value = int(value_hex, 16)
            return value
        except Exception as e:
            logger.error(f"Error decoding sDAI event: {str(e)}")
            return None

    def process_sdai_event(
        self, event: dict, imbalances: dict[str, int], is_deposit: bool
    ) -> None:
        """Process an sDAI deposit or withdrawal event to update imbalances."""
        decoded_event_value = self.decode_sdai_event(event)
        if decoded_event_value is None:
            return
        if is_deposit:
            imbalances[SDAI_TOKEN_ADDRESS] = (
                imbalances.get(SDAI_TOKEN_ADDRESS, 0) + decoded_event_value
            )
        else:
            imbalances[SDAI_TOKEN_ADDRESS] = (
                imbalances.get(SDAI_TOKEN_ADDRESS, 0) - decoded_event_value
            )

    def update_sdai_imbalance(
        self, events: dict[str, list[dict]], imbalances: dict[str, int]
    ) -> None:
        """Update the sDAI imbalance in imbalances."""

        def filter_sdai_events(event_list: list[dict], is_deposit: bool) -> None:
            for event in event_list:
                if event["address"] == SDAI_TOKEN_ADDRESS:
                    for topic in event["topics"]:
                        if (
                            Web3.to_checksum_address("0x" + topic.hex()[-40:])
                            == SETTLEMENT_CONTRACT_ADDRESS
                        ):
                            self.process_sdai_event(event, imbalances, is_deposit)
                            break

        filter_sdai_events(events["DepositSDAI"], is_deposit=True)
        filter_sdai_events(events["WithdrawSDAI"], is_deposit=False)

    def compute_imbalances(self, tx_hash: str) -> dict[str, int]:
        try:
            tx_receipt = self.get_transaction_receipt(tx_hash)
            if not tx_receipt:
                raise ValueError(f"No transaction receipt found for {tx_hash}")

            traces = self.get_transaction_trace(tx_hash)
            if traces is None:
                raise ValueError(
                    f"Error fetching transaction trace for {tx_hash}. Marking transaction as unprocessed."
                )

            events = self.extract_events(tx_receipt)
            imbalances = self.calculate_imbalances(events, SETTLEMENT_CONTRACT_ADDRESS)

            native_eth_imbalance = None
            actions = []
            actions = self.extract_actions(traces, SETTLEMENT_CONTRACT_ADDRESS)
            native_eth_imbalance = self.calculate_native_eth_imbalance(
                actions, SETTLEMENT_CONTRACT_ADDRESS
            )

            if actions:
                self.update_weth_imbalance(
                    events, imbalances, SETTLEMENT_CONTRACT_ADDRESS
                )
                self.update_native_eth_imbalance(imbalances, native_eth_imbalance)

            self.update_sdai_imbalance(events, imbalances)
            return imbalances

        except Exception as e:
            logger.error("Error computing imbalances for %s: %s", tx_hash, e)
            raise


def main() -> None:
    """main function for finding imbalance for a single tx hash."""
    tx_hash = input("Enter transaction hash: ")
    chain_name, web3 = find_chain_with_tx(tx_hash)
    rt = RawTokenImbalances(web3, chain_name)
    try:
        imbalances = rt.compute_imbalances(tx_hash)
        if imbalances:
            logger.info(f"Token Imbalances on {chain_name}:")
            for token_address, imbalance in imbalances.items():
                logger.info(f"Token: {token_address}, Imbalance: {imbalance}")
        else:
            logger.info(
                f"No imbalances found for transaction {tx_hash} on {chain_name}."
            )
    except Exception as e:
        logger.error(e)


if __name__ == "__main__":
    main()
