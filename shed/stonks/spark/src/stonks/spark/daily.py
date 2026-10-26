import logging
from datetime import date

from stonks.spark.bars import bars_summary, latest_prices, price_history, yahoo_bars
from stonks.spark.readers import read_raw_charts, read_universe
from stonks.spark.writers import write_history, write_prices

logger = logging.getLogger(__name__)

YAHOO = "yahoo"
PRICES = "prices"
HISTORY = "history"


def raw_source_path(storage: dict, s3: dict, source: str) -> str:
    prefix = storage["raw_prefix"].rstrip("/")
    return f"s3a://{s3['bucket']}/{prefix}/source={source}"


def universe_path(storage: dict, s3: dict, trade_date: date) -> str:
    prefix = storage["universe_prefix"].rstrip("/")
    return f"s3a://{s3['bucket']}/{prefix}/trade_date={trade_date.isoformat()}/universe.json"


def curated_path(storage: dict, s3: dict, table: str, trade_date: date) -> str:
    prefix = storage["curated_prefix"].rstrip("/")
    return f"s3a://{s3['bucket']}/{prefix}/{table}/trade_date={trade_date.isoformat()}"


def run_daily(spark, trade_date: date, storage: dict, s3: dict) -> None:
    charts_path = raw_source_path(storage, s3, YAHOO)
    snapshot_path = universe_path(storage, s3, trade_date)
    prices_path = curated_path(storage, s3, PRICES, trade_date)
    history_path = curated_path(storage, s3, HISTORY, trade_date)
    raw = read_raw_charts(spark, charts_path)
    universe = read_universe(spark, snapshot_path)
    bars = yahoo_bars(raw, universe, trade_date)
    bars.persist()
    try:
        summary = bars_summary(bars)
        prices = latest_prices(bars)
        write_prices(prices, prices_path)
        history = price_history(bars)
        write_history(history, history_path)
    finally:
        bars.unpersist()
    logger.info(
        "yahoo_bars trade_date=%s rows=%s instruments=%s first_date=%s last_date=%s charts=%s universe=%s prices=%s history=%s",
        trade_date,
        summary["rows"],
        summary["instruments"],
        summary["first_date"],
        summary["last_date"],
        charts_path,
        snapshot_path,
        prices_path,
        history_path,
    )
