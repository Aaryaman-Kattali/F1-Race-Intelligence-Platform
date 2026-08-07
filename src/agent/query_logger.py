"""
Agent query logger for LLMOps observability.

Logs every agent interaction to BigQuery (monitoring.agent_query_log) or
local SQLite for offline use. Queryable history for debugging and auditing.
"""

import logging
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class QueryLogger:
    """Log agent queries and responses for observability."""

    def __init__(self):
        self.project_id = os.getenv("GCP_PROJECT_ID", "")
        self._bq_client = None
        self._use_sqlite = False
        self._sqlite_path = Path(
            os.getenv("SQLITE_WAREHOUSE_PATH", "data/warehouse.db")
        )
        self._table_id = ""

        if self.project_id:
            try:
                from google.cloud import bigquery

                self._bq_client = bigquery.Client(project=self.project_id)
                self._table_id = f"{self.project_id}.monitoring.agent_query_log"
                self._ensure_table()
            except Exception as e:
                logger.warning(f"⚠️  BigQuery logging unavailable: {e}")
                self._use_sqlite = True
        else:
            self._use_sqlite = True

        if self._use_sqlite:
            self._init_sqlite()

    def _ensure_table(self):
        """Create monitoring dataset and table if needed."""
        from google.cloud import bigquery

        dataset_ref = bigquery.DatasetReference(self.project_id, "monitoring")
        try:
            self._bq_client.get_dataset(dataset_ref)
        except Exception:
            ds = bigquery.Dataset(dataset_ref)
            ds.location = "US"
            self._bq_client.create_dataset(ds)

        try:
            self._bq_client.get_table(self._table_id)
        except Exception:
            schema = [
                bigquery.SchemaField("timestamp", "TIMESTAMP"),
                bigquery.SchemaField("question", "STRING"),
                bigquery.SchemaField("generated_sql", "STRING"),
                bigquery.SchemaField("response", "STRING"),
                bigquery.SchemaField("success", "BOOLEAN"),
                bigquery.SchemaField("error", "STRING"),
                bigquery.SchemaField("latency_ms", "FLOAT"),
                bigquery.SchemaField("model_used", "STRING"),
                bigquery.SchemaField("estimated_bytes", "INTEGER"),
            ]
            table = bigquery.Table(self._table_id, schema=schema)
            self._bq_client.create_table(table)
            logger.info(f"📦 Created query log table: {self._table_id}")

    def _init_sqlite(self):
        """Create local log table."""
        self._sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self._sqlite_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_query_log (
                timestamp TEXT,
                question TEXT,
                generated_sql TEXT,
                response TEXT,
                success INTEGER,
                error TEXT,
                latency_ms REAL,
                model_used TEXT,
                estimated_bytes INTEGER
            )
        """)
        conn.commit()
        conn.close()

    def log(
        self,
        question: str,
        generated_sql: str = "",
        response: str = "",
        success: bool = True,
        error: Optional[str] = None,
        latency_ms: float = 0.0,
        model_used: Optional[str] = None,
        estimated_bytes: int = 0,
    ) -> None:
        """Log a query interaction."""
        if model_used is None:
            model_used = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
        row = {
            "timestamp": datetime.utcnow().isoformat(),
            "question": question,
            "generated_sql": generated_sql,
            "response": (
                str(response)[:2000] if response else ""
            ),  # Force string and truncate
            "success": success,
            "error": str(error) if error else "",
            "latency_ms": latency_ms,
            "model_used": model_used,
            "estimated_bytes": estimated_bytes,
        }

        try:
            if self._use_sqlite:
                self._log_to_sqlite(row)
            else:
                try:
                    self._bq_client.insert_rows_json(self._table_id, [row])
                except Exception as e:
                    logger.warning(
                        f"⚠️  BigQuery log failed (likely free tier constraint): {e}. Falling back to SQLite."
                    )
                    self._use_sqlite = True
                    self._init_sqlite()
                    self._log_to_sqlite(row)

            logger.debug(f"📝 Logged query: {question[:50]}...")
        except Exception as e:
            logger.warning(f"⚠️  Failed to log query: {e}")

    def _log_to_sqlite(self, row: dict):
        """Helper to log to SQLite."""
        conn = sqlite3.connect(str(self._sqlite_path))
        conn.execute(
            "INSERT INTO agent_query_log VALUES (?,?,?,?,?,?,?,?,?)",
            (
                row["timestamp"],
                row["question"],
                row["generated_sql"],
                row["response"],
                int(row["success"]),
                row["error"],
                row["latency_ms"],
                row["model_used"],
                row["estimated_bytes"],
            ),
        )
        conn.commit()
        conn.close()
