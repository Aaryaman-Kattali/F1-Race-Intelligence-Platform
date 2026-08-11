import os
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()
client = bigquery.Client(project=os.getenv("GCP_PROJECT_ID"))

query = """
    SELECT count(*) as cnt, count(distinct lap_number) as laps, count(distinct driver_code) as drivers
    FROM `f1-platform-dev.f1_raw.live_lap_telemetry`
    WHERE circuit_name = 'Hungarian Grand Prix' AND year = 2024
"""
job = client.query(query)
for row in job:
    print(
        f"live_lap_telemetry count: {row['cnt']} rows (Laps: {row['laps']}, Drivers: {row['drivers']})"
    )
