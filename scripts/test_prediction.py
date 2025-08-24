#!/usr/bin/env python3
"""
Test F1 GP prediction system with known results.
"""

import sys
from pathlib import Path
import argparse
import json
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.predictor.gp_predictor import GPPredictor
from src.utils.helpers import setup_logging, calculate_prediction_accuracy
from src.utils.circuit_mapping import CircuitMapper

def main():
    parser = argparse.ArgumentParser(description='Test F1 GP prediction accuracy')
    parser.add_argument('--circuit', required=True, help='Circuit to test')
    parser.add_argument('--test-year', type=int, default=2024, help='Year to test against')
    parser.add_argument('--actual-winner', required=True, help='Actual race winner (3-letter code)')
    parser.add_argument('--log-level', default='INFO', help='Logging level')
    
    args = parser.parse_args()
    
    setup_logging(args.log_level)
    
    try:
        print(f"🧪 Testing F1 GP Predictor")
        print(f"Circuit: {args.circuit}")
        print(f"Test Year: {args.test_year}")
        print(f"Actual Winner: {args.actual_winner}")
        print("=" * 50)
        
        # Initialize predictor
        predictor = GPPredictor()
        
        # Make prediction
        prediction = predictor.predict_race_winner(args.circuit, args.test_year)
        
        if 'error' in prediction:
            print(f"❌ Prediction failed: {prediction['error']}")
            return 1
        
        # Create actual results structure
        actual_results = {
            'winner': args.actual_winner.upper(),
            'circuit': args.circuit,
            'year': args.test_year
        }
        
        # Calculate accuracy
        accuracy = calculate_prediction_accuracy(prediction, actual_results)
        
        # Display results
        print(f"\n📊 PREDICTION TEST RESULTS")
        print("=" * 50)
        
        top_predictions = prediction.get('top_predictions', [])
        if top_predictions:
            predicted_winner = top_predictions[0]['driver_code']
            predicted_prob = top_predictions[0]['win_probability']
            
            print(f"🎯 Predicted Winner: {predicted_winner} ({predicted_prob:.1%})")
            print(f"🏆 Actual Winner: {args.actual_winner}")
            
            if predicted_winner == args.actual_winner:
                print(f"✅ CORRECT PREDICTION! 🎉")
            else:
                print(f"❌ Incorrect prediction")
                
                # Check if actual winner was in top predictions
                actual_rank = None
                for i, pred in enumerate(top_predictions, 1):
                    if pred['driver_code'] == args.actual_winner:
                        actual_rank = i
                        break
                
                if actual_rank:
                    print(f"📈 Actual winner was ranked #{actual_rank} in predictions")
                else:
                    print(f"📉 Actual winner not in top 10 predictions")
        
        # Accuracy metrics
        print(f"\n📈 ACCURACY METRICS:")
        print(f"   Winner Predicted: {'✅ Yes' if accuracy.get('winner_predicted') else '❌ No'}")
        print(f"   Top 3 Accuracy: {'✅ Yes' if accuracy.get('top_3_accuracy') else '❌ No'}")
        print(f"   Top 5 Accuracy: {'✅ Yes' if accuracy.get('top_5_accuracy') else '❌ No'}")
        
        # Save test results
        test_results = {
            'test_info': {
                'circuit': args.circuit,
                'test_year': args.test_year,
                'actual_winner': args.actual_winner,
                'test_date': datetime.now().isoformat()
            },
            'prediction': prediction,
            'actual_results': actual_results,
            'accuracy_metrics': accuracy
        }
        
        # Save to file
        output_file = f"test_results_{args.circuit.lower().replace(' ', '_')}_{args.test_year}.json"
        output_path = Path("data/predictions") / output_file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(test_results, f, indent=2, default=str)
        
        print(f"\n💾 Test results saved to: {output_path}")
        
        return 0 if accuracy.get('winner_predicted') else 1
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
