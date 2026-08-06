"""One-time diagnostic/migration script. Not part of the regular pipeline."""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
from google.cloud import bigquery

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent))

def main():
    load_dotenv()
    project_id = os.getenv("GCP_PROJECT_ID")
    dataset = os.getenv("BQ_DATASET", "f1_raw")
    
    if not project_id:
        logger.error("❌ GCP_PROJECT_ID not set in .env")
        sys.exit(1)
        
    client = bigquery.Client(project=project_id)
    
    tables_to_migrate = ["race_results", "weather", "qualifying_results", "lap_times"]
    
    for table in tables_to_migrate:
        # Check if table exists
        table_id = f"{project_id}.{dataset}.{table}"
        try:
            client.get_table(table_id)
        except Exception:
            logger.info(f"Table {table_id} does not exist, skipping.")
            continue
            
        logger.info(f"🔄 Migrating {table_id} to add partitioning and clustering...")
        
        # BigQuery does not allow CREATE OR REPLACE TABLE to change partition specs directly.
        # We must use a temporary backup table, drop the original, and recreate it.
        temp_table_id = f"{table_id}_migration_backup"
        
        try:
            # 1. Create backup table
            logger.info(f"  - Creating backup {temp_table_id}")
            client.query(f"CREATE OR REPLACE TABLE `{temp_table_id}` AS SELECT * FROM `{table_id}`").result()
            
            # 2. Drop original table
            logger.info(f"  - Dropping original {table_id}")
            client.delete_table(table_id)
            
            # 3. Recreate original table with new partitioning from backup
            logger.info(f"  - Recreating {table_id} with partitioning and clustering")
            query = f"""
            CREATE TABLE `{table_id}`
            PARTITION BY RANGE_BUCKET(year, GENERATE_ARRAY(1950, 2100, 1))
            CLUSTER BY circuit_name
            AS SELECT * FROM `{temp_table_id}`
            """
            client.query(query).result()
            
            # 4. Clean up backup table
            logger.info(f"  - Cleaning up backup {temp_table_id}")
            client.delete_table(temp_table_id)
            
            logger.info(f"✅ Successfully migrated {table_id}")
        except Exception as e:
            logger.error(f"❌ Failed to migrate {table_id}: {e}")
            
    # Verification
    for table in tables_to_migrate:
        table_id = f"{project_id}.{dataset}.{table}"
        try:
            t = client.get_table(table_id)
            partitioning = t.range_partitioning
            clustering = t.clustering_fields
            logger.info(f"📊 Verification for {table_id}:")
            if partitioning:
                logger.info(f"  - Partitioning: {partitioning.field} (Range: {partitioning.range_.start} to {partitioning.range_.end})")
            else:
                logger.info(f"  - Partitioning: None")
                
            if clustering:
                logger.info(f"  - Clustering: {clustering}")
            else:
                logger.info(f"  - Clustering: None")
        except Exception:
            pass

if __name__ == "__main__":
    main()
