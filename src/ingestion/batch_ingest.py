"""
Batch ingestion: pull historical F1 data via FastF1 and load into BigQuery.

Wraps the existing FastF1Collector and routes data through BigQueryLoader.
Designed to be run as a scheduled job (cron / GitHub Actions).

Usage:
    python -m src.ingestion.batch_ingest --year 2024 --circuits all
    python -m src.ingestion.batch_ingest --year 2024 --circuits "Hungarian Grand Prix"
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.data_collectors.fastf1_collector import FastF1Collector
from src.warehouse.bigquery_loader import BigQueryLoader
from src.utils.circuit_mapping import CircuitMapper

logger = logging.getLogger(__name__)


def ingest_circuit(collector: FastF1Collector, loader: BigQueryLoader,
                   circuit_name: str, year: int, backfill: bool = False) -> dict:
    """Ingest a single circuit's data for a given year (or all years if backfill=True)."""
    stats = {"circuit": circuit_name, "year": year, "race_results": 0,
             "qualifying": 0, "lap_times": 0, "weather": 0, "errors": []}

    try:
        logger.info(f"🏁 Ingesting {circuit_name} {'(backfill all years)' if backfill else year}")
        historical = collector.get_circuit_historical_data(circuit_name)

        for race in historical:
            race_year = race.get("year")
            if not backfill and race_year != year:
                continue

            race_round = race.get("round", 0)
            logger.info(f"  📅 Processing {circuit_name} {race_year} (Round {race_round})")

            # --- Race results ---
            race_rows = []
            for code, ddata in race.get("drivers", {}).items():
                race_rows.append({
                    "year": race_year,
                    "round": race_round,
                    "circuit_name": circuit_name,
                    "driver_code": code,
                    "driver_name": ddata.get("name", ""),
                    "team": ddata.get("team", ""),
                    "grid_position": ddata.get("qualifying_position"),
                    "finish_position": ddata.get("race_position"),
                    "points": ddata.get("race_points", 0),
                    "status": ddata.get("race_status", "Unknown"),
                })
            stats["race_results"] += loader.load_race_results(race_rows)

            # --- Qualifying results ---
            quali_session = race.get("sessions", {}).get("Qualifying", {})
            raw_quali = quali_session.get("raw_qualifying", [])
            if raw_quali:
                quali_rows = []
                for q in raw_quali:
                    if not q.get("driver_code"):
                        continue
                    quali_rows.append({
                        "year": race_year,
                        "round": race_round,
                        "circuit_name": circuit_name,
                        "driver_code": q["driver_code"],
                        "driver_name": q.get("driver_name", ""),
                        "team": q.get("team", ""),
                        "position": q.get("position"),
                        "q1_time": q.get("q1_time"),
                        "q2_time": q.get("q2_time"),
                        "q3_time": q.get("q3_time"),
                    })
                stats["qualifying"] += loader.load_qualifying_results(quali_rows)
            else:
                logger.warning(f"  ⚠️ No qualifying data for {circuit_name} {race_year}")

            # --- Lap times (raw per-lap records) ---
            for session_name, session_data in race.get("sessions", {}).items():
                raw_laps = session_data.get("raw_laps", [])
                if not raw_laps:
                    continue
                
                lap_rows = []
                for lap in raw_laps:
                    lap_rows.append({
                        "year": race_year,
                        "round": race_round,
                        "circuit_name": circuit_name,
                        "session_type": lap.get("session_type", session_name.upper()),
                        "driver_code": lap["driver_code"],
                        "lap_number": lap["lap_number"],
                        "lap_time_seconds": lap.get("lap_time_seconds"),
                        "sector1_seconds": lap.get("sector1_seconds"),
                        "sector2_seconds": lap.get("sector2_seconds"),
                        "sector3_seconds": lap.get("sector3_seconds"),
                        "compound": lap.get("compound"),
                        "tyre_life": lap.get("tyre_life"),
                        "stint": lap.get("stint"),
                        "position": lap.get("position"),
                        "is_personal_best": lap.get("is_personal_best"),
                    })
                stats["lap_times"] += loader.load_lap_times(lap_rows)

            # --- Weather ---
            weather = race.get("weather", {})
            if weather.get("available"):
                weather_row = {
                    "year": race_year,
                    "round": race_round,
                    "circuit_name": circuit_name,
                    "session_type": "RACE",
                    "air_temp_avg": weather.get("air_temp_avg"),
                    "track_temp_avg": weather.get("track_temp_avg"),
                    "humidity_avg": weather.get("humidity_avg"),
                    "pressure_avg": weather.get("pressure_avg"),
                    "wind_speed_avg": weather.get("wind_speed_avg"),
                    "rainfall": weather.get("rainfall", False),
                }
                stats["weather"] += loader.load_weather_data([weather_row])
            else:
                logger.warning(
                    f"  ⚠️ Weather data unavailable for {circuit_name} {race_year}"
                )

    except Exception as e:
        logger.error(f"❌ Error ingesting {circuit_name} {year}: {e}")
        stats["errors"].append(str(e))

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="🏎️  F1 Batch Ingestion — FastF1 → BigQuery"
    )
    parser.add_argument("--year", type=int, default=2024, help="Season year")
    parser.add_argument("--circuits", type=str, default="all",
                        help='Circuit name or "all" for full calendar')
    parser.add_argument("--log-level", default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--backfill", action="store_true",
                        help="Ingest all available historical years for the given circuits, ignoring --year")
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level),
                        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    collector = FastF1Collector()
    loader = BigQueryLoader()
    mapper = CircuitMapper()

    if args.circuits.lower() == "all":
        circuits = mapper.list_available_circuits()
    else:
        # Normalize to canonical official name
        circuit_key = mapper.get_circuit_key(args.circuits)
        if not circuit_key:
            logger.error(f"❌ Unknown circuit: '{args.circuits}'")
            sys.exit(1)
        
        circuit_info = mapper.get_circuit_info(circuit_key)
        canonical_name = circuit_info.get("official_names", [args.circuits])[0]
        circuits = [canonical_name]

    logger.info(f"📦 Batch ingestion: {len(circuits)} circuits for {'all historical years' if args.backfill else args.year}")

    all_stats = []
    for circuit in circuits:
        stats = ingest_circuit(collector, loader, circuit, args.year, args.backfill)
        all_stats.append(stats)
        logger.info(f"  ✅ {circuit}: {stats['race_results']} results, "
                     f"{stats['qualifying']} qualifying, "
                     f"{stats['lap_times']} laps, "
                     f"{stats['weather']} weather records")

    total_results = sum(s["race_results"] for s in all_stats)
    total_qualifying = sum(s["qualifying"] for s in all_stats)
    total_laps = sum(s["lap_times"] for s in all_stats)
    total_errors = sum(len(s["errors"]) for s in all_stats)
    logger.info(f"\n🏁 Batch complete: {total_results} race results, "
                f"{total_qualifying} qualifying, {total_laps} laps loaded, "
                f"{total_errors} errors")


if __name__ == "__main__":
    main()
