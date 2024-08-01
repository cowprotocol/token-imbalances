""" Runs a basic test for raw imbalance calculation edge-cases. """
import os
from dotenv import load_dotenv
import pytest
from src.imbalances_script import RawTokenImbalances
from src.helper_functions import get_web3_instance

load_dotenv()


@pytest.mark.parametrize(
    "tx_hash, expected_imbalances",
    [
        # Native ETH buy
        (
            "0x749b557872d7d1f857719f619300df9621631f87338caa706154a3d7040fac9f",
            {
                "0x6B175474E89094C44Da98b954EedeAC495271d0F": 6286775129763176601,
                "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2": 12147750061816,
                "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE": 221116798827683,
            },
        ),
        # SDAI sell
        (
            "0xdae82500c69c66db4e4a8c64e1d6a95f3cdc5cb81a5a00228ce6f247b9b8cefd",
            {
                "0x83F20F44975D03b1b09e64809B757c47f942BEeA": 90419674604117409792,
                "0x6B175474E89094C44Da98b954EedeAC495271d0F": 360948092321672598,
            },
        ),
        # ERC404 Token Buy
        (
            "0xfcb1d20df8a90f5b4646a5d1818da407b3a78cfcb8291f477291f5c01115ca7a",
            {
                "0x9E9FbDE7C7a83c43913BddC8779158F1368F0413": -11207351687745217,
                "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2": 64641750602289665,
            },
        ),
        # Fee Withdrawal Transaction
        (
            "0x6c83fe83684b6f8ad0f8141aa4c359ad359c09b14c8ff9b9b2a0a80228ed10de",
            {
                "0x853d955aCEf822Db058eb8505911ED77F175b99e": 7064735278981936006,
                "0x3472A5A71965499acd81997a54BBA8D852C6E53d": 2852137014171065178,
                "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2": 4722264073109523,
                "0x0f2D719407FdBeFF09D87557AbB7232601FD9F29": 10246847087992681796,
            },
        ),
    ],
)
def test_imbalances(tx_hash, expected_imbalances):
    """
    Asserts imbalances match for main script with test values provided.
    """
    chain_name = os.getenv("CHAIN_NAME")
    rt = RawTokenImbalances(get_web3_instance(), chain_name)
    imbalances = rt.compute_imbalances(tx_hash)
    for token_address, expected_imbalance in expected_imbalances.items():
        assert imbalances.get(token_address) == expected_imbalance
