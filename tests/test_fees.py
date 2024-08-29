import pytest
from hexbytes import HexBytes
from src.fees.compute_fees import batch_fee_imbalances


def test_batch_fee_imbalances():
    """
    Test the batch_fee_imbalances function with a valid transaction hash.
    """
    tx_hash = "0x714bb3b1a804af7a493bcfa991b9859e03c52387b027783f175255885fa97dbd"
    protocol_fees, network_fees = batch_fee_imbalances(HexBytes(tx_hash))

    # verify that the returned fees are dicts
    assert isinstance(protocol_fees, dict), "Protocol fees should be a dict."
    assert isinstance(network_fees, dict), "Network fees should be a dict."

    # Check that keys and values in the dict have the correct types
    for token, fee in protocol_fees.items():
        assert isinstance(token, str), "Token address should be string."
        assert isinstance(fee, int), "Fee amount should be int."

    for token, fee in network_fees.items():
        assert isinstance(token, str), "Token address should be string."
        assert isinstance(fee, int), "Fee amount should be int."


if __name__ == "__main__":
    pytest.main()
