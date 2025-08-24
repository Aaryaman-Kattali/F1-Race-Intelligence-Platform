"""
Utility functions and helper modules for F1 prediction system.

This package contains:
- Circuit name mapping utilities
- General helper functions  
- Logging configuration
- Data validation tools
"""

from .circuit_mapping import CircuitMapper
from .helpers import (
    setup_logging,
    safe_get,
    normalize_driver_name,
    format_probability,
    format_position,
    save_prediction_result,
    load_prediction_result,
    calculate_prediction_accuracy,
    get_gpu_info,
    ProgressTracker
)

__all__ = [
    "CircuitMapper",
    "setup_logging",
    "safe_get", 
    "normalize_driver_name",
    "format_probability",
    "format_position",
    "save_prediction_result",
    "load_prediction_result", 
    "calculate_prediction_accuracy",
    "get_gpu_info",
    "ProgressTracker"
]

# Utility status
import sys
import logging

UTILS_STATUS = {
    "python_version": sys.version_info[:3],
    "logging_configured": len(logging.getLogger().handlers) > 0,
    "utilities_loaded": True
}

def get_system_info():
    """Get system information for debugging."""
    import platform
    
    return {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "utilities_status": UTILS_STATUS
    }
