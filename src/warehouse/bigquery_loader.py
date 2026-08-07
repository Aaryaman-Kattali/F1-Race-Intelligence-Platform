"""
BigQuery data loader for the F1 Race Intelligence Platform.

Loads raw ingested data (race results, qualifying, lap times, weather) into
BigQuery tables.  Falls back to local SQLite for dev/offline use — but note
that the dbt transformation layer requires BigQuery and will NOT run against
SQLite.
"""

import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BQ_DATASET = os.getenv("BQ_DATASET", "f1_raw")


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


# ---------------------------------------------------------------------------
# BigQuery Loader
# ---------------------------------------------------------------------------


class BigQueryLoader:
    """
    Load raw F1 data into Google BigQuery (or local SQLite as fallback).

    Usage::

        loader = BigQueryLoader()
        loader.load_race_results([{...}, ...])
    """

    def __init__(self, project_id: Optional[str] = None, dataset: Optional[str] = None):
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID")
        self.dataset = dataset or _BQ_DATASET
        self._bq_client = None
        self._use_sqlite = False
        self._sqlite_path = Path(
            os.getenv("SQLITE_WAREHOUSE_PATH", "data/warehouse.db")
        )

        if self.project_id:
            try:
                from google.cloud import bigquery

                self._bq_client = bigquery.Client(project=self.project_id)
                self._ensure_dataset_exists()
                logger.info(
                    f"✅ BigQuery loader initialised (project={self.project_id}, dataset={self.dataset})"
                )
            except Exception as e:
                logger.warning(
                    f"⚠️  BigQuery unavailable ({e}), falling back to SQLite"
                )
                self._use_sqlite = True
        else:
            logger.info("📋 No GCP_PROJECT_ID — using local SQLite warehouse fallback")
            self._use_sqlite = True

        if self._use_sqlite:
            self._init_sqlite()

    # ------------------------------------------------------------------
    # BigQuery helpers
    # ------------------------------------------------------------------

    def _ensure_dataset_exists(self) -> None:
        from google.cloud import bigquery

        dataset_ref = bigquery.DatasetReference(self.project_id, self.dataset)
        try:
            self._bq_client.get_dataset(dataset_ref)
        except Exception:
            ds = bigquery.Dataset(dataset_ref)
            ds.location = "US"
            self._bq_client.create_dataset(ds)
            logger.info(f"📦 Created BigQuery dataset {self.dataset}")

    def _ensure_table_exists(self, table_name: str) -> None:
        from google.cloud import bigquery
        from src.warehouse.schema import TABLE_SCHEMAS

        table_id = f"{self.project_id}.{self.dataset}.{table_name}"
        try:
            self._bq_client.get_table(table_id)
        except Exception:
            schema = TABLE_SCHEMAS.get(table_name, [])
            table = bigquery.Table(table_id, schema=schema)

            # Apply partitioning and clustering to new tables
            if "year" in [field.name for field in schema]:
                table.range_partitioning = bigquery.RangePartitioning(
                    field="year",
                    range_=bigquery.PartitionRange(start=1950, end=2100, interval=1),
                )
            if "circuit_name" in [field.name for field in schema]:
                table.clustering_fields = ["circuit_name"]

            self._bq_client.create_table(table)
            logger.info(f"📦 Created BigQuery table {table_id}")

    def _sanitize_rows(self, rows: List[Dict], table_name: str) -> List[Dict]:
        """
        Fix pandas-induced type mismatches before BigQuery load.

        pandas upcasts integer columns containing NaN to float64, so a
        grid_position of 2 is serialized as 2.0 — which BigQuery's
        INTEGER schema rejects.  This method walks the schema and:
          - INTEGER fields: float → int, NaN/None → None
          - BOOLEAN fields: truthy → bool, NaN/None → None
          - FLOAT fields: NaN → None (to prevent invalid JSON 'NaN')
        """
        import math
        from src.warehouse.schema import TABLE_SCHEMAS

        schema = TABLE_SCHEMAS.get(table_name, [])
        if not schema:
            return rows

        # Build lookup: field_name → field_type
        int_fields = set()
        bool_fields = set()
        float_fields = set()
        for field in schema:
            if field.field_type == "INTEGER":
                int_fields.add(field.name)
            elif field.field_type in ("BOOLEAN", "BOOL"):
                bool_fields.add(field.name)
            elif field.field_type in ("FLOAT", "FLOAT64"):
                float_fields.add(field.name)

        if not int_fields and not bool_fields and not float_fields:
            return rows

        sanitized = []
        for row in rows:
            clean = dict(row)
            for col in int_fields:
                val = clean.get(col)
                if val is None:
                    continue
                try:
                    if isinstance(val, float):
                        if math.isnan(val) or math.isinf(val):
                            clean[col] = None
                        else:
                            clean[col] = int(val)
                    elif isinstance(val, int):
                        pass  # already fine
                    else:
                        clean[col] = int(val)
                except (ValueError, TypeError):
                    clean[col] = None

            for col in bool_fields:
                val = clean.get(col)
                if val is None:
                    continue
                try:
                    if isinstance(val, float) and math.isnan(val):
                        clean[col] = None
                    else:
                        clean[col] = bool(val)
                except (ValueError, TypeError):
                    clean[col] = None

            for col in float_fields:
                val = clean.get(col)
                if val is None:
                    continue
                if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                    clean[col] = None

            sanitized.append(clean)

        return sanitized

    def _insert_rows(self, table_name: str, rows: List[Dict]) -> int:
        """
        Load rows into BigQuery via a batch load job.

        Uses ``load_table_from_json`` instead of ``insert_rows_json``
        (streaming inserts) because streaming is not available on the
        BigQuery free tier (403 Access Denied).  Batch load jobs are
        free and sufficient for this workload.
        """
        from google.cloud import bigquery
        from src.warehouse.schema import TABLE_SCHEMAS

        self._ensure_table_exists(table_name)
        table_id = f"{self.project_id}.{self.dataset}.{table_name}"

        # Fix float→int for INTEGER columns (pandas NaN upcast issue)
        rows = self._sanitize_rows(rows, table_name)

        schema = TABLE_SCHEMAS.get(table_name, [])
        job_config = bigquery.LoadJobConfig(
            schema=schema,
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        )

        # Apply partitioning and clustering for query performance
        # Using integer range partitioning on 'year' since it's an INTEGER column
        if "year" in [field.name for field in schema]:
            job_config.range_partitioning = bigquery.RangePartitioning(
                field="year",
                range_=bigquery.PartitionRange(start=1950, end=2100, interval=1),
            )

        if "circuit_name" in [field.name for field in schema]:
            job_config.clustering_fields = ["circuit_name"]

        load_job = self._bq_client.load_table_from_json(
            rows, table_id, job_config=job_config
        )
        load_job.result()  # block until complete

        if load_job.errors:
            logger.error(
                f"❌ BigQuery load errors for {table_name}: {load_job.errors[:3]}"
            )
            return max(0, len(rows) - len(load_job.errors))

        logger.debug(
            f"📦 Batch load job completed for {table_name}: {load_job.output_rows} rows"
        )
        return load_job.output_rows or len(rows)

    # ------------------------------------------------------------------
    # SQLite helpers
    # ------------------------------------------------------------------

    def _init_sqlite(self) -> None:
        self._sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self._sqlite_path))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS race_results (
                year INTEGER, round INTEGER, circuit_name TEXT,
                driver_code TEXT, driver_name TEXT, team TEXT,
                grid_position INTEGER, finish_position INTEGER,
                points REAL, status TEXT, ingested_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS qualifying_results (
                year INTEGER, round INTEGER, circuit_name TEXT,
                driver_code TEXT, driver_name TEXT, team TEXT,
                position INTEGER, q1_time TEXT, q2_time TEXT,
                q3_time TEXT, ingested_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lap_times (
                year INTEGER, round INTEGER, circuit_name TEXT,
                session_type TEXT, driver_code TEXT, lap_number INTEGER,
                lap_time_seconds REAL, sector1_seconds REAL,
                sector2_seconds REAL, sector3_seconds REAL,
                compound TEXT, tyre_life INTEGER, stint INTEGER,
                position INTEGER, is_personal_best INTEGER,
                ingested_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weather (
                year INTEGER, round INTEGER, circuit_name TEXT,
                session_type TEXT, air_temp_avg REAL, track_temp_avg REAL,
                humidity_avg REAL, pressure_avg REAL, wind_speed_avg REAL,
                rainfall INTEGER, ingested_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS standings (
                season INTEGER, round INTEGER, driver_code TEXT,
                driver_name TEXT, team TEXT, position INTEGER,
                points REAL, ingested_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS live_lap_telemetry (
                year INTEGER, round INTEGER, circuit_name TEXT,
                driver_code TEXT, lap_number INTEGER,
                lap_time_seconds REAL, sector1_seconds REAL,
                sector2_seconds REAL, sector3_seconds REAL,
                compound TEXT, tyre_life INTEGER, position INTEGER,
                gap_to_leader REAL, published_at TEXT, ingested_at TEXT
            )
        """)
        conn.commit()
        conn.close()
        logger.info(f"📋 SQLite warehouse initialised at {self._sqlite_path}")

    def _insert_sqlite(self, table_name: str, rows: List[Dict]) -> int:
        if not rows:
            return 0
        conn = sqlite3.connect(str(self._sqlite_path))
        cursor = conn.cursor()
        columns = list(rows[0].keys())
        placeholders = ", ".join(["?"] * len(columns))
        col_names = ", ".join(columns)
        for row in rows:
            values = [row.get(c) for c in columns]
            cursor.execute(
                f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})",
                values,
            )
        conn.commit()
        conn.close()
        return len(rows)

    # ------------------------------------------------------------------
    # Public loading methods
    # ------------------------------------------------------------------

    def _delete_existing_records(self, table_name: str, rows: List[Dict]) -> None:
        """Make ingestion idempotent by deleting existing records for the incoming keys."""
        if not rows:
            return

        # Extract unique (year, round, circuit_name) combinations
        keys = set()
        for r in rows:
            if "year" in r and "round" in r and "circuit_name" in r:
                keys.add((r["year"], r["round"], r["circuit_name"]))

        if not keys:
            return

        if self._use_sqlite:
            conn = sqlite3.connect(str(self._sqlite_path))
            cursor = conn.cursor()
            for y, r, c in keys:
                cursor.execute(
                    f"DELETE FROM {table_name} WHERE year=? AND round=? AND circuit_name=?",
                    (y, r, c),
                )
            conn.commit()
            conn.close()
            logger.debug(
                f"🗑️ Cleaned existing SQLite records in {table_name} for {len(keys)} events"
            )
        else:
            self._ensure_table_exists(table_name)
            table_id = f"{self.project_id}.{self.dataset}.{table_name}"

            conditions = []
            for y, r, c in keys:
                c_esc = c.replace("'", "\\'")
                conditions.append(
                    f"(year = {y} AND round = {r} AND circuit_name = '{c_esc}')"
                )

            where_clause = " OR ".join(conditions)
            query = f"DELETE FROM `{table_id}` WHERE {where_clause}"

            try:
                job = self._bq_client.query(query)
                job.result()  # Wait for completion
                logger.debug(
                    f"🗑️ Cleaned existing BigQuery records in {table_name} for {len(keys)} events"
                )
            except Exception as e:
                logger.warning(
                    f"⚠️ Failed to delete existing records from {table_name} (might be empty/new): {e}"
                )

    def _load(self, table_name: str, rows: List[Dict]) -> int:
        """Route to BigQuery or SQLite."""
        if not rows:
            return 0

        # Clean existing records to prevent duplicates
        self._delete_existing_records(table_name, rows)

        # Stamp ingestion time
        for row in rows:
            row.setdefault("ingested_at", _now_iso())

        if self._use_sqlite:
            count = self._insert_sqlite(table_name, rows)
        else:
            count = self._insert_rows(table_name, rows)

        logger.info(f"✅ Loaded {count}/{len(rows)} rows into {table_name}")
        return count

    def load_race_results(self, rows: List[Dict]) -> int:
        return self._load("race_results", rows)

    def load_qualifying_results(self, rows: List[Dict]) -> int:
        return self._load("qualifying_results", rows)

    def load_lap_times(self, rows: List[Dict]) -> int:
        return self._load("lap_times", rows)

    def load_weather_data(self, rows: List[Dict]) -> int:
        return self._load("weather", rows)

    def load_standings(self, rows: List[Dict]) -> int:
        return self._load("standings", rows)

    def load_live_telemetry(self, rows: List[Dict]) -> int:
        return self._load("live_lap_telemetry", rows)
