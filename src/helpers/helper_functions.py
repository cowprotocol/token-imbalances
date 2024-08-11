"""
This file contains some auxiliary functions
"""
from __future__ import annotations
import sys
import os
import logging
from typing import List, Optional, Tuple
from dotenv import load_dotenv
from hexbytes import HexBytes
from web3 import Web3
from src.constants import SETTLEMENT_CONTRACT_ADDRESS

load_dotenv()
NODE_URL = os.getenv("NODE_URL")


def get_logger(filename: Optional[str] = None) -> logging.Logger:
    """
    get_logger() returns a logger object that can write to a file, terminal or only file if needed.
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Clear any existing handlers to avoid duplicate logs
    if logger.hasHandlers():
        logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter("%(levelname)s - %(message)s")

    # Handler for stdout (INFO and lower)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.INFO)
    stdout_handler.setFormatter(formatter)

    # ERROR and above logs will not be logged to stdout
    stdout_handler.addFilter(lambda record: record.levelno < logging.ERROR)

    # Handler for stderr (ERROR and higher)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.ERROR)
    stderr_handler.setFormatter(formatter)

    # Add handlers to the logger
    logger.addHandler(stdout_handler)
    logger.addHandler(stderr_handler)

    if filename:
        file_handler = logging.FileHandler(filename + ".log", mode="w")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_web3_instance() -> Web3:
    """
    returns a Web3 instance for the given blockchain via chain name.
    """
    return Web3(Web3.HTTPProvider(NODE_URL))


def get_finalized_block_number(web3: Web3) -> int:
    """
    Get the number of the most recent finalized block.
    """
    return web3.eth.block_number - 67


def get_tx_hashes_blocks(
    web3: Web3, start_block: int, end_block: int
) -> List[Tuple[str, int]]:
    """
    Get all transaction hashes appended with corresponding block (tuple) transactions
    involving the settlement contract.
    """
    tx_hashes_blocks = []

    for block_number in range(start_block, end_block + 1):
        block = web3.eth.get_block(block_number, full_transactions=True)
        for tx in block.transactions:  # type: ignore[attr-defined]
            if tx.to and tx.to.lower() == SETTLEMENT_CONTRACT_ADDRESS.lower():
                tx_hashes_blocks.append((tx.hash.hex(), block_number))
    return tx_hashes_blocks


def get_auction_id(web3: Web3, tx_hash: str) -> int:
    """
    Method that finds an auction id given a transaction hash.
    """
    transaction = web3.eth.get_transaction(HexBytes(tx_hash))
    call_data = transaction["input"]
    # convert call_data to hexString if it's in hexBytes
    call_data_bytes = bytes.fromhex(
        call_data.hex()[2:] if isinstance(call_data, HexBytes) else call_data[2:]
    )
    # convert bytes to int
    auction_id = int.from_bytes(call_data_bytes[-8:], byteorder="big")
    return auction_id


def read_sql_file(file_path: str) -> str:
    """This function reads a file (SQL) and returns its content as a string."""
    with open(file_path, "r") as file:
        return file.read()
