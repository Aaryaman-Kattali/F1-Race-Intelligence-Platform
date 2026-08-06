"""
PySpark telemetry feature engineering job.

Processes raw lap-by-lap telemetry into analytical features using genuine Spark
operations (window functions, groupBy/agg, UDFs).

Implemented using PySpark to demonstrate distributed processing patterns.
The F1 telemetry dataset for a single season (~thousands of rows) doesn't
require Spark's parallelism — the same job scales to a full multi-season
telemetry archive where the volume would justify it.

Usage:
    spark-submit src/processing/telemetry_spark_job.py \\
        --year 2024 --input-path data/laps.parquet --output-path data/features.parquet

    # Or reading from BigQuery:
    spark-submit src/processing/telemetry_spark_job.py \\
        --year 2024 --source bigquery --bq-table f1_raw.lap_times
"""

import argparse
import logging
import sys
from pathlib import Path

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql import types as T
from pyspark.sql.window import Window

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Spark session
# ---------------------------------------------------------------------------


def create_spark_session(app_name: str = "F1-Telemetry-Features",
                         master: str = "local[*]") -> SparkSession:
    """Create SparkSession configured for local or cluster mode."""
    builder = (
        SparkSession.builder
        .appName(app_name)
        .master(master)
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.sql.shuffle.partitions", "8")
        .config("spark.driver.memory", "2g")
    )
    return builder.getOrCreate()


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_from_parquet(spark: SparkSession, path: str) -> DataFrame:
    """Load lap telemetry from local parquet files."""
    return spark.read.parquet(path)


def load_from_bigquery(spark: SparkSession, table: str,
                       project_id: str) -> DataFrame:
    """Load lap telemetry from BigQuery."""
    return (
        spark.read
        .format("bigquery")
        .option("table", f"{project_id}.{table}")
        .option("viewsEnabled", "true")
        .load()
    )


def load_sample_data(spark: SparkSession, year: int) -> DataFrame:
    """
    Load sample data from FastF1 into a Spark DataFrame.
    Used when no parquet/BigQuery source is available.
    """
    try:
        import fastf1
        import os

        cache_dir = os.path.join("data", "fastf1_cache")
        fastf1.Cache.enable_cache(cache_dir)

        schedule = fastf1.get_event_schedule(year)
        all_laps = []

        # Load first 3 circuits for demo
        for _, event in list(schedule.iterrows())[:3]:
            race_round = int(event.get("RoundNumber", 0))
            event_name = str(event.get("EventName", ""))
            if race_round == 0:
                continue

            try:
                session = fastf1.get_session(year, race_round, "Race")
                session.load()

                for _, lap in session.laps.iterrows():
                    lt = lap.get("LapTime")
                    s1 = lap.get("Sector1Time")
                    s2 = lap.get("Sector2Time")
                    s3 = lap.get("Sector3Time")

                    all_laps.append({
                        "year": year,
                        "round": race_round,
                        "circuit_name": event_name,
                        "session_type": "RACE",
                        "driver_code": str(lap.get("Driver", "")),
                        "lap_number": int(lap.get("LapNumber", 0)),
                        "lap_time_seconds": lt.total_seconds() if lt and hasattr(lt, "total_seconds") else None,
                        "sector1_seconds": s1.total_seconds() if s1 and hasattr(s1, "total_seconds") else None,
                        "sector2_seconds": s2.total_seconds() if s2 and hasattr(s2, "total_seconds") else None,
                        "sector3_seconds": s3.total_seconds() if s3 and hasattr(s3, "total_seconds") else None,
                        "compound": str(lap.get("Compound", "")),
                        "tyre_life": int(lap.get("TyreLife", 0)) if lap.get("TyreLife") is not None else None,
                        "stint": int(lap.get("Stint", 0)) if lap.get("Stint") is not None else None,
                        "position": int(lap.get("Position", 0)) if lap.get("Position") is not None else None,
                    })
            except Exception as e:
                logger.warning(f"Skipping round {race_round}: {e}")

        if not all_laps:
            raise ValueError("No lap data extracted")

        schema = T.StructType([
            T.StructField("year", T.IntegerType()),
            T.StructField("round", T.IntegerType()),
            T.StructField("circuit_name", T.StringType()),
            T.StructField("session_type", T.StringType()),
            T.StructField("driver_code", T.StringType()),
            T.StructField("lap_number", T.IntegerType()),
            T.StructField("lap_time_seconds", T.DoubleType()),
            T.StructField("sector1_seconds", T.DoubleType()),
            T.StructField("sector2_seconds", T.DoubleType()),
            T.StructField("sector3_seconds", T.DoubleType()),
            T.StructField("compound", T.StringType()),
            T.StructField("tyre_life", T.IntegerType()),
            T.StructField("stint", T.IntegerType()),
            T.StructField("position", T.IntegerType()),
        ])

        return spark.createDataFrame(all_laps, schema=schema)

    except Exception as e:
        logger.error(f"Failed to load sample data: {e}")
        raise


# ---------------------------------------------------------------------------
# Feature engineering (genuine Spark operations)
# ---------------------------------------------------------------------------


def filter_outlier_laps(df: DataFrame) -> DataFrame:
    """Remove pit in/out laps and outlier times (>110% of driver's median)."""
    # Calculate per-driver-per-stint median lap time
    driver_stint_window = Window.partitionBy("driver_code", "round", "stint")

    df_with_stats = df.withColumn(
        "median_lap",
        F.percentile_approx("lap_time_seconds", 0.5).over(driver_stint_window)
    )

    # Keep laps within 110% of median (filters pit laps, safety car anomalies)
    return (
        df_with_stats
        .filter(F.col("lap_time_seconds").isNotNull())
        .filter(F.col("lap_time_seconds") > 0)
        .filter(F.col("lap_time_seconds") <= F.col("median_lap") * 1.10)
        .drop("median_lap")
    )


def compute_stint_degradation(df: DataFrame) -> DataFrame:
    """
    Compute tire degradation features using window functions.

    For each driver/stint, calculates:
    - Lap-over-lap time delta (how much slower each lap is vs previous)
    - Cumulative degradation slope
    """
    stint_window = Window.partitionBy(
        "driver_code", "round", "stint"
    ).orderBy("lap_number")

    return (
        df
        # Lap-over-lap delta
        .withColumn(
            "prev_lap_time",
            F.lag("lap_time_seconds", 1).over(stint_window)
        )
        .withColumn(
            "lap_delta",
            F.col("lap_time_seconds") - F.col("prev_lap_time")
        )
        # Rolling average delta over 3-lap window (smoothed degradation)
        .withColumn(
            "rolling_delta_3",
            F.avg("lap_delta").over(
                stint_window.rowsBetween(-1, 1)
            )
        )
        # Stint lap index (1, 2, 3, ... within each stint)
        .withColumn(
            "stint_lap_index",
            F.row_number().over(stint_window)
        )
        .drop("prev_lap_time")
    )


def compute_pace_features(df: DataFrame) -> DataFrame:
    """
    Compute pace delta to leader per lap using window functions.

    Uses a partition by (round, lap_number) to find the leader's time
    on each lap and compute each driver's gap.
    """
    lap_window = Window.partitionBy("round", "lap_number")

    return (
        df
        .withColumn(
            "leader_lap_time",
            F.min("lap_time_seconds").over(lap_window)
        )
        .withColumn(
            "pace_delta_to_leader",
            F.col("lap_time_seconds") - F.col("leader_lap_time")
        )
        .drop("leader_lap_time")
    )


def compute_consistency_features(df: DataFrame) -> DataFrame:
    """
    Compute rolling consistency scores (stddev of lap times).

    Uses a 5-lap sliding window per driver per race.
    """
    rolling_window = Window.partitionBy(
        "driver_code", "round"
    ).orderBy("lap_number").rowsBetween(-2, 2)

    return (
        df
        .withColumn(
            "rolling_stddev_5",
            F.stddev("lap_time_seconds").over(rolling_window)
        )
        .withColumn(
            "consistency_score",
            F.lit(1.0) / (F.lit(1.0) + F.coalesce(F.col("rolling_stddev_5"), F.lit(0.0)))
        )
    )


def compute_sector_features(df: DataFrame) -> DataFrame:
    """
    Compute sector time deltas and identify strongest sectors per driver.
    """
    driver_race_window = Window.partitionBy("driver_code", "round")

    return (
        df
        .withColumn("avg_s1", F.avg("sector1_seconds").over(driver_race_window))
        .withColumn("avg_s2", F.avg("sector2_seconds").over(driver_race_window))
        .withColumn("avg_s3", F.avg("sector3_seconds").over(driver_race_window))
        .withColumn(
            "s1_delta",
            F.col("sector1_seconds") - F.col("avg_s1")
        )
        .withColumn(
            "s2_delta",
            F.col("sector2_seconds") - F.col("avg_s2")
        )
        .withColumn(
            "s3_delta",
            F.col("sector3_seconds") - F.col("avg_s3")
        )
        .drop("avg_s1", "avg_s2", "avg_s3")
    )


def compute_teammate_comparison(df: DataFrame) -> DataFrame:
    """
    Compute head-to-head teammate pace comparison.

    This requires knowing team assignments, which we approximate by
    grouping drivers who share the same circuit/position patterns.
    For simplicity, we add a per-lap rank within each race.
    """
    race_lap_window = Window.partitionBy(
        "round", "lap_number"
    ).orderBy("lap_time_seconds")

    return df.withColumn(
        "lap_rank",
        F.rank().over(race_lap_window)
    )


def compute_aggregate_features(df: DataFrame) -> DataFrame:
    """
    Aggregate per-driver-per-race features using groupBy + agg.

    This is the final summary table — one row per driver per race.
    """
    return (
        df
        .groupBy("year", "round", "circuit_name", "driver_code")
        .agg(
            F.count("*").alias("total_laps"),
            F.round(F.avg("lap_time_seconds"), 3).alias("avg_lap_time"),
            F.round(F.min("lap_time_seconds"), 3).alias("fastest_lap"),
            F.round(F.max("lap_time_seconds"), 3).alias("slowest_lap"),
            F.round(F.stddev("lap_time_seconds"), 3).alias("lap_time_stddev"),
            F.round(F.avg("consistency_score"), 3).alias("avg_consistency"),
            F.round(F.avg("pace_delta_to_leader"), 3).alias("avg_pace_delta"),
            F.round(F.avg("lap_delta"), 4).alias("avg_degradation_per_lap"),
            F.round(F.avg("rolling_delta_3"), 4).alias("avg_smoothed_degradation"),
            F.countDistinct("stint").alias("num_stints"),
            F.countDistinct("compound").alias("num_compounds"),
            F.first("compound").alias("starting_compound"),
            F.round(F.avg("s1_delta"), 3).alias("avg_s1_delta"),
            F.round(F.avg("s2_delta"), 3).alias("avg_s2_delta"),
            F.round(F.avg("s3_delta"), 3).alias("avg_s3_delta"),
        )
    )


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


def run_feature_pipeline(df: DataFrame) -> DataFrame:
    """Run the full feature engineering pipeline."""
    logger.info(f"📊 Input: {df.count()} lap records")

    # Step 1: Filter outliers
    df = filter_outlier_laps(df)
    logger.info(f"  ✅ After outlier filter: {df.count()} laps")

    # Step 2: Stint degradation
    df = compute_stint_degradation(df)
    logger.info("  ✅ Stint degradation features computed")

    # Step 3: Pace features
    df = compute_pace_features(df)
    logger.info("  ✅ Pace delta features computed")

    # Step 4: Consistency
    df = compute_consistency_features(df)
    logger.info("  ✅ Consistency features computed")

    # Step 5: Sector analysis
    df = compute_sector_features(df)
    logger.info("  ✅ Sector features computed")

    # Step 6: Teammate comparison
    df = compute_teammate_comparison(df)
    logger.info("  ✅ Lap rank computed")

    # Step 7: Aggregate to per-driver-per-race
    features = compute_aggregate_features(df)
    logger.info(f"  ✅ Aggregated to {features.count()} driver-race feature rows")

    return features


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="🏎️  PySpark Telemetry Feature Engineering"
    )
    parser.add_argument("--year", type=int, default=2024)
    parser.add_argument("--source", choices=["parquet", "bigquery", "fastf1"],
                        default="fastf1")
    parser.add_argument("--input-path", type=str, default="data/laps.parquet")
    parser.add_argument("--output-path", type=str, default="data/telemetry_features.parquet")
    parser.add_argument("--bq-table", type=str, default="f1_raw.lap_times")
    parser.add_argument("--master", type=str, default="local[*]",
                        help="Spark master URL")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    spark = create_spark_session(master=args.master)
    logger.info(f"🚀 Spark session created: {spark.sparkContext.master}")

    try:
        # Load data
        if args.source == "parquet":
            df = load_from_parquet(spark, args.input_path)
        elif args.source == "bigquery":
            import os
            project_id = os.getenv("GCP_PROJECT_ID", "")
            df = load_from_bigquery(spark, args.bq_table, project_id)
        else:
            df = load_sample_data(spark, args.year)

        # Run pipeline
        features = run_feature_pipeline(df)

        # Write output
        output_path = args.output_path
        features.coalesce(1).write.mode("overwrite").parquet(output_path)
        logger.info(f"💾 Features written to {output_path}")

        # Show sample
        features.show(10, truncate=False)

    finally:
        spark.stop()
        logger.info("🏁 Spark session stopped")


if __name__ == "__main__":
    main()
