""" A daemon to inspect all Settlement calls to the settlement contract in almost-real time.
"""

# pylint: disable=logging-fstring-interpolation

from hexbytes import HexBytes
from src.fee_calculations.web3_api import Blockchain
from src.fee_calculations.database_api import Database

from src.fee_calculations.exceptions import (
    MissingCompetitionData,
    MissingTradeData,
    InvalidSettlement,
)
from src.fee_calculations.logger import logger
from fractions import Fraction


def compute_all_fees(
    tx_hash: HexBytes,
    onchain_fetcher: Blockchain,
    offchain_fetcher: Database,
):
    logger.debug(f"Processing hash {tx_hash!r}")
    try:
        onchain_data = onchain_fetcher.get_onchain_data(tx_hash)
        offchain_data = offchain_fetcher.get_offchain_data(onchain_data)

        res = []
        for trade in offchain_data.trades:
            trade_raw_surplus = int(trade.raw_surplus())
            protocol_fee = 0
            clearing_prices = offchain_data.clearing_prices

            if trade.kind == "sell":
                trade_onchain_surplus = trade.buy_amount - trade.limit_buy_amount
                if trade_raw_surplus > trade_onchain_surplus:
                    protocol_fee = trade_raw_surplus - trade_onchain_surplus
                    res.append(
                        (
                            onchain_data.auction_id,
                            onchain_data.tx_hash,
                            trade.order_uid,
                            trade.surplus_token(),
                            protocol_fee,
                            "protocol_fee",
                        )
                    )
                raw_buy_amount = trade.buy_amount + max(
                    trade_raw_surplus - trade_onchain_surplus, 0
                )
                network_fee = trade.sell_amount - (
                    raw_buy_amount
                    * clearing_prices[trade.buy_token]
                    // clearing_prices[trade.sell_token]
                )
                res.append(
                    (
                        onchain_data.auction_id,
                        onchain_data.tx_hash,
                        trade.order_uid,
                        trade.sell_token,
                        network_fee,
                        "network_fee",
                    )
                )
            else:
                trade_onchain_surplus = trade.limit_sell_amount - trade.sell_amount
                if trade_raw_surplus > trade_onchain_surplus:
                    protocol_fee = trade_raw_surplus - trade_onchain_surplus
                    res.append(
                        (
                            onchain_data.auction_id,
                            onchain_data.tx_hash,
                            trade.order_uid,
                            trade.surplus_token(),
                            protocol_fee,
                        )
                    )
                network_fee = trade.sell_amount - max(trade_raw_surplus - trade_onchain_surplus, 0) - (
                    raw_buy_amount
                    * clearing_prices[trade.buy_token]
                    // clearing_prices[trade.sell_token]
                )
                res.append(
                    (
                        onchain_data.auction_id,
                        onchain_data.tx_hash,
                        trade.order_uid,
                        trade.sell_token,
                        network_fee,
                        "network_fee",
                    )
                )
        return res
    except (ConnectionError, MissingTradeData) as err:
        logger.info(
            f"Problem fetching data for tx {tx_hash.hex()}: {err}\t" "rechecking hash"
        )
    except (MissingCompetitionData, InvalidSettlement) as err:
        logger.error(f"Problem checking hash tx {tx_hash.hex()}: {err}\t")
    except Exception as err:  # pylint: disable=broad-exception-caught
        logger.error(
            "Uncaught exception for tx " f"{tx_hash.hex()}: {err}\t skipping hash"
        )
    return []
