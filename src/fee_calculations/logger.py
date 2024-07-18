"""
This file contains some logging functions
"""

import logging
import sys


def get_logger(name: str = "default") -> logging.Logger:
    """Get a logger
    The resulting logger logs errors to stderr and less severe logs to stdout
    """

    result_logger = logging.getLogger(name)
    result_logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(levelname)s - %(message)s")

    main_handler = logging.StreamHandler(sys.stdout)
    main_handler.setFormatter(formatter)
    main_handler.setLevel(logging.DEBUG)
    main_handler.addFilter(lambda record: record.levelno < logging.ERROR)

    error_handler = logging.StreamHandler(sys.stderr)
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.ERROR)

    result_logger.addHandler(main_handler)
    result_logger.addHandler(error_handler)

    return result_logger


logger = get_logger()
