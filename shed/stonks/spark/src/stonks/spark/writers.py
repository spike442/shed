from pyspark.sql import DataFrame


def write_prices(prices: DataFrame, path: str) -> None:
    single_file = prices.coalesce(1)
    single_file.write.mode("overwrite").parquet(path)
