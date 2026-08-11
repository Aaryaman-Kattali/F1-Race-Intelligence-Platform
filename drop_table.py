import os
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()
client = bigquery.Client(project=os.getenv("GCP_PROJECT_ID"))

table_id = f"{os.getenv('GCP_PROJECT_ID')}.f1_raw.live_lap_telemetry"
print(f"Deleting table {table_id}...")
client.delete_table(table_id, not_found_ok=True)
print("Table deleted.")
