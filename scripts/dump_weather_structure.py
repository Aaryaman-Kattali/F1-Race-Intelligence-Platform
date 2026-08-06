"""One-time diagnostic/migration script. Not part of the regular pipeline."""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.data_collectors.fastf1_collector import FastF1Collector

collector = FastF1Collector()
historical = collector.get_circuit_historical_data("Hungarian Grand Prix")

for race in historical:
    if race.get("year") == 2024:
        print("Keys of race data:", list(race.keys()))
        print("Keys of race['weather']:", list(race.get("weather", {}).keys()))
        if "weather" in race:
            print("Content of race['weather']:", json.dumps(race["weather"], indent=2))
        
        # also print sessions just in case
        print("Keys of race['sessions']:", list(race.get("sessions", {}).keys()))
        if "Race" in race.get("sessions", {}):
            race_session = race["sessions"]["Race"]
            print("Keys of race['sessions']['Race']:", list(race_session.keys()))
            if "weather" in race_session:
                print("Content of race['sessions']['Race']['weather']:", json.dumps(race_session["weather"], indent=2))
        break
