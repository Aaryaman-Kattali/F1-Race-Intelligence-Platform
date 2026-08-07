#!/usr/bin/env python3
"""
Simplified F1 Grand Prix prediction script - Optimized for any GP circuit.
"""

import sys
import argparse
import logging
from typing import Dict
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.predictor.gp_predictor import GPPredictor
from src.utils.helpers import setup_logging, save_prediction_result
from src.utils.circuit_mapping import CircuitMapper


def main():
    """Simplified main function for any GP prediction."""

    parser = argparse.ArgumentParser(
        description="🏎️  Optimized F1 Grand Prix Prediction System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🚀 OPTIMIZED PREDICTION SYSTEM:
   • Uses local 2025 championship data
   • No redundant API calls for standings
   • Fast predictions for any GP circuit
   • Top 10 results with win percentages

Examples:
  python predict_gp.py "Hungarian Grand Prix"
  python predict_gp.py "Abu Dhabi Grand Prix"
  python predict_gp.py "Monaco Grand Prix" --save-results
        """,
    )

    parser.add_argument(
        "circuit",
        help='GP circuit name (e.g., "Hungarian Grand Prix", "Abu Dhabi Grand Prix", "Monaco Grand Prix")',
    )

    parser.add_argument(
        "--save-results",
        action="store_true",
        help="Save prediction results to JSON file",
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)",
    )

    parser.add_argument(
        "--list-circuits", action="store_true", help="List all available circuits"
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)

    try:
        # Handle list circuits request
        if args.list_circuits:
            circuit_mapper = CircuitMapper()
            circuits = circuit_mapper.list_available_circuits()

            print("\n🏁 Available F1 Circuits:")
            print("=" * 40)
            for i, circuit in enumerate(circuits, 1):
                print(f"{i:2d}. {circuit}")
            print(f"\nTotal: {len(circuits)} circuits available")
            return 0

        # Validate circuit input
        if not args.circuit:
            print("❌ Please specify a circuit name")
            print("Use --list-circuits to see available options")
            return 1

        # Initialize optimized predictor
        print("🚀 Initializing Optimized F1 Predictor...")
        predictor = GPPredictor()

        # Make prediction
        results = predictor.predict_race_winner(args.circuit)

        if "error" in results:
            print(f"\n❌ Prediction failed: {results['error']}")

            # Suggest similar circuits
            circuit_mapper = CircuitMapper()
            suggestions = circuit_mapper.suggest_circuit_name(args.circuit)

            if suggestions:
                print(f"\n💡 Did you mean one of these?")
                for suggestion in suggestions:
                    print(f"   • {suggestion}")

            return 1

        # Save results if requested
        if args.save_results:
            output_file = save_prediction_result(results)
            if output_file:
                print(f"\n💾 Results saved to: {output_file}")

        print(f"\n🎯 Prediction completed successfully!")
        return 0

    except KeyboardInterrupt:
        print(f"\n⚠️  Prediction cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"\n❌ Unexpected error occurred: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
