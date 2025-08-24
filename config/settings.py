"""
Configuration settings for F1 GP Predictor - Updated with Real 2025 Data.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
FASTF1_CACHE_DIR = DATA_DIR / "fastf1_cache"
PREDICTIONS_DIR = DATA_DIR / "predictions"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

# Create directories
for directory in [DATA_DIR, FASTF1_CACHE_DIR, PREDICTIONS_DIR, PROCESSED_DATA_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# API Keys
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

# GPU Configuration (for your GTX 1650)
USE_GPU = os.getenv("USE_GPU", "true").lower() == "true"
CUDA_DEVICE = os.getenv("CUDA_DEVICE", "cuda:0")

# XGBoost GPU Configuration
GPU_CONFIG = {
    "tree_method": "hist",
    "device": CUDA_DEVICE if USE_GPU else "cpu",
    "n_jobs": 1 if USE_GPU else -1,
}

# F1 Configuration
CURRENT_SEASON = 2025
HISTORICAL_YEARS = [2018, 2019, 2020, 2021, 2022, 2023, 2024]

# *** REAL 2025 F1 DRIVER ROSTER (from actual season data) ***
ACTIVE_DRIVERS_2025 = [
    {"code": "PIA", "name": "Oscar Piastri", "team": "McLaren", "number": 81},
    {"code": "NOR", "name": "Lando Norris", "team": "McLaren", "number": 4},
    {"code": "LEC", "name": "Charles Leclerc", "team": "Ferrari", "number": 16},
    {"code": "HAM", "name": "Lewis Hamilton", "team": "Ferrari", "number": 44},  # Hamilton at Ferrari in 2025
    {"code": "VER", "name": "Max Verstappen", "team": "Red Bull Racing", "number": 1},
    {"code": "TSU", "name": "Yuki Tsunoda", "team": "Red Bull Racing", "number": 22},  # Tsunoda promoted to Red Bull
    {"code": "RUS", "name": "George Russell", "team": "Mercedes", "number": 63},
    {"code": "ANT", "name": "Kimi Antonelli", "team": "Mercedes", "number": 12},  # Rookie 2025
    {"code": "SAI", "name": "Carlos Sainz", "team": "Williams", "number": 55},
    {"code": "ALB", "name": "Alexander Albon", "team": "Williams", "number": 23},
    {"code": "ALO", "name": "Fernando Alonso", "team": "Aston Martin", "number": 14},
    {"code": "STR", "name": "Lance Stroll", "team": "Aston Martin", "number": 18},
    {"code": "GAS", "name": "Pierre Gasly", "team": "Alpine", "number": 10},
    {"code": "COL", "name": "Franco Colapinto", "team": "Alpine", "number": 43},  # New in 2025
    {"code": "LAW", "name": "Liam Lawson", "team": "Racing Bulls", "number": 30},  # Promoted from reserve
    {"code": "HAD", "name": "Isack Hadjar", "team": "Racing Bulls", "number": 6},   # Rookie 2025
    {"code": "OCO", "name": "Esteban Ocon", "team": "Haas", "number": 31},
    {"code": "BEA", "name": "Oliver Bearman", "team": "Haas", "number": 87},       # Rookie 2025
    {"code": "HUL", "name": "Nico Hulkenberg", "team": "Kick Sauber", "number": 27},
    {"code": "BOR", "name": "Gabriel Bortoleto", "team": "Kick Sauber", "number": 5}, # Rookie 2025
    # Jack Doohan appears in some races but not consistent - excluding from main roster
]

# Current championship standings (as of Spanish GP 2025)
CURRENT_2025_STANDINGS = {
    "PIA": {"position": 1, "points": 284, "team": "McLaren"},
    "NOR": {"position": 2, "points": 275, "team": "McLaren"},
    "VER": {"position": 3, "points": 187, "team": "Red Bull Racing"},
    "RUS": {"position": 4, "points": 172, "team": "Mercedes"},
    "LEC": {"position": 5, "points": 151, "team": "Ferrari"},
    "HAM": {"position": 6, "points": 109, "team": "Ferrari"},
    "ANT": {"position": 7, "points": 64, "team": "Mercedes"},
    "ALB": {"position": 8, "points": 54, "team": "Williams"},
    "HUL": {"position": 9, "points": 37, "team": "Kick Sauber"},
    "OCO": {"position": 10, "points": 27, "team": "Haas"},
    "ALO": {"position": 11, "points": 26, "team": "Aston Martin"},
    "STR": {"position": 12, "points": 26, "team": "Aston Martin"},
    "HAD": {"position": 13, "points": 22, "team": "Racing Bulls"},
    "GAS": {"position": 14, "points": 20, "team": "Alpine"},
    "LAW": {"position": 15, "points": 20, "team": "Racing Bulls"},
    "SAI": {"position": 16, "points": 16, "team": "Williams"},
    "BOR": {"position": 17, "points": 14, "team": "Kick Sauber"},
    "TSU": {"position": 18, "points": 10, "team": "Red Bull Racing"},
    "BEA": {"position": 19, "points": 8, "team": "Haas"},
    "COL": {"position": 20, "points": 0, "team": "Alpine"},
    "DOO": {"position": 21, "points": 0, "team": "Kick Sauber"},  # Jack Doohan as reserve    
}

# Helper function to get active driver codes
def get_active_driver_codes():
    """Get list of 2025 active driver codes."""
    return [driver['code'] for driver in ACTIVE_DRIVERS_2025]

def get_active_driver_info(driver_code: str):
    """Get driver info by code."""
    for driver in ACTIVE_DRIVERS_2025:
        if driver['code'] == driver_code:
            return driver
    return None

def is_rookie_driver_2025(driver_code: str):
    """Check if driver is new to F1 in 2025 (based on actual data)."""
    # Rookies based on the 2025 season data
    rookie_drivers = ['ANT', 'BEA', 'HAD', 'BOR', 'COL']  # Real rookies in 2025
    return driver_code in rookie_drivers

def get_2025_driver_performance(driver_code: str):
    """Get current season performance for driver."""
    return CURRENT_2025_STANDINGS.get(driver_code, {
        "position": 20,
        "points": 0,
        "team": "Unknown"
    })

# Optimization flags
USE_LOCAL_STANDINGS = True  # Use local data instead of API
ENABLE_API_FALLBACK = False  # Disable API fallback for standings
FAST_PREDICTION_MODE = True  # Enable optimized prediction mode

# Team performance rankings (based on constructor standings)
TEAM_RANKINGS_2025 = {
    "McLaren": 1,           # 303 points
    "Ferrari": 2,           # 232 points  
    "Mercedes": 3,          # 226 points
    "Red Bull Racing": 4,   # 98 points
    "Williams": 5,          # 45 points
    "Racing Bulls": 6,      # 26 points
    "Haas": 7,             # 19 points
    "Aston Martin": 8,     # 10 points
    "Alpine": 9,           # 10 points
    "Kick Sauber": 10     # 5 points
}

# Prediction weights (updated for 2025 season characteristics)
DEFAULT_FEATURE_WEIGHTS = {
    'current_2025_form': 0.40,       # Highest weight for current season
    'historical_performance': 0.30,  # Reduced weight
    'qualifying_expected': 0.20,     # Circuit dependent
    'weather_adaptation': 0.05,
    'circuit_experience': 0.05
}

# File paths for 2025 data
F1_2025_DATA_FILES = {
    'race_results': BASE_DIR / "data" / "F1_2025_RaceResults.csv",
    'qualifying_results': BASE_DIR / "data" / "F1_2025_QualifyingResults.csv",
    'sprint_results': BASE_DIR / "data" / "F1_2025_SprintResults.csv",
    'sprint_qualifying': BASE_DIR / "data" / "F1_2025_SprintQualifyingResults.csv"
}

# Logging configuration
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        },
    },
    'handlers': {
        'default': {
            'level': 'INFO',
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        '': {
            'handlers': ['default'],
            'level': 'INFO',
            'propagate': False
        }
    }
}
