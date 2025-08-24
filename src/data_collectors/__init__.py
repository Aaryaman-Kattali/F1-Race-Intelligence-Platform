"""
Data collection modules for F1 prediction system.

This package contains collectors for:
- FastF1 historical race data
- Perplexity AI current intelligence  
- OpenWeatherMap weather forecasts
"""

from .fastf1_collector import FastF1Collector
from .perplexity_agent import PerplexityAgent
from .weather_collector import WeatherCollector

__all__ = [
    "FastF1Collector",
    "PerplexityAgent", 
    "WeatherCollector"
]

# Version compatibility check
try:
    import fastf1
    FASTF1_AVAILABLE = True
    FASTF1_VERSION = fastf1.__version__
except ImportError:
    FASTF1_AVAILABLE = False
    FASTF1_VERSION = None

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# Data collector status
COLLECTOR_STATUS = {
    "fastf1": FASTF1_AVAILABLE,
    "requests": REQUESTS_AVAILABLE,
    "fastf1_version": FASTF1_VERSION
}
