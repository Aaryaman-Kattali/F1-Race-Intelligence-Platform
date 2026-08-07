"""One-time diagnostic/migration script. Not part of the regular pipeline."""

"""
One-off script to de-duplicate existing tables in BigQuery.
Uses ROW_NUMBER() OVER (PARTITION BY ... ORDER BY ingested_at DESC)
to keep only the most recent row for each unique event/record.
"""
import os
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add src to path so we can import the schema/settings
sys.path.insert(0, str(Path(__file__).parent.parent))

from google.cloud import bigquery
from dotenv import load_dotenv


def main():
    load_dotenv()

    project_id = os.getenv("GCP_PROJECT_ID")
    dataset = os.getenv("BQ_DATASET", "f1_raw")

    if not project_id:
        logger.error("❌ GCP_PROJECT_ID not set in .env")
        sys.exit(1)

    client = bigquery.Client(project=project_id)

    # 1. De-duplicate race_results
    race_results_query = f"""
    CREATE OR REPLACE TABLE `{project_id}.{dataset}.race_results` AS
    SELECT * EXCEPT(rn)
    FROM (
        SELECT *,
               ROW_NUMBER() OVER(
                   PARTITION BY year, round, circuit_name, driver_code 
                   ORDER BY ingested_at DESC
               ) as rn
        FROM `{project_id}.{dataset}.race_results`
    )
    WHERE rn = 1
    """

    # 2. De-duplicate weather
    weather_query = f"""
    CREATE OR REPLACE TABLE `{project_id}.{dataset}.weather` AS
    SELECT * EXCEPT(rn)
    FROM (
        SELECT *,
               ROW_NUMBER() OVER(
                   PARTITION BY year, round, circuit_name, session_type 
                   ORDER BY ingested_at DESC
               ) as rn
        FROM `{project_id}.{dataset}.weather`
    )
    WHERE rn = 1
    """

    queries = {"race_results": race_results_query, "weather": weather_query}

    for table, query in queries.items():
        logger.info(f"🧹 Running de-duplication for {table}...")
        try:
            job = client.query(query)
            job.result()  # Wait for job to complete
            logger.info(f"✅ Successfully de-duplicated {table}")
        except Exception as e:
            logger.error(f"❌ Failed to de-duplicate {table}: {e}")


if __name__ == "__main__":
    main()
