from hexbytes import HexBytes
from src.fees.compute_fees import compute_all_fees_of_batch
from src.helpers.config import logger


def log_token_data(title: str, data: dict, name: str):
    logger.info(title)
    for token, value in data.items():
        logger.info(f"Token Address: {token}, {name}: {value}")


def main():
    protocol_fees, partner_fees, network_fees = compute_all_fees_of_batch(
        HexBytes(input("tx hash: "))
    )
    log_token_data("Protocol Fees:", protocol_fees, "Protocol Fee")
    log_token_data("Partner Fees:", partner_fees, "Partner Fee")
    log_token_data("Network Fees:", network_fees, "Network Fee")
    # e.g. input: 0x980fa3f8ff95c504ba61e054e5c3e50ea36b892f865703b8a665564ac0beb1f4


if __name__ == "__main__":
    main()
