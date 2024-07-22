"""
Class to connect to the orderbook db and fetch relevant data.
"""

# pylint: disable=logging-fstring-interpolation

from fractions import Fraction
import math
import os
from typing import Any

from dotenv import load_dotenv
from hexbytes import HexBytes
from sqlalchemy import create_engine, text, Row

from src.fee_calculations.exceptions import MissingCompetitionData, MissingTradeData
from src.fee_calculations.logger import logger
from src.fee_calculations.models import (
    OnchainTrade,
    OffchainTrade,
    OffchainSettlementData,
    OnchainSettlementData,
    ProtocolFee,
    SurplusFee,
    VolumeFee,
    PriceImprovementFee,
)


class Database:
    """
    This is a class for connecting to the db, and contains a few functions that
    fetch necessary data to run the checks that we need.
    """

    def __init__(self) -> None:
        load_dotenv()

        barn_db_url = os.getenv("BARN_DB_URL")
        prod_db_url = os.getenv("PROD_DB_URL")
        self.barn_db = create_engine(f"postgresql+psycopg2://{barn_db_url}")
        self.prod_db = create_engine(f"postgresql+psycopg2://{prod_db_url}")
        logger.debug("Successfully connected to databsase.")

    def get_offchain_data(
        self, onchain_data: OnchainSettlementData
    ) -> OffchainSettlementData:
        """
        Methohd that fetches all necessary data from the db.
        """
        # pylint: disable=too-many-locals
        solver = onchain_data.solver
        auction_id = onchain_data.auction_id

        competition_data = self.get_competition_data(auction_id, solver)
        trade_data = self.get_trade_data(auction_id, solver)

        offchain_data = self.query_result_to_offchain_data(
            onchain_data, competition_data, trade_data
        )
        return offchain_data

    def query_result_to_offchain_data(
        self,
        onchain_data: OnchainSettlementData,
        competition_data: Row[Any],
        trade_data: list[Row[Any]],
    ) -> OffchainSettlementData:
        """Turn Row from database query into OffchainSettlementData"""
        # pylint: disable=too-many-locals
        json_data = competition_data._asdict()
        auction_id = json_data["auction_id"]
        solver = HexBytes(json_data["solution"]["solverAddress"])
        call_data = HexBytes(json_data["solution"]["callData"])

        trades: list[OffchainTrade] = []
        trade_data_dict = {HexBytes(trade.order_uid): trade for trade in trade_data}
        onchain_trades_dict = {trade.order_uid: trade for trade in onchain_data.trades}
        for order in json_data["solution"]["orders"]:
            order_uid = HexBytes(order["id"])
            onchain_trade = onchain_trades_dict[order_uid]
            trade_datum = trade_data_dict[order_uid]  # this fails sometimes

            protocol_fees = self.parse_protocol_fees(trade_datum)
            quote_sell_amount, quote_buy_amount = self.compute_quote_amounts(
                onchain_trade, trade_datum
            )

            trade = OffchainTrade(
                HexBytes(order["id"]),
                onchain_trade.owner,
                onchain_trade.sell_token,
                onchain_trade.buy_token,
                int(order["sellAmount"]),
                int(order["buyAmount"]),
                onchain_trade.limit_sell_amount,
                onchain_trade.limit_buy_amount,
                onchain_trade.kind,
                quote_sell_amount,
                quote_buy_amount,
                protocol_fees,
            )
            trades.append(trade)
        valid_orders = {HexBytes(order) for order in json_data["auction"]["orders"]}
        native_prices = {
            HexBytes(address): int(price)
            for address, price in json_data["auction"]["prices"].items()
        }
        # combining addresses from
        # https://solver-instances.s3.eu-central-1.amazonaws.com/prod/mainnet/auction/9097291.json
        # and
        # https://dune.com/cowprotocol/cowamms
        # this should be read from the competition endpoint whenever jit order addresses are added
        # there
        jit_order_addresses: set[HexBytes] = {
            HexBytes("0xbeef5afe88ef73337e5070ab2855d37dbf5493a4"),
            HexBytes("0xb3bf81714f704720dcb0351ff0d42eca61b069fc"),
            HexBytes("0x7c420c3a33aa87bf0c6327930b93376079e06a18"),
            HexBytes("0x027e1cbf2c299cba5eb8a2584910d04f1a8aa403"),
            HexBytes("0xe96b516d40db176f6b120fd8ff025de6b7bb32ee"),
            HexBytes("0x301076c36e034948a747bb61bab9cd03f62672e3"),
            HexBytes("0xc6b13d5e662fa0458f03995bcb824a1934aa895f"),
            HexBytes("0x9941fd7db2003308e7ee17b04400012278f12ac6"),
            HexBytes("0xd7cb8cc1b56356bb7b78d02e785ead28e2158660"),
            HexBytes("0x079c868f97aed8e0d03f11e1529c3b056ff21cea"),
        }
        clearing_prices = {
            HexBytes(address): int(price)
            for address, price in json_data["solution"]["clearingPrices"].items()
        }
        return OffchainSettlementData(
            auction_id,
            solver,
            call_data,
            trades,
            valid_orders,
            jit_order_addresses,
            native_prices,
            clearing_prices,
        )

    def get_competition_data(self, auction_id: int, solver: HexBytes) -> Row[Any]:
        """Fetch competition data from the database"""
        results: list[Row[Any]] = []
        for engine in [self.prod_db, self.barn_db]:
            with open(
                "src/queries/competition_table.sql", mode="r", encoding="utf-8"
            ) as file:
                query_file = (
                    file.read()
                    .replace(
                        "{{auction_id}}",
                        str(auction_id),
                    )
                    .replace(
                        "{{solver}}",
                        solver.hex(),
                    )
                )
                with engine.connect() as con:
                    results = results + list(con.execute(text(query_file)).fetchall())

        if len(results) == 0:
            raise MissingCompetitionData(
                f"Offchain settlement data not found for id {auction_id}.",
                solver=solver,
            )

        if len(results) > 1:
            logger.warning(
                f"More than one competition data with auction id {auction_id}. Using the first "
                f"entry for computation."
            )

        return results[0]

    def get_trade_data(self, auction_id: int, solver: HexBytes) -> list[Row[Any]]:
        """Fetch trade data from database"""
        results: list[Row[Any]] = []
        for engine in [self.prod_db, self.barn_db]:
            with open("src/queries/trade_data.sql", mode="r", encoding="utf-8") as file:
                query_file = (
                    file.read()
                    .replace(
                        "{{auction_id}}",
                        str(auction_id),
                    )
                    .replace(
                        "{{solver}}",
                        solver.hex(),
                    )
                )
                with engine.connect() as con:
                    results = results + list(con.execute(text(query_file)).fetchall())

        if len(results) == 0:
            raise MissingTradeData(
                f"Off-chain trade data of auction {auction_id} is missing."
            )
        return results

    def parse_protocol_fees(self, trade_datum: Row[Any]) -> list[ProtocolFee]:
        """Pase protocol fees into sorted list"""
        protocol_fees: list[ProtocolFee] = []
        if trade_datum.protocol_fee_kind is None:
            return protocol_fees
        protocol_fee_kinds = str(trade_datum.protocol_fee_kind).strip("{}").split(",")
        for (
            _,
            protocol_fee_kind,
            surplus_factor,
            surplus_max_volume_factor,
            volume_factor,
            price_improvement_factor,
            price_improvement_max_volume_factor,
        ) in sorted(
            zip(
                trade_datum.application_order,
                protocol_fee_kinds,
                trade_datum.surplus_factor,
                trade_datum.surplus_max_volume_factor,
                trade_datum.volume_factor,
                trade_datum.price_improvement_factor,
                trade_datum.price_improvement_max_volume_factor,
            )
        ):
            if protocol_fee_kind == "surplus":
                protocol_fees.append(
                    SurplusFee(
                        Fraction(surplus_factor), Fraction(surplus_max_volume_factor)
                    )
                )
            elif protocol_fee_kind == "volume":
                protocol_fees.append(VolumeFee(Fraction(volume_factor)))
            elif protocol_fee_kind == "priceimprovement":
                protocol_fees.append(
                    PriceImprovementFee(
                        Fraction(price_improvement_factor),
                        Fraction(price_improvement_max_volume_factor),
                    )
                )
            else:
                raise ValueError(f"Fee kind {protocol_fee_kind} is invalid.")

        return protocol_fees

    def compute_quote_amounts(
        self, onchain_trade: OnchainTrade, trade_datum: Row[Any]
    ) -> tuple[int, int]:
        """Compute effective quote amounts"""
        if trade_datum.quote_buy_amount is None:
            # if quotes are missing, use limit prices
            quote_sell_amount = onchain_trade.limit_sell_amount
            quote_buy_amount = onchain_trade.limit_buy_amount
        elif onchain_trade.kind == "sell":
            quote_sell_amount = int(trade_datum.quote_sell_amount)
            # fee intentionally uses inaccurate math
            quote_fee_amount = int(
                int(trade_datum.quote_gas_amount)
                * trade_datum.quote_gas_price
                / trade_datum.quote_sell_token_price
            )
            quote_exchange_rate = Fraction(
                int(trade_datum.quote_buy_amount), int(trade_datum.quote_sell_amount)
            )
            quote_buy_amount = math.ceil(
                (quote_sell_amount - quote_fee_amount) * quote_exchange_rate
            )
        elif onchain_trade.kind == "buy":
            quote_buy_amount = int(trade_datum.quote_buy_amount)
            # fee intentionally uses inaccurate math
            quote_fee_amount = int(
                int(trade_datum.quote_gas_amount)
                * trade_datum.quote_gas_price
                / trade_datum.quote_sell_token_price
            )
            quote_sell_amount = int(
                int(trade_datum.quote_sell_amount) + quote_fee_amount
            )
        else:
            raise ValueError(f"Order kind {trade_datum.kind} is invalid.")
        return quote_sell_amount, quote_buy_amount
