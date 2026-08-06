"""
Configuration package for F1 Race Intelligence Platform.

Contains:
- Settings and environment configuration
- Circuit characteristics database
- Dynamic standings loading with cache + fallback
"""

from .settings import (
    BASE_DIR,
    DATA_DIR,
    FASTF1_CACHE_DIR,
    PREDICTIONS_DIR,
    PROCESSED_DATA_DIR,
    CACHE_DIR,
    PERPLEXITY_API_KEY,
    OPENWEATHER_API_KEY,
    GOOGLE_API_KEY,
    GCP_PROJECT_ID,
    USE_GPU,
    CUDA_DEVICE,
    GPU_CONFIG,
    CURRENT_SEASON,
    HISTORICAL_YEARS,
    OFFLINE_MODE,
    ACTIVE_DRIVERS_2025,
    CURRENT_2025_STANDINGS,
    TEAM_RANKINGS_2025,
    DEFAULT_FEATURE_WEIGHTS,
    LOGGING_CONFIG,
    get_active_driver_codes,
    get_active_driver_info,
    is_rookie_driver_2025,
    get_2025_driver_performance,
)

__all__ = [
    "BASE_DIR",
    "DATA_DIR",
    "FASTF1_CACHE_DIR",
    "PREDICTIONS_DIR",
    "PROCESSED_DATA_DIR",
    "CACHE_DIR",
    "PERPLEXITY_API_KEY",
    "OPENWEATHER_API_KEY",
    "GOOGLE_API_KEY",
    "GCP_PROJECT_ID",
    "USE_GPU",
    "CUDA_DEVICE",
    "GPU_CONFIG",
    "CURRENT_SEASON",
    "HISTORICAL_YEARS",
    "OFFLINE_MODE",
    "ACTIVE_DRIVERS_2025",
    "CURRENT_2025_STANDINGS",
    "TEAM_RANKINGS_2025",
    "DEFAULT_FEATURE_WEIGHTS",
    "LOGGING_CONFIG",
    "get_active_driver_codes",
    "get_active_driver_info",
    "is_rookie_driver_2025",
    "get_2025_driver_performance",
]

# Configuration validation
import os
from pathlib import Path


def validate_config():
    """Validate configuration setup."""
    issues = []

    # Check required directories
    required_dirs = [DATA_DIR, FASTF1_CACHE_DIR, PREDICTIONS_DIR, PROCESSED_DATA_DIR]
    for dir_path in required_dirs:
        if not Path(dir_path).exists():
            issues.append(f"Directory missing: {dir_path}")

    # Check API keys
    if not PERPLEXITY_API_KEY:
        issues.append("PERPLEXITY_API_KEY not configured")

    if not OPENWEATHER_API_KEY:
        issues.append("OPENWEATHER_API_KEY not configured")

    # Check circuits.json
    circuits_file = BASE_DIR / "config" / "circuits.json"
    if not circuits_file.exists():
        issues.append("circuits.json file missing")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "gpu_enabled": USE_GPU,
        "current_season": CURRENT_SEASON,
        "offline_mode": OFFLINE_MODE,
    }


CONFIG_STATUS = validate_config()
