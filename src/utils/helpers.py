"""
General utility functions and helpers.
"""

import logging
import logging.config
from typing import Dict, Any, Optional
from datetime import datetime
import json
from pathlib import Path


def setup_logging(log_level: str = "INFO") -> None:
    """Setup logging configuration."""

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
            "simple": {"format": "%(levelname)s - %(message)s"},
        },
        "handlers": {
            "console": {
                "level": log_level,
                "formatter": "simple",
                "class": "logging.StreamHandler",
            },
            "file": {
                "level": "DEBUG",
                "formatter": "detailed",
                "class": "logging.FileHandler",
                "filename": "f1_predictor.log",
                "mode": "a",
            },
        },
        "loggers": {
            "": {"handlers": ["console"], "level": log_level, "propagate": False},
            "detailed": {
                "handlers": ["console", "file"],
                "level": "DEBUG",
                "propagate": False,
            },
        },
    }

    logging.config.dictConfig(logging_config)


def safe_get(data: Dict, key: str, default: Any = None) -> Any:
    """Safely get value from dictionary."""
    try:
        return data.get(key, default) if data else default
    except (AttributeError, TypeError):
        return default


def normalize_driver_name(name: str) -> str:
    """Normalize driver name to consistent format."""
    if not name:
        return ""

    # Common driver name mappings
    name_mappings = {
        "max verstappen": "VER",
        "lewis hamilton": "HAM",
        "charles leclerc": "LEC",
        "george russell": "RUS",
        "carlos sainz": "SAI",
        "lando norris": "NOR",
        "oscar piastri": "PIA",
        "fernando alonso": "ALO",
        "lance stroll": "STR",
        "sergio perez": "PER",
        "pierre gasly": "GAS",
        "esteban ocon": "OCO",
        "alexander albon": "ALB",
        "logan sargeant": "SAR",
        "kevin magnussen": "MAG",
        "nico hulkenberg": "HUL",
        "valtteri bottas": "BOT",
        "zhou guanyu": "ZHO",
        "yuki tsunoda": "TSU",
        "daniel ricciardo": "RIC",
    }

    name_lower = name.lower().strip()
    return name_mappings.get(name_lower, name.upper()[:3])


def format_probability(prob: float) -> str:
    """Format probability as percentage."""
    return f"{prob:.1%}"


def format_position(position: int) -> str:
    """Format position with ordinal suffix."""
    if position == 1:
        return "1st"
    elif position == 2:
        return "2nd"
    elif position == 3:
        return "3rd"
    else:
        return f"{position}th"


def save_prediction_result(prediction: Dict, output_path: Optional[Path] = None) -> str:
    """Save prediction result to JSON file."""
    try:
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            gp_name = prediction.get("race_info", {}).get("gp_name", "unknown")
            filename = f"{gp_name.lower().replace(' ', '_')}_{timestamp}.json"
            output_path = Path("data/predictions") / filename

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(prediction, f, indent=2, default=str)

        return str(output_path)

    except Exception as e:
        logging.error(f"Error saving prediction: {e}")
        return ""


def load_prediction_result(file_path: str) -> Optional[Dict]:
    """Load prediction result from JSON file."""
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading prediction: {e}")
        return None


def calculate_prediction_accuracy(predictions: Dict, actual_results: Dict) -> Dict:
    """Calculate accuracy metrics for predictions."""
    try:
        accuracy_metrics = {
            "winner_predicted": False,
            "top_3_accuracy": 0,
            "top_5_accuracy": 0,
            "mean_position_error": 0.0,
        }

        actual_winner = actual_results.get("winner")
        predicted_top = [
            p["driver_code"] for p in predictions.get("top_predictions", [])[:10]
        ]

        # Winner accuracy
        if predicted_top and predicted_top[0] == actual_winner:
            accuracy_metrics["winner_predicted"] = True

        # Top N accuracy
        if actual_winner:
            if actual_winner in predicted_top[:3]:
                accuracy_metrics["top_3_accuracy"] = 1
            if actual_winner in predicted_top[:5]:
                accuracy_metrics["top_5_accuracy"] = 1

        return accuracy_metrics

    except Exception as e:
        logging.error(f"Error calculating accuracy: {e}")
        return {}


def get_gpu_info() -> Dict:
    """Get GPU information for logging."""
    try:
        import cupy

        device = cupy.cuda.Device()
        props = cupy.cuda.runtime.getDeviceProperties(device.id)

        return {
            "gpu_available": True,
            "gpu_name": props["name"].decode("utf-8"),
            "gpu_memory": props["totalGlobalMem"] // (1024**2),  # MB
            "cuda_cores": props["multiProcessorCount"],
            "compute_capability": f"{props['major']}.{props['minor']}",
        }
    except Exception:
        return {"gpu_available": False}


class ProgressTracker:
    """Simple progress tracking utility."""

    def __init__(self, total_steps: int = 100):
        self.total_steps = total_steps
        self.current_step = 0
        self.start_time = datetime.now()

    def update(self, step: int = 1, message: str = ""):
        """Update progress."""
        self.current_step = min(self.current_step + step, self.total_steps)
        progress = (self.current_step / self.total_steps) * 100

        if message:
            print(f"⏳ {progress:.1f}% - {message}")

    def complete(self, message: str = "Complete"):
        """Mark as complete."""
        elapsed = datetime.now() - self.start_time
        print(f"✅ {message} (took {elapsed.total_seconds():.1f}s)")
