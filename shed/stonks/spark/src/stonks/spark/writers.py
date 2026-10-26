from pyspark.sql import DataFrame


def write_prices(prices: DataFrame, path: str) -> None:
    single_file = prices.coalesce(1)
    single_file.write.mode("overwrite").parquet(path)


def write_history(history: DataFrame, path: str) -> None:
    by_instrument = history.repartition("isin").sortWithinPartitions("bar_date")
    by_instrument.write.mode("overwrite").partitionBy("isin").parquet(path)
