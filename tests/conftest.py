"""
Shared pytest fixtures for F1 Race Intelligence Platform tests.

These fixtures provide mock data so tests don't depend on live APIs,
FastF1 network calls, or BigQuery credentials.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import pandas as pd
import numpy as np

# Ensure project root is on the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# ---------------------------------------------------------------------------
# Force OFFLINE_MODE before any config imports so DynamicStandingsLoader
# uses the static fallback and doesn't attempt network calls during tests.
# ---------------------------------------------------------------------------
import os

os.environ["OFFLINE_MODE"] = "true"


# ---------------------------------------------------------------------------
# Fixtures: historical race data
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_historical_data():
    """Mock historical race data for 3 years at a single circuit."""
    return [
        {
            "year": 2022,
            "round": 13,
            "circuit_name": "Hungarian Grand Prix",
            "race_winner": "VER",
            "drivers": {
                "VER": {
                    "name": "Max Verstappen",
                    "team": "Red Bull Racing",
                    "race_position": 1,
                    "qualifying_position": 10,
                    "race_points": 26,
                    "race_status": "Finished",
                },
                "HAM": {
                    "name": "Lewis Hamilton",
                    "team": "Mercedes",
                    "race_position": 2,
                    "qualifying_position": 7,
                    "race_points": 18,
                    "race_status": "Finished",
                },
                "NOR": {
                    "name": "Lando Norris",
                    "team": "McLaren",
                    "race_position": 4,
                    "qualifying_position": 4,
                    "race_points": 12,
                    "race_status": "Finished",
                },
                "RUS": {
                    "name": "George Russell",
                    "team": "Mercedes",
                    "race_position": 3,
                    "qualifying_position": 1,
                    "race_points": 15,
                    "race_status": "Finished",
                },
                "LEC": {
                    "name": "Charles Leclerc",
                    "team": "Ferrari",
                    "race_position": 6,
                    "qualifying_position": 3,
                    "race_points": 8,
                    "race_status": "Finished",
                },
                "ALO": {
                    "name": "Fernando Alonso",
                    "team": "Alpine",
                    "race_position": 9,
                    "qualifying_position": 9,
                    "race_points": 2,
                    "race_status": "Finished",
                },
            },
            "weather": {"available": True, "air_temp_avg": 33.5, "rainfall": False},
        },
        {
            "year": 2023,
            "round": 12,
            "circuit_name": "Hungarian Grand Prix",
            "race_winner": "VER",
            "drivers": {
                "VER": {
                    "name": "Max Verstappen",
                    "team": "Red Bull Racing",
                    "race_position": 1,
                    "qualifying_position": 2,
                    "race_points": 25,
                    "race_status": "Finished",
                },
                "NOR": {
                    "name": "Lando Norris",
                    "team": "McLaren",
                    "race_position": 2,
                    "qualifying_position": 3,
                    "race_points": 18,
                    "race_status": "Finished",
                },
                "HAM": {
                    "name": "Lewis Hamilton",
                    "team": "Mercedes",
                    "race_position": 4,
                    "qualifying_position": 6,
                    "race_points": 12,
                    "race_status": "Finished",
                },
                "LEC": {
                    "name": "Charles Leclerc",
                    "team": "Ferrari",
                    "race_position": 5,
                    "qualifying_position": 5,
                    "race_points": 10,
                    "race_status": "Finished",
                },
            },
            "weather": {"available": True, "air_temp_avg": 30.2, "rainfall": False},
        },
        {
            "year": 2024,
            "round": 13,
            "circuit_name": "Hungarian Grand Prix",
            "race_winner": "PIA",
            "drivers": {
                "PIA": {
                    "name": "Oscar Piastri",
                    "team": "McLaren",
                    "race_position": 1,
                    "qualifying_position": 2,
                    "race_points": 25,
                    "race_status": "Finished",
                },
                "NOR": {
                    "name": "Lando Norris",
                    "team": "McLaren",
                    "race_position": 2,
                    "qualifying_position": 1,
                    "race_points": 18,
                    "race_status": "Finished",
                },
                "VER": {
                    "name": "Max Verstappen",
                    "team": "Red Bull Racing",
                    "race_position": 5,
                    "qualifying_position": 3,
                    "race_points": 10,
                    "race_status": "Finished",
                },
                "HAM": {
                    "name": "Lewis Hamilton",
                    "team": "Mercedes",
                    "race_position": 3,
                    "qualifying_position": 5,
                    "race_points": 15,
                    "race_status": "Finished",
                },
                "LEC": {
                    "name": "Charles Leclerc",
                    "team": "Ferrari",
                    "race_position": 4,
                    "qualifying_position": 4,
                    "race_points": 12,
                    "race_status": "Finished",
                },
            },
            "weather": {"available": True, "air_temp_avg": 35.0, "rainfall": False},
        },
    ]


# ---------------------------------------------------------------------------
# Fixtures: circuit configuration
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_circuit_config():
    """Mock circuit config for the Hungaroring."""
    return {
        "circuit_key": "hungarian_gp",
        "official_names": ["Hungarian Grand Prix"],
        "circuit_type": "technical",
        "qualifying_importance": 0.85,
        "overtaking_difficulty": "high",
        "weather_sensitivity": 0.4,
        "key_factors": ["downforce", "traction", "mechanical_grip"],
        "location": {
            "city": "Budapest",
            "country": "Hungary",
            "coordinates": [47.5789, 19.2486],
        },
    }


# ---------------------------------------------------------------------------
# Fixtures: weather data
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_weather_data_dry():
    """Mock dry weather conditions."""
    return {
        "current_weather": {
            "available": True,
            "temperature": 32.0,
        },
        "race_weekend_analysis": {
            "race_day_conditions": {
                "temperature": 34.0,
                "rain_probability": 10,
                "weather_impact": "normal_conditions",
            }
        },
    }


@pytest.fixture
def mock_weather_data_wet():
    """Mock wet weather conditions."""
    return {
        "current_weather": {
            "available": True,
            "temperature": 18.0,
        },
        "race_weekend_analysis": {
            "race_day_conditions": {
                "temperature": 17.0,
                "rain_probability": 80,
                "weather_impact": "high_rain_impact",
            }
        },
    }


# ---------------------------------------------------------------------------
# Fixtures: current intelligence
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_current_intelligence():
    """Mock current-season intelligence data (no qualifying available)."""
    return {
        "driver_standings": {
            "standings_available": True,
            "drivers": [
                {
                    "code": "PIA",
                    "name": "Oscar Piastri",
                    "position": 1,
                    "points": 284,
                    "team": "McLaren",
                },
                {
                    "code": "NOR",
                    "name": "Lando Norris",
                    "position": 2,
                    "points": 275,
                    "team": "McLaren",
                },
                {
                    "code": "VER",
                    "name": "Max Verstappen",
                    "position": 3,
                    "points": 187,
                    "team": "Red Bull Racing",
                },
                {
                    "code": "RUS",
                    "name": "George Russell",
                    "position": 4,
                    "points": 172,
                    "team": "Mercedes",
                },
                {
                    "code": "LEC",
                    "name": "Charles Leclerc",
                    "position": 5,
                    "points": 151,
                    "team": "Ferrari",
                },
            ],
        },
        "team_standings": {
            "standings_available": True,
            "constructors": [
                {"team": "McLaren", "points": 559},
                {"team": "Ferrari", "points": 260},
            ],
        },
        "race_weekend_data": {},
        "standings_source": "test_fixture",
    }


# ---------------------------------------------------------------------------
# Fixtures: features DataFrame
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_features_df():
    """Pre-built features DataFrame for predictor scoring tests."""
    data = {
        "driver_name": [
            "Oscar Piastri",
            "Lando Norris",
            "Max Verstappen",
            "George Russell",
            "Kimi Antonelli",
        ],
        "team_2025": ["McLaren", "McLaren", "Red Bull Racing", "Mercedes", "Mercedes"],
        "is_rookie_2025": [False, False, False, False, True],
        "historical_avg_position": [3.5, 4.0, 1.8, 4.5, 12.0],
        "grid_position": [2, 1, 3, 5, 10],
        "circuit_type_advantage": [0.2, 0.2, 0.2, 0.0, 0.0],
        "current_form_score": [0.95, 0.90, 0.85, 0.80, 0.65],
        "current_team_2025": [
            "McLaren",
            "McLaren",
            "Red Bull Racing",
            "Mercedes",
            "Mercedes",
        ],
    }
    df = pd.DataFrame(data, index=["PIA", "NOR", "VER", "RUS", "ANT"])
    df.index.name = "driver_code"
    return df
