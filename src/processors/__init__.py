"""
Data processing modules for feature engineering and data transformation.

This package contains processors for:
- Historical FastF1 data analysis
- Current season intelligence processing
- Feature engineering for ML models
"""

from .historical_processor import HistoricalProcessor
from .current_processor import CurrentProcessor
from .feature_engineer import FeatureEngineer

__all__ = ["HistoricalProcessor", "CurrentProcessor", "FeatureEngineer"]

# Processing capabilities
try:
    import pandas as pd
    import numpy as np

    PROCESSING_AVAILABLE = True
    PANDAS_VERSION = pd.__version__
    NUMPY_VERSION = np.__version__
except ImportError:
    PROCESSING_AVAILABLE = False
    PANDAS_VERSION = None
    NUMPY_VERSION = None

PROCESSOR_STATUS = {
    "processing_available": PROCESSING_AVAILABLE,
    "pandas_version": PANDAS_VERSION,
    "numpy_version": NUMPY_VERSION,
}
