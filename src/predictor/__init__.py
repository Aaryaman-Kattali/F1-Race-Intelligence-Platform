"""
Core prediction engine for F1 Grand Prix winner predictions.

This package contains:
- Main GPPredictor class
- Circuit-specific analysis tools
- Multi-method prediction algorithms
"""

from .gp_predictor import GPPredictor
from .circuit_analyzer import CircuitAnalyzer

__all__ = [
    "GPPredictor",
    "CircuitAnalyzer"
]

# GPU capability detection
try:
    import xgboost as xgb
    XGB_AVAILABLE = True
    XGB_VERSION = xgb.__version__
    
    # Test GPU availability
    try:
        import cupy
        GPU_AVAILABLE = True
        GPU_INFO = "NVIDIA GPU detected"
    except ImportError:
        GPU_AVAILABLE = False
        GPU_INFO = "CPU only"
        
except ImportError:
    XGB_AVAILABLE = False
    XGB_VERSION = None
    GPU_AVAILABLE = False
    GPU_INFO = "XGBoost not available"

PREDICTOR_STATUS = {
    "xgboost_available": XGB_AVAILABLE,
    "xgboost_version": XGB_VERSION,
    "gpu_available": GPU_AVAILABLE,
    "gpu_info": GPU_INFO
}

def get_predictor_info():
    """Get information about prediction capabilities."""
    return {
        "version": "1.0.0",
        "capabilities": PREDICTOR_STATUS,
        "supported_circuits": 24,
        "supported_years": "2018-2025"
    }
