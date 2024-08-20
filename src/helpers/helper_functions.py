"""
This file contains some auxiliary functions
"""
from __future__ import annotations
import sys
import os
import logging
from dotenv import load_dotenv
from web3 import Web3
from contracts.erc20_abi import erc20_abi

load_dotenv()
NODE_URL = os.getenv("NODE_URL")


def get_logger(filename: str | None = None) -> logging.Logger:
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


def read_sql_file(file_path: str) -> str:
    """This function reads a file (SQL) and returns its content as a string."""
    with open(file_path, "r") as file:
        return file.read()


def extract_params(price_params: dict, is_block: bool):
    """Extract relevant parameters for fetching price from provider."""
    if is_block:
        return price_params.get("token_address"), price_params.get("block_number")
    return price_params.get("token_address"), price_params.get("tx_hash")


def set_params(token_address: str, block_number: int, tx_hash: str):
    """Build dictionary for price fetching using params."""
    return {
        "tx_hash": tx_hash,
        "block_number": block_number,
        "token_address": token_address,
    }


def get_token_decimals(token_address: str) -> int:
    """Get number of decimals for a token."""
    web3 = get_web3_instance()
    contract = web3.eth.contract(
        address=Web3.to_checksum_address(token_address), abi=erc20_abi
    )
    return contract.functions.decimals().call()
