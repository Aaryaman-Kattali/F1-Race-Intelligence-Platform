"""
Configuration settings for F1 Race Intelligence Platform.

Driver roster and championship standings are loaded dynamically from FastF1/web
collectors and cached locally.  Static fallbacks are used when OFFLINE_MODE=true
or when the dynamic fetch fails.
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
FASTF1_CACHE_DIR = DATA_DIR / "fastf1_cache"
PREDICTIONS_DIR = DATA_DIR / "predictions"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
CACHE_DIR = DATA_DIR / "cache"

# Create directories
for directory in [
    DATA_DIR,
    FASTF1_CACHE_DIR,
    PREDICTIONS_DIR,
    PROCESSED_DATA_DIR,
    CACHE_DIR,
]:
    directory.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")

# ---------------------------------------------------------------------------
# GPU Configuration
# ---------------------------------------------------------------------------
USE_GPU = os.getenv("USE_GPU", "true").lower() == "true"
CUDA_DEVICE = os.getenv("CUDA_DEVICE", "cuda:0")

GPU_CONFIG = {
    "tree_method": "hist",
    "device": CUDA_DEVICE if USE_GPU else "cpu",
    "n_jobs": 1 if USE_GPU else -1,
}

# ---------------------------------------------------------------------------
# F1 Configuration
# ---------------------------------------------------------------------------
CURRENT_SEASON = 2025
HISTORICAL_YEARS = [2018, 2019, 2020, 2021, 2022, 2023, 2024]
OFFLINE_MODE = os.getenv("OFFLINE_MODE", "false").lower() == "true"

# ---------------------------------------------------------------------------
# Static fallback data  (used when dynamic fetch fails or OFFLINE_MODE=true)
# ---------------------------------------------------------------------------
_FALLBACK_DRIVERS_2025 = [
    {"code": "PIA", "name": "Oscar Piastri", "team": "McLaren", "number": 81},
    {"code": "NOR", "name": "Lando Norris", "team": "McLaren", "number": 4},
    {"code": "LEC", "name": "Charles Leclerc", "team": "Ferrari", "number": 16},
    {"code": "HAM", "name": "Lewis Hamilton", "team": "Ferrari", "number": 44},
    {"code": "VER", "name": "Max Verstappen", "team": "Red Bull Racing", "number": 1},
    {"code": "TSU", "name": "Yuki Tsunoda", "team": "Red Bull Racing", "number": 22},
    {"code": "RUS", "name": "George Russell", "team": "Mercedes", "number": 63},
    {"code": "ANT", "name": "Kimi Antonelli", "team": "Mercedes", "number": 12},
    {"code": "SAI", "name": "Carlos Sainz", "team": "Williams", "number": 55},
    {"code": "ALB", "name": "Alexander Albon", "team": "Williams", "number": 23},
    {"code": "ALO", "name": "Fernando Alonso", "team": "Aston Martin", "number": 14},
    {"code": "STR", "name": "Lance Stroll", "team": "Aston Martin", "number": 18},
    {"code": "GAS", "name": "Pierre Gasly", "team": "Alpine", "number": 10},
    {"code": "COL", "name": "Franco Colapinto", "team": "Alpine", "number": 43},
    {"code": "LAW", "name": "Liam Lawson", "team": "Racing Bulls", "number": 30},
    {"code": "HAD", "name": "Isack Hadjar", "team": "Racing Bulls", "number": 6},
    {"code": "OCO", "name": "Esteban Ocon", "team": "Haas", "number": 31},
    {"code": "BEA", "name": "Oliver Bearman", "team": "Haas", "number": 87},
    {"code": "HUL", "name": "Nico Hulkenberg", "team": "Kick Sauber", "number": 27},
    {"code": "BOR", "name": "Gabriel Bortoleto", "team": "Kick Sauber", "number": 5},
]

_FALLBACK_STANDINGS_2025 = {
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
    "DOO": {"position": 21, "points": 0, "team": "Kick Sauber"},
}

_FALLBACK_TEAM_RANKINGS_2025 = {
    "McLaren": 1,
    "Ferrari": 2,
    "Mercedes": 3,
    "Red Bull Racing": 4,
    "Williams": 5,
    "Racing Bulls": 6,
    "Haas": 7,
    "Aston Martin": 8,
    "Alpine": 9,
    "Kick Sauber": 10,
}


# ---------------------------------------------------------------------------
# Dynamic standings loader
# ---------------------------------------------------------------------------
_STANDINGS_CACHE_FILE = CACHE_DIR / "standings_cache.json"
_STANDINGS_CACHE_TTL = timedelta(hours=24)


class DynamicStandingsLoader:
    """
    Attempts to load current driver roster and championship standings
    dynamically from FastF1, falling back to static data on failure or
    when OFFLINE_MODE is enabled.
    """

    def __init__(self):
        self._drivers: Optional[List[Dict]] = None
        self._standings: Optional[Dict] = None
        self._team_rankings: Optional[Dict] = None
        self._source: str = "not_loaded"

    def _cache_is_valid(self) -> bool:
        """Check if local cache exists and is within TTL."""
        if not _STANDINGS_CACHE_FILE.exists():
            return False
        try:
            with open(_STANDINGS_CACHE_FILE, "r") as f:
                cached = json.load(f)
            cached_at = datetime.fromisoformat(cached.get("cached_at", "2000-01-01"))
            return datetime.now() - cached_at < _STANDINGS_CACHE_TTL
        except Exception:
            return False

    def _load_from_cache(self) -> bool:
        """Load standings from local cache file."""
        try:
            with open(_STANDINGS_CACHE_FILE, "r") as f:
                cached = json.load(f)
            self._drivers = cached["drivers"]
            self._standings = cached["standings"]
            self._team_rankings = cached.get(
                "team_rankings", _FALLBACK_TEAM_RANKINGS_2025
            )
            self._source = "cache"
            logger.info("✅ Loaded standings from local cache")
            return True
        except Exception as e:
            logger.warning(f"⚠️  Cache load failed: {e}")
            return False

    def _save_to_cache(self) -> None:
        """Save current standings to local cache."""
        try:
            cache_data = {
                "cached_at": datetime.now().isoformat(),
                "drivers": self._drivers,
                "standings": self._standings,
                "team_rankings": self._team_rankings,
            }
            with open(_STANDINGS_CACHE_FILE, "w") as f:
                json.dump(cache_data, f, indent=2)
            logger.info(f"💾 Standings cached to {_STANDINGS_CACHE_FILE}")
        except Exception as e:
            logger.warning(f"⚠️  Cache save failed: {e}")

    def _fetch_from_fastf1(self) -> bool:
        """Attempt to fetch current standings from FastF1."""
        try:
            import fastf1

            fastf1.Cache.enable_cache(str(FASTF1_CACHE_DIR))

            # Get current season schedule to find the latest completed round
            schedule = fastf1.get_event_schedule(CURRENT_SEASON)
            now = datetime.now()

            # Find latest completed event
            completed_events = []
            for _, event in schedule.iterrows():
                event_date = event.get("EventDate")
                if event_date is not None:
                    try:
                        if hasattr(event_date, "to_pydatetime"):
                            event_dt = event_date.to_pydatetime()
                        else:
                            event_dt = event_date
                        # Compare date only (strip timezone)
                        if event_dt.replace(tzinfo=None) < now:
                            completed_events.append(event)
                    except Exception:
                        continue

            if not completed_events:
                logger.warning("No completed events found for current season")
                return False

            latest_event = completed_events[-1]
            latest_round = int(latest_event.get("RoundNumber", 0))

            if latest_round == 0:
                return False

            # Load latest race session to get driver info and results
            session = fastf1.get_session(CURRENT_SEASON, latest_round, "Race")
            session.load()

            if session.results.empty:
                return False

            # Build driver roster from session results
            drivers = []
            seen_codes = set()
            for _, row in session.results.iterrows():
                code = str(row.get("Abbreviation", ""))
                if code and code not in seen_codes:
                    seen_codes.add(code)
                    drivers.append(
                        {
                            "code": code,
                            "name": f"{row.get('FirstName', '')} {row.get('LastName', '')}".strip(),
                            "team": str(row.get("TeamName", "Unknown")),
                            "number": int(row.get("DriverNumber", 0)),
                        }
                    )

            if not drivers:
                return False

            # Build standings from championship points
            # FastF1 provides cumulative points in some configurations,
            # but we'll build from session results as a baseline
            standings = {}
            sorted_drivers = sorted(drivers, key=lambda d: d["code"])

            # Try to get actual standings from results Points column
            driver_points = {}
            for _, row in session.results.iterrows():
                code = str(row.get("Abbreviation", ""))
                # Note: session.results.Points is race points, not championship
                # We use it as a signal but the fallback has better cumulative data
                if code:
                    driver_points[code] = float(row.get("Points", 0))

            # Since FastF1 doesn't directly expose championship standings,
            # and we'd need to sum across all rounds, use the fetched roster
            # but keep fallback standings for points (more accurate)
            self._drivers = drivers
            self._standings = (
                _FALLBACK_STANDINGS_2025  # Points from fallback are more accurate
            )
            self._team_rankings = _FALLBACK_TEAM_RANKINGS_2025
            self._source = "fastf1_roster_with_fallback_points"
            logger.info(
                f"✅ Loaded {len(drivers)} drivers from FastF1 (round {latest_round})"
            )
            return True

        except Exception as e:
            logger.warning(f"⚠️  FastF1 fetch failed: {e}")
            return False

    def _use_fallback(self) -> None:
        """Use static fallback data."""
        self._drivers = _FALLBACK_DRIVERS_2025
        self._standings = _FALLBACK_STANDINGS_2025
        self._team_rankings = _FALLBACK_TEAM_RANKINGS_2025
        self._source = "static_fallback"
        logger.info("📋 Using static fallback standings data")

    def load(self) -> None:
        """
        Load standings using priority: cache → FastF1 → static fallback.
        In OFFLINE_MODE, skip network calls entirely.
        """
        if self._drivers is not None:
            return  # Already loaded

        if OFFLINE_MODE:
            logger.info("🔌 OFFLINE_MODE enabled — using static fallback")
            self._use_fallback()
            return

        # Try cache first
        if self._cache_is_valid() and self._load_from_cache():
            return

        # Try FastF1
        if self._fetch_from_fastf1():
            self._save_to_cache()
            return

        # Try stale cache
        if _STANDINGS_CACHE_FILE.exists() and self._load_from_cache():
            logger.info("⚠️  Using stale cache (fresh fetch failed)")
            return

        # Final fallback
        self._use_fallback()

    @property
    def drivers(self) -> List[Dict]:
        self.load()
        return self._drivers

    @property
    def standings(self) -> Dict:
        self.load()
        return self._standings

    @property
    def team_rankings(self) -> Dict:
        self.load()
        return self._team_rankings

    @property
    def source(self) -> str:
        self.load()
        return self._source


# ---------------------------------------------------------------------------
# Module-level singleton — lazy-loaded on first access
# ---------------------------------------------------------------------------
_standings_loader = DynamicStandingsLoader()


# Public API  (drop-in replacements for the old static constants)
# These are properties that trigger loading on first access.


def _get_active_drivers():
    return _standings_loader.drivers


def _get_current_standings():
    return _standings_loader.standings


def _get_team_rankings():
    return _standings_loader.team_rankings


# For backwards compatibility — modules that import these names directly
# will get the data via these module-level references.
# We use a lazy-loading pattern: first access triggers the load.


class _LazyList(list):
    """List that populates itself on first access."""

    def __init__(self, loader_fn):
        self._loader_fn = loader_fn
        self._loaded = False

    def _ensure_loaded(self):
        if not self._loaded:
            self._loaded = True
            super().clear()
            super().extend(self._loader_fn())

    def __iter__(self):
        self._ensure_loaded()
        return super().__iter__()

    def __len__(self):
        self._ensure_loaded()
        return super().__len__()

    def __getitem__(self, index):
        self._ensure_loaded()
        return super().__getitem__(index)

    def __contains__(self, item):
        self._ensure_loaded()
        return super().__contains__(item)

    def __bool__(self):
        self._ensure_loaded()
        return super().__bool__()


class _LazyDict(dict):
    """Dict that populates itself on first access."""

    def __init__(self, loader_fn):
        self._loader_fn = loader_fn
        self._loaded = False

    def _ensure_loaded(self):
        if not self._loaded:
            self._loaded = True
            super().clear()
            super().update(self._loader_fn())

    def __iter__(self):
        self._ensure_loaded()
        return super().__iter__()

    def __len__(self):
        self._ensure_loaded()
        return super().__len__()

    def __getitem__(self, key):
        self._ensure_loaded()
        return super().__getitem__(key)

    def __contains__(self, key):
        self._ensure_loaded()
        return super().__contains__(key)

    def get(self, key, default=None):
        self._ensure_loaded()
        return super().get(key, default)

    def items(self):
        self._ensure_loaded()
        return super().items()

    def keys(self):
        self._ensure_loaded()
        return super().keys()

    def values(self):
        self._ensure_loaded()
        return super().values()

    def __bool__(self):
        self._ensure_loaded()
        return super().__bool__()


# Drop-in replacements for the old module-level constants
ACTIVE_DRIVERS_2025 = _LazyList(_get_active_drivers)
CURRENT_2025_STANDINGS = _LazyDict(_get_current_standings)
TEAM_RANKINGS_2025 = _LazyDict(_get_team_rankings)


# ---------------------------------------------------------------------------
# Helper functions  (unchanged public API)
# ---------------------------------------------------------------------------


def get_active_driver_codes() -> List[str]:
    """Get list of 2025 active driver codes."""
    return [driver["code"] for driver in ACTIVE_DRIVERS_2025]


def get_active_driver_info(driver_code: str) -> Optional[Dict]:
    """Get driver info by code."""
    for driver in ACTIVE_DRIVERS_2025:
        if driver["code"] == driver_code:
            return driver
    return None


def is_rookie_driver_2025(driver_code: str) -> bool:
    """Check if driver is new to F1 in 2025."""
    rookie_drivers = ["ANT", "BEA", "HAD", "BOR", "COL"]
    return driver_code in rookie_drivers


def get_2025_driver_performance(driver_code: str) -> Dict:
    """Get current season performance for driver."""
    return CURRENT_2025_STANDINGS.get(
        driver_code,
        {"position": 20, "points": 0, "team": "Unknown"},
    )


# ---------------------------------------------------------------------------
# Optimization flags
# ---------------------------------------------------------------------------
USE_LOCAL_STANDINGS = True
ENABLE_API_FALLBACK = False
FAST_PREDICTION_MODE = True

# ---------------------------------------------------------------------------
# Prediction weights
# ---------------------------------------------------------------------------
DEFAULT_FEATURE_WEIGHTS = {
    "current_2025_form": 0.40,
    "historical_performance": 0.30,
    "qualifying_expected": 0.20,
    "weather_adaptation": 0.05,
    "circuit_experience": 0.05,
}

# ---------------------------------------------------------------------------
# File paths for 2025 data
# ---------------------------------------------------------------------------
F1_2025_DATA_FILES = {
    "race_results": BASE_DIR / "data" / "F1_2025_RaceResults.csv",
    "qualifying_results": BASE_DIR / "data" / "F1_2025_QualifyingResults.csv",
    "sprint_results": BASE_DIR / "data" / "F1_2025_SprintResults.csv",
    "sprint_qualifying": BASE_DIR / "data" / "F1_2025_SprintQualifyingResults.csv",
}

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"},
    },
    "handlers": {
        "default": {
            "level": "INFO",
            "formatter": "standard",
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "": {
            "handlers": ["default"],
            "level": "INFO",
            "propagate": False,
        }
    },
}
