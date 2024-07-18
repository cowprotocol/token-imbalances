"""Exceptions for circuit breaker"""

from hexbytes import HexBytes


class MissingOnchainData(Exception):
    """This exception signals missing onchain data.
    This can happen due to nodes being out of sync.
    This exception is not critical and should result in rechecking later.
    """


class MissingCompetitionData(Exception):
    """This exception signals missing competition data.
    This should only happen if the autopilot malfunctions.
    This exception should result in blacklisting.
    """

    def __init__(self, message: str, /, solver: HexBytes) -> None:
        super().__init__(message)
        self.solver: HexBytes = solver


class MissingTradeData(Exception):
    """This exceptions signals missing trade data
    This might happend due to delayes indexing or updating of tables in the database.
    It should result in rechecking of the auction at a later time.
    """


class InvalidSettlement(Exception):
    """This exception signals that a check for the settlement failed.
    This only happens when all data is available and the check fails.
    It should always result in blacklisting.
    """

    def __init__(self, message: str, /, solver: HexBytes) -> None:
        super().__init__(message)
        self.solver: HexBytes = solver


class WhitelistedSolver(Exception):
    """This exception signals that a settlement comes from a whitelisted solver.
    This exception should result in skipping all checks.
    """

    def __init__(self, message: str, /, solver: HexBytes) -> None:
        super().__init__(message)
        self.solver: HexBytes = solver
