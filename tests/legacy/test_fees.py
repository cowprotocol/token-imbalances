"""End-to-end tests for fee computations"""

from hexbytes import HexBytes
from src.fees.compute_fees import compute_all_fees_of_batch

ratio_tolerance = 0.001
absolute_tolerance = 100


def absolute_tolerance_check(value_1: int, value_2: int, epsilon: float) -> bool:
    if abs(value_1 - value_2) < epsilon:
        return True
    else:
        return False


def ratio_tolerance_check(ratio: float, epsilon: float) -> bool:
    if (ratio > 1 - epsilon) and (ratio < 1 + epsilon):
        return True
    else:
        return False


def test_sample_trades():
    tx_hash_list = [
        "0x70d242d7991fbd3f91033e693436df9514cdf615d4a2230c5ed0557af37c073a",
        "0xce17b91e8f50a674c317a39cbfb4ca7e417af075a53b1aa0eece5aa957ed0bbe",
        "0x87ab7f4ee01388e85a6f1a1ebd6aff885b6a42fac0b9acd5cda9dd66bebfc0b9",
        "0x87ab7f4ee01388e85a6f1a1ebd6aff885b6a42fac0b9acd5cda9dd66bebfc0b9",
        "0xf9400f66210e3eab46fb66232196cde0e1bbe8cfc694489a13b766eae4a21c66",
    ]
    orders_list = [
        "0xc4be63dd6e3baf39f4b2ba1709f78c4971ae7d526a40dcea4eea94c5b0133d0831ae23b20c9f5d0e5fb1f864301d13793b63e1dc66d24952",
        "0x05babeb0e90f2f3a6ba999f397fbcb5e983eff1c1bade7fe0bb2cb9196919b615c9e070ec97e9cd64bd74b53049ca700ff68111466ce4929",
        "0x53e4f7041b532c0952fe3821b4e18a6f6b26fa403fb398efaeca129f2d8e22ce4b41cc5a22e0e2568b1e80756e5784a5b120805066be643a",
        "0xb415d0d7e0aeb27df3777de95933fa9b6cf3430e3a332cd73ef87d8e30787cc57bc5ddf54c57fe74bd5b9a14cae952e730bd847666be64f0",
        "0xa9fbfbe1f61606162b29c6a5df2eb4c0913929248e5ea9899797851f421f075040a50cf069e992aa4536211b23f286ef88752187ffffffff",
    ]
    protocol_fees_list = [
        265066228346000000,
        863347103526919000000000,
        0,
        2439671,
        0,
    ]
    partner_fees_list = [
        699996861102526000000,
        0,
        101968968211339000000,
        0,
        0,
    ]
    network_fees_list = [
        631761621422024452,
        301172642049802509484032,
        5701811,
        371687632145107059212288,
        247664759315072,
    ]
    for i, tx_hash in enumerate(tx_hash_list):
        protocol_fees, partner_fees, network_fees = compute_all_fees_of_batch(
            HexBytes(tx_hash)
        )
        uid = orders_list[i]
        if protocol_fees_list[i] * protocol_fees[uid][1] == 0:
            assert absolute_tolerance_check(
                protocol_fees_list[i], protocol_fees[uid][1], absolute_tolerance
            )
        else:
            protocol_fees_ratio = protocol_fees_list[i] / protocol_fees[uid][1]
            assert ratio_tolerance_check(protocol_fees_ratio, ratio_tolerance)

        if partner_fees_list[i] * partner_fees[uid][1] == 0:
            assert absolute_tolerance_check(
                partner_fees_list[i], partner_fees[uid][1], absolute_tolerance
            )
        else:
            partner_fees_ratio = partner_fees_list[i] / partner_fees[uid][1]
            assert ratio_tolerance_check(partner_fees_ratio, ratio_tolerance)

        if network_fees_list[i] * network_fees[uid][1] == 0:
            assert absolute_tolerance_check(
                network_fees_list[i], network_fees[uid][1], absolute_tolerance
            )
        else:
            network_fees_ratio = network_fees_list[i] / network_fees[uid][1]
            assert ratio_tolerance_check(network_fees_ratio, ratio_tolerance)


# hashes/orders to check

# Example 1
# hash = 0x70d242d7991fbd3f91033e693436df9514cdf615d4a2230c5ed0557af37c073a
# order_uid = 0xc4be63dd6e3baf39f4b2ba1709f78c4971ae7d526a40dcea4eea94c5b0133d0831ae23b20c9f5d0e5fb1f864301d13793b63e1dc66d24952
# Here we have both partner and protocol fees

# Example 2
# hash = 0xce17b91e8f50a674c317a39cbfb4ca7e417af075a53b1aa0eece5aa957ed0bbe
# order_uid = 0x05babeb0e90f2f3a6ba999f397fbcb5e983eff1c1bade7fe0bb2cb9196919b615c9e070ec97e9cd64bd74b53049ca700ff68111466ce4929
# Here we have partner fee but the partner fee recipient is the null address, in which case we redirect it to the DAO as protocol fee


# Example 3
# hash = 0x87ab7f4ee01388e85a6f1a1ebd6aff885b6a42fac0b9acd5cda9dd66bebfc0b9
# order_uid = 0x53e4f7041b532c0952fe3821b4e18a6f6b26fa403fb398efaeca129f2d8e22ce4b41cc5a22e0e2568b1e80756e5784a5b120805066be643a
# Here we only have partner fee

# Example 4
# hash = 0x87ab7f4ee01388e85a6f1a1ebd6aff885b6a42fac0b9acd5cda9dd66bebfc0b9
# order_uid = 0xb415d0d7e0aeb27df3777de95933fa9b6cf3430e3a332cd73ef87d8e30787cc57bc5ddf54c57fe74bd5b9a14cae952e730bd847666be64f0
# Here we only have protocol fee

# Example 5
# hash = 0xf9400f66210e3eab46fb66232196cde0e1bbe8cfc694489a13b766eae4a21c66
# order_uid = 0xa9fbfbe1f61606162b29c6a5df2eb4c0913929248e5ea9899797851f421f075040a50cf069e992aa4536211b23f286ef88752187ffffffff
# Here we don't have protocol or partner fee
