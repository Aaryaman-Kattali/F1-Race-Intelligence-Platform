"""One-time diagnostic/migration script. Not part of the regular pipeline."""

"""Verification queries for Parts 1-3."""
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from google.cloud import bigquery
project_id = os.getenv("GCP_PROJECT_ID", "f1-platform-dev")
client = bigquery.Client(project=project_id)

# 1. Qualifying count for Hungary
q1 = f"""
SELECT COUNT(*) as cnt
FROM `{project_id}.f1_raw_staging.stg_qualifying`
WHERE LOWER(circuit_name) LIKE '%hungarian%'
"""
print("=== stg_qualifying: Hungary total rows ===")
for row in client.query(q1).result():
    print(f"  Count: {row.cnt}")

# 2. Lap times count for Hungary
q2 = f"""
SELECT COUNT(*) as cnt
FROM `{project_id}.f1_raw_staging.stg_lap_times`
WHERE LOWER(circuit_name) LIKE '%hungarian%'
"""
print("\n=== stg_lap_times: Hungary total rows ===")
for row in client.query(q2).result():
    print(f"  Count: {row.cnt}")

# 3. Qualifying per year breakdown
q3 = f"""
SELECT season_year, COUNT(*) as drivers
FROM `{project_id}.f1_raw_staging.stg_qualifying`
WHERE LOWER(circuit_name) LIKE '%hungarian%'
GROUP BY season_year
ORDER BY season_year
"""
print("\n=== stg_qualifying: Hungary per-year breakdown ===")
for row in client.query(q3).result():
    print(f"  {row.season_year}: {row.drivers} drivers")

# 4. tire_degradation_by_circuit output
q4 = f"""
SELECT circuit_name, driver_code, compound, n_laps, deg_seconds_per_lap
FROM `{project_id}.f1_raw_marts.tire_degradation_by_circuit`
WHERE LOWER(circuit_name) LIKE '%hungarian%'
ORDER BY compound, deg_seconds_per_lap DESC
LIMIT 15
"""
print("\n=== tire_degradation_by_circuit: Hungary sample ===")
for row in client.query(q4).result():
    print(f"  {row.driver_code} | {row.compound} | {row.n_laps} laps | deg={row.deg_seconds_per_lap} s/lap")
