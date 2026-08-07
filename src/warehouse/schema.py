"""
BigQuery table schema definitions for the F1 Race Intelligence Platform.
"""

from google.cloud.bigquery import SchemaField

# ---------------------------------------------------------------------------
# Raw layer schemas
# ---------------------------------------------------------------------------

RACE_RESULTS_SCHEMA = [
    SchemaField("year", "INTEGER", mode="REQUIRED"),
    SchemaField("round", "INTEGER", mode="REQUIRED"),
    SchemaField("circuit_name", "STRING", mode="REQUIRED"),
    SchemaField("driver_code", "STRING", mode="REQUIRED"),
    SchemaField("driver_name", "STRING"),
    SchemaField("team", "STRING"),
    SchemaField("grid_position", "INTEGER"),
    SchemaField("finish_position", "INTEGER"),
    SchemaField("points", "FLOAT"),
    SchemaField("status", "STRING"),
    SchemaField("ingested_at", "TIMESTAMP"),
]

QUALIFYING_RESULTS_SCHEMA = [
    SchemaField("year", "INTEGER", mode="REQUIRED"),
    SchemaField("round", "INTEGER", mode="REQUIRED"),
    SchemaField("circuit_name", "STRING", mode="REQUIRED"),
    SchemaField("driver_code", "STRING", mode="REQUIRED"),
    SchemaField("driver_name", "STRING"),
    SchemaField("team", "STRING"),
    SchemaField("position", "INTEGER"),
    SchemaField("q1_time", "STRING"),
    SchemaField("q2_time", "STRING"),
    SchemaField("q3_time", "STRING"),
    SchemaField("ingested_at", "TIMESTAMP"),
]

LAP_TIMES_SCHEMA = [
    SchemaField("year", "INTEGER", mode="REQUIRED"),
    SchemaField("round", "INTEGER", mode="REQUIRED"),
    SchemaField("circuit_name", "STRING", mode="REQUIRED"),
    SchemaField("session_type", "STRING", mode="REQUIRED"),
    SchemaField("driver_code", "STRING", mode="REQUIRED"),
    SchemaField("lap_number", "INTEGER", mode="REQUIRED"),
    SchemaField("lap_time_seconds", "FLOAT"),
    SchemaField("sector1_seconds", "FLOAT"),
    SchemaField("sector2_seconds", "FLOAT"),
    SchemaField("sector3_seconds", "FLOAT"),
    SchemaField("compound", "STRING"),
    SchemaField("tyre_life", "INTEGER"),
    SchemaField("stint", "INTEGER"),
    SchemaField("position", "INTEGER"),
    SchemaField("is_personal_best", "BOOLEAN"),
    SchemaField("ingested_at", "TIMESTAMP"),
]

WEATHER_SCHEMA = [
    SchemaField("year", "INTEGER", mode="REQUIRED"),
    SchemaField("round", "INTEGER", mode="REQUIRED"),
    SchemaField("circuit_name", "STRING", mode="REQUIRED"),
    SchemaField("session_type", "STRING"),
    SchemaField("air_temp_avg", "FLOAT"),
    SchemaField("track_temp_avg", "FLOAT"),
    SchemaField("humidity_avg", "FLOAT"),
    SchemaField("pressure_avg", "FLOAT"),
    SchemaField("wind_speed_avg", "FLOAT"),
    SchemaField("rainfall", "BOOLEAN"),
    SchemaField("ingested_at", "TIMESTAMP"),
]

STANDINGS_SCHEMA = [
    SchemaField("season", "INTEGER", mode="REQUIRED"),
    SchemaField("round", "INTEGER"),
    SchemaField("driver_code", "STRING", mode="REQUIRED"),
    SchemaField("driver_name", "STRING"),
    SchemaField("team", "STRING"),
    SchemaField("position", "INTEGER"),
    SchemaField("points", "FLOAT"),
    SchemaField("ingested_at", "TIMESTAMP"),
]

LIVE_LAP_TELEMETRY_SCHEMA = [
    SchemaField("year", "INTEGER", mode="REQUIRED"),
    SchemaField("round", "INTEGER", mode="REQUIRED"),
    SchemaField("circuit_name", "STRING"),
    SchemaField("driver_code", "STRING", mode="REQUIRED"),
    SchemaField("lap_number", "INTEGER", mode="REQUIRED"),
    SchemaField("lap_time_seconds", "FLOAT"),
    SchemaField("sector1_seconds", "FLOAT"),
    SchemaField("sector2_seconds", "FLOAT"),
    SchemaField("sector3_seconds", "FLOAT"),
    SchemaField("compound", "STRING"),
    SchemaField("tyre_life", "INTEGER"),
    SchemaField("position", "INTEGER"),
    SchemaField("gap_to_leader", "FLOAT"),
    SchemaField("published_at", "TIMESTAMP"),
    SchemaField("ingested_at", "TIMESTAMP"),
]

# Table name → schema mapping
TABLE_SCHEMAS = {
    "race_results": RACE_RESULTS_SCHEMA,
    "qualifying_results": QUALIFYING_RESULTS_SCHEMA,
    "lap_times": LAP_TIMES_SCHEMA,
    "weather": WEATHER_SCHEMA,
    "standings": STANDINGS_SCHEMA,
    "live_lap_telemetry": LIVE_LAP_TELEMETRY_SCHEMA,
}
