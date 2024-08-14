from abc import ABC, abstractmethod


class AbstractPriceProvider(ABC):
    """
    abstract base class for all price providers.
    """

    @abstractmethod
    def get_price(self, block_number: int, token_address: str) -> float | None:
        """gets the price of a token."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """gets the name of the price provider."""
        pass
