"""
F1 Race Intelligence Platform — FastAPI Application.

Endpoints:
    GET  /              — API status
    POST /api/predict   — Race winner prediction (rule-based + XGBoost hybrid)
    GET  /api/circuits  — List available circuits
    GET  /api/health    — Health check
    POST /api/ask       — Natural-language query agent (LangChain + Gemini)
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import sys
from pathlib import Path
import logging

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.predictor.gp_predictor import GPPredictor

logger = logging.getLogger(__name__)

app = FastAPI(
    title="F1 Race Intelligence Platform",
    description="Data engineering + agentic AI platform for F1 race prediction and analysis",
    version="2.0.0",
)

# CORS middleware (replaces Flask-CORS)
import os
import time

from dotenv import load_dotenv

load_dotenv(project_root / ".env")

frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
allowed_origins = [origin.strip() for origin in frontend_origin.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize predictor
predictor = GPPredictor()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class PredictRequest(BaseModel):
    gp_name: str = Field(
        ..., description="Grand Prix name, e.g. 'Hungarian Grand Prix'"
    )


class AskRequest(BaseModel):
    question: str = Field(..., description="Natural-language question about F1 data")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/")
async def home():
    return {"message": "F1 Race Intelligence Platform is running!"}


@app.post("/api/predict")
async def predict_race(request: PredictRequest):
    """Generate race winner prediction using the rule-based/XGBoost hybrid engine."""
    try:
        logger.info(f"🏁 API: Predicting for {request.gp_name}")
        prediction = predictor.predict_race_winner(request.gp_name)

        if "error" in prediction:
            raise HTTPException(status_code=400, detail=prediction["error"])

        return {"success": True, "data": prediction}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/circuits")
async def get_circuits():
    """List all available F1 circuits."""
    circuits = predictor.circuit_mapper.list_available_circuits()
    return circuits


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "message": "F1 Race Intelligence Platform is running",
        "circuits_loaded": len(predictor.circuits),
        "active_drivers": len(predictor.active_drivers_2025),
    }


stats_cache = {}
circuit_perf_cache = {}
driver_perf_cache = {}
tire_deg_cache = {}
stint_sample_cache = {}
race_replay_cache = {}
CACHE_TTL = 300  # 5 minutes

# A replayable race needs more than a handful of laps. The 2021 Belgian GP is
# in the warehouse with a single lap (it was abandoned behind the safety car),
# so "most recent season" alone would pick a race with nothing to replay.
MIN_REPLAY_LAPS = 20

# Stints shorter than this produce meaningless regression slopes — a 2-lap
# sample at Monza yields -5.075 s/lap, which is noise, not degradation.
MIN_STINT_LAPS = 8

DEGRADATION_CAVEAT = (
    "Degradation here is a linear regression of lap time vs. tyre life within "
    "a stint. It does not correct for fuel load, so durable compounds "
    "(HARD/MEDIUM) can show apparent negative degradation because fuel "
    "burn-off's speed gain outweighs their small wear effect — SOFT reflects "
    "true wear most reliably, though even it can invert at low-degradation, "
    "high-fuel-effect circuits."
)

# Legacy, unnormalized circuit_name values that predate the naming convention.
# Stopgap in the API layer because the BigQuery free tier blocks the DML we'd
# need to delete the old rows. The real fix is normalizing in dbt staging.
#
# Note these are NOT extra data to merge in: 'hungarian' is a byte-identical
# duplicate of 'Hungarian Grand Prix', and 'monza' is a stale partial snapshot
# (20 rows, 19 of them disagreeing with the 32 rows under 'Italian Grand Prix').
# So every query filters to the canonical name only — unioning the aliases in
# would yield duplicate drivers carrying conflicting stats.
CIRCUIT_NAME_ALIASES = {
    "hungarian": "Hungarian Grand Prix",
    "monza": "Italian Grand Prix",
}


def normalize_circuit_name(name: str) -> str:
    return CIRCUIT_NAME_ALIASES.get(name.lower(), name)


def _readonly_bq_client():
    """BigQuery client using the read-only agent service account.

    Falls back to the writer creds only if the read-only one isn't configured,
    and to ADC if neither is. Read-only endpoints share this.
    """
    from google.cloud import bigquery
    from google.oauth2 import service_account

    project_id = os.getenv("GCP_PROJECT_ID") or None
    agent_creds_path = os.getenv("GOOGLE_AGENT_CREDENTIALS", "")

    if agent_creds_path:
        creds_file = Path(agent_creds_path)
        if not creds_file.is_absolute():
            creds_file = project_root / creds_file
        # Only use the key file if it is actually present. On Cloud Run there
        # is no key file — credentials come from the attached runtime service
        # account via ADC — and a stale env var pointing at a missing path
        # must not take the whole endpoint down.
        if creds_file.is_file():
            creds = service_account.Credentials.from_service_account_file(
                str(creds_file)
            )
            return bigquery.Client(project=project_id, credentials=creds)
        logger.info(
            f"GOOGLE_AGENT_CREDENTIALS points at {creds_file} which does not "
            "exist — falling back to Application Default Credentials."
        )
    return bigquery.Client(project=project_id)

@app.get("/api/stats")
async def get_stats():
    """Lightweight stats endpoint for frontend dashboard."""
    now = time.time()
    if "data" in stats_cache and (now - stats_cache["timestamp"]) < CACHE_TTL:
        return stats_cache["data"]

    fallback_data = {
        "circuits_ingested": 4,
        "circuit_names": ["Hungarian Grand Prix", "Italian Grand Prix", "Belgian Grand Prix", "British Grand Prix"],
        "season_range": "2018-2024",
        # Last confirmed-real numbers, legacy alias rows excluded.
        "total_race_entries": 540,
        "total_laps_processed": 26367,
        "agent_model": os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite"),
        "live": False
    }

    try:
        if os.getenv("OFFLINE_MODE", "").lower() == "true":
            raise Exception("Offline mode is enabled")

        from google.cloud import bigquery

        client = _readonly_bq_client()

        query_circuits = "SELECT DISTINCT circuit_name FROM f1_raw_marts.driver_circuit_performance WHERE circuit_name IS NOT NULL"
        circuits_result = list(client.query(query_circuits).result())

        # Normalize legacy aliases, then dedupe — 'hungarian'/'monza' collapse
        # into their canonical names so this reports 4 circuits, not 6.
        circuit_names = sorted(
            {normalize_circuit_name(row.circuit_name) for row in circuits_result}
        )

        # The legacy alias rows are duplicates of data that already exists under
        # the canonical name, so counting both double-counts. Verified: every
        # 'hungarian' row is an exact duplicate of a 'Hungarian Grand Prix' row
        # in both staging tables, and all 20 'monza' rows already appear under
        # 'Italian Grand Prix'. Excluding them loses nothing.
        legacy_names = sorted(CIRCUIT_NAME_ALIASES.keys())
        exclude_legacy = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ArrayQueryParameter("legacy", "STRING", legacy_names)
            ]
        )

        query_seasons = """
            SELECT MIN(season_year) as min_y, MAX(season_year) as max_y
            FROM f1_raw_staging.stg_race_results
            WHERE LOWER(circuit_name) NOT IN UNNEST(@legacy)
        """
        seasons_result = list(client.query(query_seasons, job_config=exclude_legacy).result())[0]
        season_range = f"{seasons_result.min_y}-{seasons_result.max_y}"

        query_entries = """
            SELECT COUNT(*) as cnt FROM f1_raw_staging.stg_race_results
            WHERE LOWER(circuit_name) NOT IN UNNEST(@legacy)
        """
        entries = list(client.query(query_entries, job_config=exclude_legacy).result())[0].cnt

        query_laps = """
            SELECT COUNT(*) as cnt FROM f1_raw_staging.stg_lap_times
            WHERE LOWER(circuit_name) NOT IN UNNEST(@legacy)
        """
        laps = list(client.query(query_laps, job_config=exclude_legacy).result())[0].cnt

        data = {
            "circuits_ingested": len(circuit_names),
            "circuit_names": circuit_names,
            "season_range": season_range,
            "total_race_entries": entries,
            "total_laps_processed": laps,
            "agent_model": os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite"),
            "live": True
        }
        
        stats_cache["data"] = data
        stats_cache["timestamp"] = now
        return data

    except Exception as e:
        logger.warning(f"Failed to fetch live stats from BigQuery, returning fallback: {e}")
        return fallback_data


@app.get("/api/circuit-performance")
async def circuit_performance(circuit: str):
    """Top 5 drivers by average finishing position at a given circuit.

    Accepts either the canonical circuit name or a legacy alias. A circuit
    with no ingested data is not an error — it returns 200 with an empty
    driver list and live=False, so the frontend can render an empty state.
    """
    canonical = normalize_circuit_name(circuit)
    now = time.time()

    cached = circuit_perf_cache.get(canonical)
    if cached and (now - cached["timestamp"]) < CACHE_TTL:
        return cached["data"]

    empty = {"circuit_name": canonical, "drivers": [], "live": False}

    try:
        if os.getenv("OFFLINE_MODE", "").lower() == "true":
            raise RuntimeError("Offline mode is enabled")

        from google.cloud import bigquery

        client = _readonly_bq_client()

        # Filter to the canonical name only. The legacy alias rows are either
        # exact duplicates or a stale partial snapshot, so including them would
        # return the same driver twice with conflicting numbers.
        query = """
            SELECT driver_code, races_at_circuit, avg_finish, wins, podiums
            FROM f1_raw_marts.driver_circuit_performance
            WHERE circuit_name = @circuit
            ORDER BY avg_finish ASC
            LIMIT 5
        """
        job = client.query(
            query,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("circuit", "STRING", canonical)
                ]
            ),
        )

        drivers = [
            {
                "driver_code": row.driver_code,
                "races_at_circuit": row.races_at_circuit,
                "avg_finish": row.avg_finish,
                "wins": row.wins,
                "podiums": row.podiums,
            }
            for row in job.result()
        ]

        if not drivers:
            # Circuit simply isn't ingested yet — a valid empty state, not live data.
            return empty

        data = {"circuit_name": canonical, "drivers": drivers, "live": True}
        circuit_perf_cache[canonical] = {"data": data, "timestamp": now}
        return data

    except Exception as e:
        logger.warning(
            f"Failed to fetch circuit performance for {canonical!r}, "
            f"returning empty result: {e}"
        )
        return empty


@app.get("/api/driver-performance")
async def driver_performance(driver: str):
    """A driver's record across every ingested circuit, plus career totals.

    A driver with no rows is not an error — it returns 200 with an empty
    circuit list, zeroed totals and live=False, so the frontend can render
    an honest empty state.
    """
    driver_code = driver.upper()
    now = time.time()

    cached = driver_perf_cache.get(driver_code)
    if cached and (now - cached["timestamp"]) < CACHE_TTL:
        return cached["data"]

    empty = {
        "driver_code": driver_code,
        "circuits": [],
        "totals": {"total_races": 0, "total_wins": 0, "total_podiums": 0},
        "live": False,
    }

    try:
        if os.getenv("OFFLINE_MODE", "").lower() == "true":
            raise RuntimeError("Offline mode is enabled")

        from google.cloud import bigquery

        client = _readonly_bq_client()

        # Exclude legacy alias rows for the same reason /api/circuit-performance
        # does: they'd add a duplicate circuit entry carrying stale numbers.
        query = """
            SELECT circuit_name, races_at_circuit, avg_finish, wins, podiums
            FROM f1_raw_marts.driver_circuit_performance
            WHERE driver_code = @driver
              AND LOWER(circuit_name) NOT IN UNNEST(@legacy)
            ORDER BY circuit_name
        """
        job = client.query(
            query,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("driver", "STRING", driver_code),
                    bigquery.ArrayQueryParameter(
                        "legacy", "STRING", sorted(CIRCUIT_NAME_ALIASES.keys())
                    ),
                ]
            ),
        )

        circuits = [
            {
                "circuit_name": row.circuit_name,
                "races_at_circuit": row.races_at_circuit,
                "avg_finish": row.avg_finish,
                "wins": row.wins,
                "podiums": row.podiums,
            }
            for row in job.result()
        ]

        if not circuits:
            return empty

        totals = {
            "total_races": sum(c["races_at_circuit"] for c in circuits),
            "total_wins": sum(c["wins"] for c in circuits),
            "total_podiums": sum(c["podiums"] for c in circuits),
        }

        data = {
            "driver_code": driver_code,
            "circuits": circuits,
            "totals": totals,
            "live": True,
        }
        driver_perf_cache[driver_code] = {"data": data, "timestamp": now}
        return data

    except Exception as e:
        logger.warning(
            f"Failed to fetch driver performance for {driver_code!r}, "
            f"returning empty result: {e}"
        )
        return empty


@app.get("/api/tire-degradation")
async def tire_degradation(circuit: str):
    """Average tyre degradation per compound at a circuit.

    Only stints of at least MIN_STINT_LAPS laps are included — shorter
    samples produce regression slopes that are noise rather than signal.
    Compounds with no qualifying rows are omitted entirely.
    """
    canonical = normalize_circuit_name(circuit)
    now = time.time()

    cached = tire_deg_cache.get(canonical)
    if cached and (now - cached["timestamp"]) < CACHE_TTL:
        return cached["data"]

    empty = {
        "circuit_name": canonical,
        "compounds": [],
        "caveat": DEGRADATION_CAVEAT,
        "live": False,
    }

    try:
        if os.getenv("OFFLINE_MODE", "").lower() == "true":
            raise RuntimeError("Offline mode is enabled")

        from google.cloud import bigquery

        client = _readonly_bq_client()

        # Canonical name only — the marts table carries 'hungarian' duplicates
        # that would otherwise double-weight the Hungaroring averages.
        query = """
            SELECT
              compound,
              AVG(deg_seconds_per_lap) AS avg_degradation_per_lap,
              COUNT(DISTINCT driver_code) AS driver_count,
              AVG(n_laps) AS avg_stint_length
            FROM f1_raw_marts.tire_degradation_by_circuit
            WHERE circuit_name = @circuit
              AND n_laps >= @min_laps
            GROUP BY compound
            ORDER BY compound
        """
        job = client.query(
            query,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("circuit", "STRING", canonical),
                    bigquery.ScalarQueryParameter("min_laps", "INT64", MIN_STINT_LAPS),
                ]
            ),
        )

        compounds = [
            {
                "compound": row.compound,
                "avg_degradation_per_lap": round(row.avg_degradation_per_lap, 4),
                "driver_count": row.driver_count,
                "avg_stint_length": round(row.avg_stint_length, 1),
            }
            for row in job.result()
        ]

        if not compounds:
            return empty

        data = {
            "circuit_name": canonical,
            "compounds": compounds,
            "caveat": DEGRADATION_CAVEAT,
            "live": True,
        }
        tire_deg_cache[canonical] = {"data": data, "timestamp": now}
        return data

    except Exception as e:
        logger.warning(
            f"Failed to fetch tire degradation for {canonical!r}, "
            f"returning empty result: {e}"
        )
        return empty


@app.get("/api/stint-sample")
async def stint_sample(circuit: str, compound: str):
    """The single longest real race stint for a circuit + compound.

    A stint is identified by (season_year, round_number, driver_code, stint)
    — NOT by (driver_code, stint) alone. The same stint number recurs every
    race, so the looser key would splice laps from different races into one
    fabricated mega-stint (e.g. SAI stint 2 at Silverstone spans 4 seasons
    and 102 laps, versus the real longest of 36).
    """
    canonical = normalize_circuit_name(circuit)
    compound_code = compound.upper()
    cache_key = (canonical, compound_code)
    now = time.time()

    cached = stint_sample_cache.get(cache_key)
    if cached and (now - cached["timestamp"]) < CACHE_TTL:
        return cached["data"]

    empty = {
        "driver_code": None,
        "compound": compound_code,
        "laps": [],
        "live": False,
    }

    try:
        if os.getenv("OFFLINE_MODE", "").lower() == "true":
            raise RuntimeError("Offline mode is enabled")

        from google.cloud import bigquery

        client = _readonly_bq_client()

        query = """
            WITH longest_stint AS (
              SELECT season_year, round_number, driver_code, stint
              FROM f1_raw_staging.stg_lap_times
              WHERE circuit_name = @circuit
                AND compound = @compound
                AND session_type = 'RACE'
                AND lap_time_seconds IS NOT NULL
              GROUP BY season_year, round_number, driver_code, stint
              ORDER BY COUNT(*) DESC, season_year DESC, driver_code
              LIMIT 1
            )
            SELECT l.driver_code, l.lap_number, l.tyre_life, l.lap_time_seconds
            FROM f1_raw_staging.stg_lap_times l
            JOIN longest_stint s
              USING (season_year, round_number, driver_code, stint)
            WHERE l.circuit_name = @circuit
              AND l.compound = @compound
              AND l.session_type = 'RACE'
              AND l.lap_time_seconds IS NOT NULL
            ORDER BY l.lap_number
        """
        job = client.query(
            query,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("circuit", "STRING", canonical),
                    bigquery.ScalarQueryParameter("compound", "STRING", compound_code),
                ]
            ),
        )

        rows = list(job.result())
        if not rows:
            return empty

        laps = [
            {
                "lap_number": r.lap_number,
                "tyre_life": r.tyre_life,
                "lap_time_seconds": round(r.lap_time_seconds, 3),
            }
            for r in rows
        ]

        data = {
            "driver_code": rows[0].driver_code,
            "compound": compound_code,
            "laps": laps,
            "live": True,
        }
        stint_sample_cache[cache_key] = {"data": data, "timestamp": now}
        return data

    except Exception as e:
        logger.warning(
            f"Failed to fetch stint sample for {canonical!r}/{compound_code!r}, "
            f"returning empty result: {e}"
        )
        return empty


@app.get("/api/race-replay")
async def race_replay(circuit: str):
    """One complete real race at this circuit, grouped lap by lap.

    This is a recorded historical race replayed from the warehouse — not a
    live feed. Picks the most recent season that actually has a full race's
    worth of laps.
    """
    canonical = normalize_circuit_name(circuit)
    now = time.time()

    cached = race_replay_cache.get(canonical)
    if cached and (now - cached["timestamp"]) < CACHE_TTL:
        return cached["data"]

    empty = {
        "circuit_name": canonical,
        "season_year": None,
        "total_laps": 0,
        "laps": [],
        "live": False,
    }

    try:
        if os.getenv("OFFLINE_MODE", "").lower() == "true":
            raise RuntimeError("Offline mode is enabled")

        from google.cloud import bigquery

        client = _readonly_bq_client()
        circuit_param = bigquery.ScalarQueryParameter("circuit", "STRING", canonical)

        # Most recent season with a real race's worth of laps at this circuit.
        season_row = list(
            client.query(
                """
                SELECT season_year
                FROM f1_raw_staging.stg_lap_times
                WHERE circuit_name = @circuit AND session_type = 'RACE'
                GROUP BY season_year
                HAVING COUNT(DISTINCT lap_number) >= @min_laps
                ORDER BY season_year DESC
                LIMIT 1
                """,
                job_config=bigquery.QueryJobConfig(
                    query_parameters=[
                        circuit_param,
                        bigquery.ScalarQueryParameter(
                            "min_laps", "INT64", MIN_REPLAY_LAPS
                        ),
                    ]
                ),
            ).result()
        )
        if not season_row:
            return empty
        season_year = season_row[0].season_year

        job = client.query(
            """
            SELECT driver_code, lap_number, position, lap_time_seconds
            FROM f1_raw_staging.stg_lap_times
            WHERE circuit_name = @circuit
              AND season_year = @season
              AND session_type = 'RACE'
            ORDER BY lap_number, position
            """,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    circuit_param,
                    bigquery.ScalarQueryParameter("season", "INT64", season_year),
                ]
            ),
        )

        # Group into one entry per lap, preserving the position ordering.
        by_lap: dict[int, list] = {}
        for row in job.result():
            by_lap.setdefault(row.lap_number, []).append(
                {
                    "driver_code": row.driver_code,
                    "position": row.position,
                    "lap_time_seconds": round(row.lap_time_seconds, 3),
                }
            )

        if not by_lap:
            return empty

        laps = [
            {"lap_number": lap_number, "drivers": by_lap[lap_number]}
            for lap_number in sorted(by_lap)
        ]

        data = {
            "circuit_name": canonical,
            "season_year": season_year,
            # The real race distance. Not the same as len(laps): laps with no
            # recorded times are absent, so British 2024 has 44 lap entries
            # spanning a 52-lap race.
            "total_laps": max(by_lap),
            "laps": laps,
            "live": True,
        }
        race_replay_cache[canonical] = {"data": data, "timestamp": now}
        return data

    except Exception as e:
        logger.warning(
            f"Failed to fetch race replay for {canonical!r}, "
            f"returning empty result: {e}"
        )
        return empty


@app.post("/api/ask")
async def ask_question(request: AskRequest):
    """
    Natural-language query against the F1 data warehouse.

    Uses a LangChain text-to-SQL agent backed by Gemini to generate and execute
    SQL against the BigQuery warehouse (dbt-modeled tables).
    """
    try:
        from src.agent.query_agent import QueryAgent
        from src.agent.query_logger import QueryLogger

        agent = QueryAgent()
        query_logger = QueryLogger()

        result = agent.ask(request.question)
        query_logger.log(
            question=request.question,
            generated_sql=result.get("generated_sql", ""),
            response=result.get("natural_language_answer", ""),
            success="error" not in result,
            error=result.get("error"),
            estimated_bytes=result.get("estimated_bytes_scanned", 0),
        )
        return {"success": True, "data": result}
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="Agent module not yet configured. Set GOOGLE_API_KEY and BigQuery credentials.",
        )
    except Exception as e:
        logger.error(f"❌ Agent Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    print("🏎️ Starting F1 Race Intelligence Platform...")
    print("📍 API will be available at: http://localhost:8000")
    print("📚 Docs at: http://localhost:8000/docs")
    print("🎯 Health: http://localhost:8000/api/health")
    uvicorn.run(app, host="0.0.0.0", port=8000)
