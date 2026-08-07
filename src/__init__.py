"""
F1 Grand Prix Predictor - AI-powered Formula 1 race winner prediction system.
"""

__version__ = "1.0.0"
__author__ = "F1 Predictor Developer"
__email__ = "your.email@example.com"
__description__ = "AI-powered Formula 1 Grand Prix winner prediction using historical data, current intelligence, and weather forecasting"

# Import main components for easy access
from .predictor.gp_predictor import GPPredictor
from .utils.circuit_mapping import CircuitMapper
from .utils.helpers import setup_logging

__all__ = ["GPPredictor", "CircuitMapper", "setup_logging"]
