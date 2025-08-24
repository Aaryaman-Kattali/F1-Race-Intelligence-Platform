from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import sys
from pathlib import Path
import os

# Add your project to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.predictor.gp_predictor import GPPredictor

app = Flask(__name__)
CORS(app)  # Allow React frontend to call API

predictor = GPPredictor()

@app.route('/')
def home():
    return jsonify({"message": "F1 Prediction API is running!"})

@app.route('/api/predict', methods=['POST'])
def predict_race():
    data = request.json
    gp_name = data.get('gp_name', '')
    
    try:
        print(f"🏁 API: Predicting for {gp_name}")
        prediction = predictor.predict_race_winner(gp_name)
        
        return jsonify({
            'success': True,
            'data': prediction
        })
    except Exception as e:
        print(f"❌ API Error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/circuits', methods=['GET'])
def get_circuits():
    circuits = predictor.circuit_mapper.list_available_circuits()
    return jsonify(circuits)

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'message': 'F1 Prediction API is running',
        'circuits_loaded': len(predictor.circuits),
        'active_drivers': len(predictor.active_drivers_2025)
    })

if __name__ == '__main__':
    print("🏎️ Starting F1 Prediction API...")
    print("📍 API will be available at: http://localhost:5000")
    print("🎯 Test endpoint: http://localhost:5000/api/health")
    app.run(debug=True, port=5000, host='0.0.0.0')
