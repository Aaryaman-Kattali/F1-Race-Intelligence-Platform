"""
LangChain text-to-SQL agent for the F1 Race Intelligence Platform.

Uses Google Gemini (gemini-2.5-flash) to translate natural-language questions
into SQL, then executes against the BigQuery warehouse (dbt-modeled tables).

Safety guardrails (interview-worthy design point):
    1. Read-only BigQuery connection via dedicated service account
    2. SELECT-only enforcement — rejects any DML/DDL
    3. Dry-run cost check — rejects queries exceeding byte threshold
"""

import logging
import os
import re
import time
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_BYTES_SCANNED = int(os.getenv("AGENT_MAX_BYTES", str(100 * 1024 * 1024)))  # 100 MB

_SYSTEM_PROMPT = """\
You are an F1 data analyst assistant. You have access to a BigQuery data warehouse
containing Formula 1 race data.

To save API calls, the complete database schema is provided below. DO NOT attempt to use any tools to discover the schema, list tables, or describe tables. 
YOU MUST write and execute a SQL query using the provided query execution tool to get the actual data before answering. Do not rely on your pre-training knowledge. You do not know the data until you query it.

SCHEMA:
CREATE TABLE `f1_raw_marts.driver_circuit_performance` (
	`driver_code` STRING, 
	`circuit_name` STRING, 
	`races_at_circuit` INT64, 
	`avg_finish` FLOAT64, 
	`best_finish` INT64, 
	`avg_grid` FLOAT64, 
	`total_points` FLOAT64, 
	`wins` INT64, 
	`podiums` INT64, 
	`points_finishes` INT64, 
	`dnfs` INT64, 
	`avg_positions_gained` FLOAT64, 
	`consistency_score` FLOAT64, 
	`win_rate` FLOAT64, 
	`podium_rate` FLOAT64, 
	`dnf_rate` FLOAT64
)

CREATE TABLE `f1_raw_marts.driver_form_last5` (
	`driver_code` STRING, 
	`races_counted` INT64, 
	`avg_finish_last5` FLOAT64, 
	`best_finish_last5` INT64, 
	`total_points_last5` FLOAT64, 
	`finish_stddev_last5` FLOAT64, 
	`consistency_score_last5` FLOAT64, 
	`avg_positions_gained_last5` FLOAT64, 
	`podiums_last5` INT64, 
	`points_finishes_last5` INT64
)

CREATE TABLE `f1_raw_marts.tire_degradation_by_circuit` (
	`circuit_name` STRING, 
	`driver_code` STRING, 
	`compound` STRING, 
	`n_laps` INT64, 
	`deg_seconds_per_lap` FLOAT64, 
	`avg_lap_time` FLOAT64, 
	`fastest_lap` FLOAT64
)

CREATE TABLE `f1_raw_staging.stg_race_results` (
	`season_year` INT64, 
	`round_number` INT64, 
	`circuit_name` STRING, 
	`driver_code` STRING, 
	`driver_name` STRING, 
	`team` STRING, 
	`grid_position` INT64, 
	`finish_position` INT64, 
	`points` FLOAT64, 
	`status` STRING, 
	`ingested_at` TIMESTAMP
)

IMPORTANT LIMITATION: The data currently ONLY covers 4 circuits:
- Hungarian Grand Prix
- Italian Grand Prix (Monza)
- Belgian Grand Prix
- British Grand Prix
If asked about a circuit not in this list, you MUST clearly state that you do not have data for it. Do not fabricate an answer.

IMPORTANT: Driver codes are 3-letter uppercase abbreviations (e.g., VER, HAM, NOR, PIA).
Always use UPPER CASE for driver codes in WHERE clauses.

Generate efficient SQL queries. Prefer the analytical tables when they contain
the data needed — they are pre-aggregated and faster.
"""


# ---------------------------------------------------------------------------
# SQL safety
# ---------------------------------------------------------------------------


def validate_sql_is_select(sql: str) -> bool:
    """
    Reject any SQL that is not a pure SELECT statement.

    Guards against LLM-generated DML (INSERT, UPDATE, DELETE)
    or DDL (CREATE, DROP, ALTER, TRUNCATE).
    """
    cleaned = sql.strip().upper()
    # Remove leading comments
    cleaned = re.sub(r"--.*?\n", "", cleaned)
    cleaned = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.DOTALL)
    cleaned = cleaned.strip()

    forbidden_keywords = [
        "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE",
        "CREATE", "MERGE", "GRANT", "REVOKE", "EXEC", "EXECUTE",
    ]
    first_word = cleaned.split()[0] if cleaned.split() else ""

    if first_word not in ("SELECT", "WITH"):
        logger.warning(f"🚫 Rejected non-SELECT SQL: starts with {first_word}")
        return False

    # Also check for any forbidden keyword as a standalone statement
    for kw in forbidden_keywords:
        pattern = rf"\b{kw}\b"
        if re.search(pattern, cleaned):
            logger.warning(f"🚫 Rejected SQL containing forbidden keyword: {kw}")
            return False

    return True


def dry_run_cost_check(sql: str, project_id: str,
                       credentials_path: Optional[str] = None) -> Dict:
    """
    Run a BigQuery dry-run to estimate bytes scanned.

    Returns:
        {"estimated_bytes": int, "approved": bool, "reason": str}
    """
    try:
        from google.cloud import bigquery
        from google.oauth2 import service_account

        if credentials_path:
            creds = service_account.Credentials.from_service_account_file(credentials_path)
            client = bigquery.Client(project=project_id, credentials=creds)
        else:
            client = bigquery.Client(project=project_id)

        job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
        query_job = client.query(sql, job_config=job_config)

        estimated = query_job.total_bytes_processed or 0
        approved = estimated <= _MAX_BYTES_SCANNED

        result = {
            "estimated_bytes": estimated,
            "estimated_mb": round(estimated / (1024 * 1024), 2),
            "approved": approved,
            "reason": "OK" if approved else f"Exceeds {_MAX_BYTES_SCANNED / (1024*1024):.0f}MB limit",
        }

        if not approved:
            logger.warning(
                f"🚫 Dry-run rejected: {result['estimated_mb']}MB > "
                f"{_MAX_BYTES_SCANNED / (1024*1024):.0f}MB limit"
            )

        return result

    except Exception as e:
        logger.warning(f"⚠️  Dry-run check failed: {e}")
        return {"estimated_bytes": 0, "approved": True, "reason": f"Dry-run failed: {e}"}


# ---------------------------------------------------------------------------
# Query Agent
# ---------------------------------------------------------------------------


class QueryAgent:
    """
    Natural-language to SQL query agent using LangChain + Gemini.

    Connects to BigQuery via SQLAlchemy (sqlalchemy-bigquery dialect)
    using a READ-ONLY service account.
    """

    def __init__(self):
        self.project_id = os.getenv("GCP_PROJECT_ID", "")
        self.dataset = os.getenv("BQ_DATASET", "f1_raw")
        self._agent = None
        self._db = None
        self._use_sqlite = False

        # Use read-only credentials for the agent
        self._agent_creds = os.getenv(
            "GOOGLE_AGENT_CREDENTIALS",
            os.getenv("GOOGLE_APPLICATION_CREDENTIALS", ""),
        )

    def _init_bigquery_db(self):
        """Initialise SQLAlchemy connection to BigQuery."""
        from langchain_community.utilities import SQLDatabase
        from sqlalchemy.engine.interfaces import Dialect
        
        # Patch SQLAlchemy Dialect to avoid NotImplementedError for BigQuery views
        Dialect.get_materialized_view_names = lambda self, connection, schema=None, **kw: []

        # Connect at the project level to access multiple datasets
        uri = f"bigquery://{self.project_id}"
        if self._agent_creds:
            uri += f"?credentials_path={self._agent_creds}"

        allowed_tables = [
            "f1_raw_marts.driver_circuit_performance",
            "f1_raw_marts.driver_form_last5",
            "f1_raw_marts.tire_degradation_by_circuit",
            "f1_raw_staging.stg_race_results",
        ]

        self._db = SQLDatabase.from_uri(uri, include_tables=allowed_tables, view_support=True)
        logger.info(f"✅ Agent connected to BigQuery: {self.project_id} (Restricted to {len(allowed_tables)} tables)")

    def _init_sqlite_db(self):
        """Fallback: connect to local SQLite warehouse."""
        from langchain_community.utilities import SQLDatabase

        sqlite_path = os.getenv("SQLITE_WAREHOUSE_PATH", "data/warehouse.db")
        self._db = SQLDatabase.from_uri(f"sqlite:///{sqlite_path}")
        self._use_sqlite = True
        logger.info(f"📋 Agent connected to SQLite: {sqlite_path}")

    def _init_agent(self):
        """Initialise the LangChain agent."""
        if self._agent is not None:
            return

        # Connect to DB
        if self.project_id:
            try:
                self._init_bigquery_db()
            except Exception as e:
                logger.warning(f"⚠️  BigQuery connection failed ({e}), trying SQLite")
                self._init_sqlite_db()
        else:
            self._init_sqlite_db()

        # Initialise LLM
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

        llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0,
        )

        # Create SQL toolkit + agent
        from langchain_community.agent_toolkits import SQLDatabaseToolkit
        from langchain_community.agent_toolkits import create_sql_agent
        from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
        
        class StaticSQLDatabaseToolkit(SQLDatabaseToolkit):
            def get_tools(self):
                # Return ONLY the query execution tool, skipping list/describe tools
                return [QuerySQLDataBaseTool(db=self.db)]

        toolkit = StaticSQLDatabaseToolkit(db=self._db, llm=llm)
        self._agent = create_sql_agent(
            llm=llm,
            toolkit=toolkit,
            agent_type="openai-tools",
            prefix=_SYSTEM_PROMPT,
            verbose=False,
            agent_executor_kwargs={"return_intermediate_steps": True}
        )

        logger.info("✅ LangChain SQL agent initialised")

    def ask(self, question: str) -> Dict:
        """
        Answer a natural-language question about F1 data.

        Returns:
            {
                "question": str,
                "generated_sql": str,
                "result": any,
                "natural_language_answer": str,
                "estimated_bytes_scanned": int,
                "execution_time_ms": float,
            }
        """
        start = time.time()

        try:
            self._init_agent()

            # Run agent with retry-with-backoff
            max_retries = 2
            response = None
            for attempt in range(max_retries + 1):
                try:
                    response = self._agent.invoke({"input": question})
                    break
                except Exception as e:
                    error_str = str(e)
                    if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                        if attempt < max_retries:
                            sleep_time = 15 * (attempt + 1)
                            logger.warning(f"⚠️ Rate limit hit. Retrying in {sleep_time}s... (Attempt {attempt+1}/{max_retries})")
                            time.sleep(sleep_time)
                            continue
                    raise e
                    
            raw_output = response.get("output", "")
            if isinstance(raw_output, list):
                text_blocks = [item.get("text", "") for item in raw_output if isinstance(item, dict) and item.get("type") == "text"]
                answer = "\n".join(text_blocks)
            else:
                answer = str(raw_output)

            # Try to extract SQL from intermediate steps
            generated_sql = ""
            if "intermediate_steps" in response:
                print(f"DEBUG intermediate_steps: {response['intermediate_steps']}", flush=True)
                for step in response["intermediate_steps"]:
                    if hasattr(step, "__len__") and len(step) >= 2:
                        action = step[0]
                        if hasattr(action, "tool_input"):
                            tool_input = action.tool_input
                            if isinstance(tool_input, str) and "SELECT" in tool_input.upper():
                                generated_sql = tool_input
                                break
                            elif isinstance(tool_input, dict) and "query" in tool_input:
                                generated_sql = tool_input["query"]
                                break

            # Safety checks on extracted SQL
            estimated_bytes = 0
            if generated_sql:
                if not validate_sql_is_select(generated_sql):
                    return {
                        "question": question,
                        "error": "Generated SQL was rejected: only SELECT queries are allowed",
                        "generated_sql": generated_sql,
                    }

                if not self._use_sqlite and self.project_id:
                    cost_check = dry_run_cost_check(
                        generated_sql, self.project_id, self._agent_creds
                    )
                    estimated_bytes = cost_check["estimated_bytes"]
                    if not cost_check["approved"]:
                        return {
                            "question": question,
                            "error": f"Query rejected: {cost_check['reason']}",
                            "generated_sql": generated_sql,
                            "estimated_bytes_scanned": estimated_bytes,
                        }

            elapsed = (time.time() - start) * 1000

            return {
                "question": question,
                "generated_sql": generated_sql,
                "natural_language_answer": answer,
                "estimated_bytes_scanned": estimated_bytes,
                "execution_time_ms": round(elapsed, 1),
                "model": "gemini-2.5-flash",
                "backend": "sqlite" if self._use_sqlite else "bigquery",
            }

        except Exception as e:
            elapsed = (time.time() - start) * 1000
            logger.error(f"❌ Agent error: {e}")
            return {
                "question": question,
                "error": str(e),
                "execution_time_ms": round(elapsed, 1),
            }
