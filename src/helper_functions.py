"""
This file contains some auxiliary functions
"""
from __future__ import annotations
import sys
import logging
from typing import Optional


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
