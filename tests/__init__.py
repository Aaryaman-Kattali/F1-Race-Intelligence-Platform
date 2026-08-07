"""
Test package for F1 GP Predictor system.

Contains unit tests and integration tests for:
- Data collectors
- Processors
- Prediction engine
- Utility functions
"""

import unittest
import sys
from pathlib import Path

# Add project root to path for testing
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_all_tests():
    """Run all test suites."""
    loader = unittest.TestLoader()
    suite = loader.discover(str(Path(__file__).parent), pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


def run_quick_tests():
    """Run quick smoke tests."""
    try:
        # Test imports
        from src.predictor.gp_predictor import GPPredictor
        from src.data_collectors.fastf1_collector import FastF1Collector
        from src.utils.circuit_mapping import CircuitMapper

        print("✅ All imports successful")

        # Test basic functionality
        mapper = CircuitMapper()
        circuits = mapper.list_available_circuits()
        print(f"✅ Circuit mapping working: {len(circuits)} circuits loaded")

        return True

    except Exception as e:
        print(f"❌ Quick test failed: {e}")
        return False


__all__ = ["run_all_tests", "run_quick_tests"]
