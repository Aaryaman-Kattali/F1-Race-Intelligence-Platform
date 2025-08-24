"""
Optimized F1 Grand Prix prediction engine - Removes redundant API calls.
"""

import json
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

from ..data_collectors.fastf1_collector import FastF1Collector
from ..data_collectors.perplexity_agent import PerplexityAgent
from ..data_collectors.weather_collector import WeatherCollector
from ..processors.feature_engineer import Enhanced2025FeatureEngineer
from ..utils.circuit_mapping import CircuitMapper
from config.settings import (
    BASE_DIR, DEFAULT_FEATURE_WEIGHTS, GPU_CONFIG, USE_GPU,
    ACTIVE_DRIVERS_2025, get_active_driver_codes, CURRENT_2025_STANDINGS
)

logger = logging.getLogger(__name__)

class GPPredictor:
    """Optimized F1 prediction engine using local 2025 data."""
    
    def __init__(self):
        self.fastf1_collector = FastF1Collector()
        self.perplexity_agent = PerplexityAgent()  # Only for race weekend data
        self.weather_collector = WeatherCollector()
        self.feature_engineer = Enhanced2025FeatureEngineer()
        self.circuit_mapper = CircuitMapper()
        
        self.circuits = self._load_circuit_configs()
        self.use_gpu = USE_GPU
        self.gpu_config = GPU_CONFIG
        self.active_drivers_2025 = set(get_active_driver_codes())
        
        logger.info(f"🏎️  Optimized GP Predictor initialized")
        logger.info(f"   - Local 2025 standings: ✅")
        logger.info(f"   - Active drivers: {len(self.active_drivers_2025)}")
        logger.info(f"   - Redundant API calls: ❌ (Removed)")
    
    def predict_race_winner(self, gp_name: str, year: int = 2025) -> Dict:
        """
        Optimized race prediction using local standings data.
        """
        try:
            logger.info(f"\n🏁 Starting OPTIMIZED prediction for {gp_name} {year}")
            print(f"\n{'='*60}")
            print(f"🏎️  OPTIMIZED F1 PREDICTION: {gp_name.upper()} {year}")
            print(f"{'='*60}")
            
            # Step 1: Circuit validation
            circuit_key = self.circuit_mapper.get_circuit_key(gp_name)
            if not circuit_key:
                logger.error(f"❌ Circuit not found: {gp_name}")
                return {'error': f'Circuit not found: {gp_name}'}
            
            circuit_config = self.circuits.get(circuit_key, {})
            print(f"📍 Circuit: {circuit_config.get('official_names', [gp_name])[0]}")
            print(f"🏁 Type: {circuit_config.get('circuit_type', 'unknown').replace('_', ' ').title()}")
            
            # Step 2: Historical data (filtered to 2025 active drivers)
            print(f"\n🔍 Collecting historical data (2025 active drivers only)...")
            historical_data = self.fastf1_collector.get_circuit_historical_data(gp_name)
            filtered_historical = self._filter_historical_data(historical_data)
            
            active_driver_count = sum(len(race.get('drivers', {})) for race in filtered_historical)
            print(f"✅ Historical data: {len(filtered_historical)} races, {active_driver_count} driver entries (2025 active only)")
            
            # Step 3: Use LOCAL standings instead of API calls
            print(f"\n📊 Using LOCAL 2025 championship standings...")
            current_intelligence = self._create_local_intelligence(gp_name)
            print(f"✅ Local standings loaded: {len(current_intelligence['driver_standings']['drivers'])} drivers")
            
            # Step 4: Weather data
            print(f"\n🌤️  Getting weather forecast...")
            weather_data = self.weather_collector.get_race_weekend_weather(circuit_config)
            
            if weather_data.get('current_weather', {}).get('available'):
                current_temp = weather_data['current_weather']['temperature']
                print(f"✅ Weather data available (Current: {current_temp:.1f}°C)")
                
                race_analysis = weather_data.get('race_weekend_analysis', {})
                if race_analysis.get('race_day_conditions'):
                    race_temp = race_analysis['race_day_conditions'].get('temperature', 0)
                    rain_prob = race_analysis['race_day_conditions'].get('rain_probability', 0)
                    print(f"🏁 Race forecast: {race_temp:.1f}°C, {rain_prob:.0f}% rain chance")
            else:
                print(f"⚠️  Using fallback weather data")
            
            # Step 5: Feature engineering with LOCAL data
            print(f"\n🔧 Engineering features with LOCAL 2025 data...")
            features = self.feature_engineer.create_prediction_features(
                historical_data=filtered_historical,
                current_intelligence=current_intelligence,
                weather_data=weather_data,
                circuit_config=circuit_config
            )
            
            if features.empty:
                logger.error("❌ Could not create prediction features")
                return {'error': 'Could not create prediction features'}
            
            # Show driver breakdown
            rookies = len([idx for idx in features.index if features.loc[idx, 'is_rookie_2025']])
            experienced = len(features) - rookies
            print(f"✅ Features created: {experienced} experienced + {rookies} rookie drivers")
            
            # Step 6: Generate predictions
            print(f"\n🎯 Generating optimized predictions...")
            predictions = self._make_optimized_predictions(
                features=features,
                circuit_config=circuit_config,
                historical_data=filtered_historical,
                weather_data=weather_data
            )
            
            # Step 7: Add metadata
            predictions.update({
                'race_info': {
                    'gp_name': gp_name,
                    'year': year,
                    'circuit_key': circuit_key,
                    'circuit_type': circuit_config.get('circuit_type'),
                    'prediction_date': datetime.now().isoformat(),
                    'optimized_prediction': True
                },
                'data_sources': {
                    'historical_races': len(filtered_historical),
                    'local_standings_used': True,
                    'redundant_api_calls': False,
                    'weather_available': weather_data.get('current_weather', {}).get('available', False),
                    'features_engineered': len(features)
                },
                'driver_breakdown': {
                    'experienced_drivers': experienced,
                    'rookie_drivers_2025': rookies,
                    'total_active_drivers': len(features)
                }
            })
            
            # Display results
            self._display_optimized_results(predictions)
            
            return predictions
            
        except Exception as e:
            logger.error(f"❌ Optimized prediction failed: {e}")
            return {'error': f'Optimized prediction failed: {str(e)}'}
    
    def _create_local_intelligence(self, gp_name: str) -> Dict:
        """Create intelligence data using official F1.com + local standings."""
        
        # Convert local standings to intelligence format
        drivers_data = []
        for driver_code, data in CURRENT_2025_STANDINGS.items():
            drivers_data.append({
                'code': driver_code,
                'name': next((d['name'] for d in ACTIVE_DRIVERS_2025 if d['code'] == driver_code), 'Unknown'),
                'position': data['position'],
                'points': data['points'],
                'team': data['team']
            })
        
        drivers_data.sort(key=lambda x: x['position'])
        
        # Get race weekend data using official F1.com collector
        race_weekend_data = {}
        try:
            print(f"🔍 Getting official race weekend data for {gp_name}...")
            
            from ..data_collectors.formula1_web_collector import Formula1WebCollector
            f1_collector = Formula1WebCollector()
            
            # Get qualifying data (most important for predictions)
            qualifying_data = f1_collector.get_qualifying_data(gp_name)
            
            if qualifying_data.get('available'):
                race_weekend_data = {
                    'weekend_data_available': True,
                    'data_source': 'official_f1_website',
                    'sessions': {
                        'Qualifying': qualifying_data,
                        'FP1': f1_collector.get_practice_1_data(gp_name),
                        'FP2': f1_collector.get_practice_2_data(gp_name),
                        'FP3': f1_collector.get_practice_3_data(gp_name)
                    }
                }
                print(f"✅ Official data retrieved - Pole: {qualifying_data.get('pole_position', 'Unknown')}")
            else:
                print(f"⚠️  No official qualifying data available for {gp_name}")
                
        except Exception as e:
            logger.warning(f"Official F1.com data unavailable: {e}")
            race_weekend_data = {}
        
        return {
            'driver_standings': {
                'standings_available': True,
                'drivers': drivers_data
            },
            'team_standings': {
                'standings_available': True,
                'constructors': self._get_constructor_standings()
            },
            'race_weekend_data': race_weekend_data,
            'standings_source': 'local_settings_plus_official_f1'
        }
    
    def _get_constructor_standings(self) -> List[Dict]:
        """Generate constructor standings from driver standings."""
        team_points = {}
        
        for driver_code, data in CURRENT_2025_STANDINGS.items():
            team = data['team']
            points = data['points']
            
            if team not in team_points:
                team_points[team] = 0
            team_points[team] += points
        
        # Convert to list and sort
        constructors = [{'team': team, 'points': points} for team, points in team_points.items()]
        constructors.sort(key=lambda x: x['points'], reverse=True)
        
        return constructors
    
    def _filter_historical_data(self, historical_data: List[Dict]) -> List[Dict]:
        """Filter historical data to only include 2025 active drivers."""
        filtered_data = []
        
        for race in historical_data:
            filtered_race = race.copy()
            original_drivers = race.get('drivers', {})
            
            # Only keep 2025 active drivers
            filtered_drivers = {
                driver_code: driver_data 
                for driver_code, driver_data in original_drivers.items()
                if driver_code in self.active_drivers_2025
            }
            
            filtered_race['drivers'] = filtered_drivers
            
            # Update race winner if not active in 2025
            race_winner = race.get('race_winner')
            if race_winner and race_winner not in self.active_drivers_2025:
                # Find highest finishing active driver
                active_finishers = [
                    (driver_code, driver_data.get('race_position', 99))
                    for driver_code, driver_data in filtered_drivers.items()
                    if driver_data.get('race_position', 99) < 99
                ]
                if active_finishers:
                    active_finishers.sort(key=lambda x: x[1])
                    filtered_race['race_winner'] = active_finishers[0][0]
            
            filtered_data.append(filtered_race)
        
        return filtered_data
    
    def _make_optimized_predictions(self, features: pd.DataFrame, circuit_config: Dict, 
                                   historical_data: List[Dict], weather_data: Dict) -> Dict:
        """Generate optimized predictions using local data."""
        
        # Enhanced prediction using local data
        predictions = self._local_data_prediction(features, circuit_config)
        
        # Pattern matching with active drivers
        pattern_predictions = self._pattern_matching_prediction(features, historical_data, circuit_config)
        
        # Combine predictions
        final_predictions = self._combine_predictions(predictions, pattern_predictions)
        
        # Create results
        results = {
            'predictions': {},
            'top_predictions': [],
            'model_confidence': 0.0,
            'circuit_analysis': self._analyze_circuit_factors(circuit_config, weather_data)
        }
        
        # Process predictions
        for i, (driver_code, prob) in enumerate(final_predictions.items()):
            driver_features = features.loc[driver_code] if driver_code in features.index else {}
            real_perf = CURRENT_2025_STANDINGS.get(driver_code, {})
            
            results['predictions'][driver_code] = {
                'win_probability': float(prob * 100),  # Convert to percentage
                'rank': i + 1,
                'driver_name': driver_features.get('driver_name', 'Unknown'),
                'team_2025': driver_features.get('team_2025', 'Unknown'),
                'championship_position': real_perf.get('position', 20),
                'championship_points': real_perf.get('points', 0),
                'is_rookie_2025': driver_features.get('is_rookie_2025', False)
            }
        
        # Get top 10 predictions
        sorted_preds = sorted(results['predictions'].items(), 
                            key=lambda x: x[1]['win_probability'], reverse=True)
        
        results['top_predictions'] = [
            {
                'driver_code': driver,
                'driver_name': pred['driver_name'],
                'team': pred['team_2025'],
                'win_probability': pred['win_probability'],
                'rank': pred['rank'],
                'championship_position': pred['championship_position'],
                'is_rookie': pred['is_rookie_2025']
            }
            for driver, pred in sorted_preds[:10]
        ]
        
        # Calculate model confidence
        top_prob = sorted_preds[0][1]['win_probability'] if sorted_preds else 0
        second_prob = sorted_preds[1][1]['win_probability'] if len(sorted_preds) > 1 else 0
        results['model_confidence'] = float(top_prob - second_prob)
        
        return results
    
    def _local_data_prediction(self, features: pd.DataFrame, circuit_config: Dict) -> Dict:
        """Balanced prediction that doesn't over-favor pole position."""
        predictions = {}
        qualifying_importance = circuit_config.get('qualifying_importance', 0.7)
        
        for driver_code in features.index:
            driver_features = features.loc[driver_code]
            
            # Base championship form score (higher weight)
            real_perf = CURRENT_2025_STANDINGS.get(driver_code, {'position': 20, 'points': 0})
            champ_pos = real_perf['position']
            form_score = (21 - champ_pos) / 20.0
            
            # Historical performance
            hist_score = (21 - driver_features.get('historical_avg_position', 15)) / 20.0
            
            # Qualifying position boost (balanced)
            grid_pos = driver_features.get('grid_position', 20)
            qualifying_boost = self._calculate_qualifying_boost(grid_pos, qualifying_importance, driver_code)
            
            # Circuit and team advantages
            circuit_advantage = driver_features.get('circuit_type_advantage', 0.0)
            team_advantage = self._calculate_team_advantage(driver_features.get('current_team_2025', 'Unknown'))
            
            # BALANCED WEIGHTING - championship form still matters most
            total_score = (
                form_score * 0.4 +           # Championship form (40%)
                hist_score * 0.2 +           # Historical performance (20%)
                qualifying_boost * 0.25 +    # Qualifying advantage (25%)
                circuit_advantage * 0.1 +    # Circuit advantages (10%)
                team_advantage * 0.05        # Team performance (5%)
            )
            
            # Rookie penalty
            if driver_features.get('is_rookie_2025', False):
                total_score *= 0.85
            
            predictions[driver_code] = max(0.01, min(0.95, total_score))
        
        # Normalize
        total = sum(predictions.values())
        if total > 0:
            predictions = {k: v/total for k, v in predictions.items()}
        
        return predictions
    
    def _calculate_qualifying_boost(self, grid_pos: int, quali_importance: float, driver_code: str) -> float:
        """Balanced qualifying boost - pole gives advantage but doesn't guarantee win."""
        if grid_pos == 1:  # POLE POSITION
            # Balanced pole advantage (not overwhelming)
            boost = quali_importance * 0.4  # Reduced from 0.8 to 0.4
            logger.info(f"🏁 {driver_code} POLE POSITION BOOST: {boost:.3f}")
            return boost
        elif grid_pos == 2:  # Front row
            return quali_importance * 0.25
        elif grid_pos == 3:  # Second row
            return quali_importance * 0.15
        elif grid_pos <= 5:  # Top 5
            return quali_importance * 0.10
        elif grid_pos <= 10:  # Points positions
            return quali_importance * 0.05
        else:
            return 0.0
    
    def _calculate_team_advantage(self, team_name: str) -> float:
        """Calculate team performance advantage based on 2025 constructor standings."""
        
        # Based on 2025 constructor standings from your local data
        team_performance = {
            "McLaren": 0.25,        # Leading constructors (559 points combined)
            "Ferrari": 0.20,        # Strong second (260 points combined)
            "Mercedes": 0.18,       # Competitive (236 points combined)
            "Red Bull Racing": 0.12, # Struggling in 2025 (197 points combined)
            "Red Bull": 0.12,       # Handle both name variations
            "Williams": 0.08,       # Improved midfield (70 points)
            "Racing Bulls": 0.06,   # Midfield (42 points)
            "Haas": 0.05,          # Lower midfield (35 points)
            "Aston Martin": 0.04,   # Disappointing 2025 (52 points)
            "Alpine": 0.03,         # Struggling (20 points)
            "Kick Sauber": 0.02     # Backmarkers (51 points)
        }
        
        # Clean team name variations
        cleaned_team = team_name.replace("Racing", "").strip()
        
        advantage = team_performance.get(team_name, team_performance.get(cleaned_team, 0.01))
        
        logger.debug(f"🏁 {team_name} team advantage: {advantage:.3f}")
        return advantage
    
    def _pattern_matching_prediction(self, features: pd.DataFrame, historical_data: List[Dict], 
                                   circuit_config: Dict) -> Optional[Dict]:
        """Pattern matching with active drivers."""
        if len(historical_data) < 3:
            return None
        
        winner_patterns = {}
        for race in historical_data:
            winner = race.get('race_winner')
            if winner and winner in self.active_drivers_2025:
                winner_patterns[winner] = winner_patterns.get(winner, 0) + 1
        
        predictions = {}
        for driver_code in features.index:
            base_score = 0.5
            
            if driver_code in winner_patterns:
                winner_bonus = winner_patterns[driver_code] / len(historical_data)
                base_score += winner_bonus * 0.3
            
            form_multiplier = features.loc[driver_code].get('current_form_score', 0.5)
            final_score = base_score * (0.5 + form_multiplier)
            
            predictions[driver_code] = max(0.01, min(0.99, final_score))
        
        total = sum(predictions.values())
        if total > 0:
            predictions = {k: v/total for k, v in predictions.items()}
        
        return predictions
    
    def _calculate_circuit_advantage(self, driver_code: str, circuit_config: Dict, features: Dict) -> float:
        """Calculate circuit-specific advantages using official 2025 GP names."""
        advantage = 0.0
        circuit_type = circuit_config.get('circuit_type', 'mixed')
        
        # Circuit type specialists
        specialists = {
            'street_circuit': ['HAM', 'LEC', 'VER', 'RUS', 'PIA'],  # Monaco, Singapore, Miami, etc.
            'high_speed': ['VER', 'LEC', 'NOR', 'SAI', 'PIA'],      # Monza, Spa, Silverstone, etc.
            'technical': ['HAM', 'ALO', 'VER', 'LEC', 'RUS'],       # Hungary, Zandvoort, Suzuka, etc.
            'mixed': ['VER', 'HAM', 'PIA', 'NOR', 'LEC']            # Most modern circuits
        }
        
        if driver_code in specialists.get(circuit_type, []):
            advantage += 0.15
        
        # HOME ADVANTAGE - Updated for 2025 official GP names
        home_advantages = {
            'australian_gp': ['PIA'],           # Oscar Piastri's home
            'dutch_gp': ['VER'],                # Max Verstappen's home
            'british_gp': ['HAM', 'RUS'],       # British drivers
            'spanish_gp': ['ALO', 'SAI'],       # Spanish drivers
            'monaco_gp': ['LEC'],               # Leclerc's "home"
            'italian_gp': ['LEC'],              # Ferrari's home
            'canadian_gp': ['STR'],             # Lance Stroll
            'united_states_gp': [],             # No current American drivers
            'mexico_city_gp': [],               # No current Mexican drivers
            'sao_paulo_gp': [],                 # No current Brazilian drivers
            'austrian_gp': [],                  # No current Austrian drivers (Red Bull team)
            'japanese_gp': ['TSU'],             # Yuki Tsunoda
            'chinese_gp': [],                   # No current Chinese drivers
            'bahrain_gp': [],                   # No current Bahraini drivers
            'saudi_arabian_gp': [],             # No current Saudi drivers
            'miami_gp': [],                     # No current American drivers
            'emilia_romagna_gp': [],            # Italian circuit but already covered by Italian GP
            'belgian_gp': [],                   # No current Belgian drivers
            'hungarian_gp': [],                 # No current Hungarian drivers
            'azerbaijan_gp': [],                # No current Azerbaijani drivers
            'singapore_gp': [],                 # No current Singaporean drivers
            'las_vegas_gp': [],                 # No current American drivers
            'qatar_gp': [],                     # No current Qatari drivers
            'abu_dhabi_gp': []                  # No current Emirati drivers
        }
        
        circuit_key = circuit_config.get('circuit_key', '')
        home_drivers = home_advantages.get(circuit_key, [])
        
        if driver_code in home_drivers:
            advantage += 0.2
            logger.info(f"🏠 {driver_code} gets HOME ADVANTAGE at {circuit_key}")
        
        # Historical winners bonus
        hist_winner_bonus = features.get('historical_winner_bonus', 0.0)
        advantage += hist_winner_bonus
        
        return min(advantage, 0.4)  # Cap at 40%
    
    def _combine_predictions(self, local_pred: Dict, pattern_pred: Optional[Dict]) -> Dict:
        """Combine prediction methods."""
        combined = {}
        
        for driver_code in local_pred.keys():
            score = local_pred[driver_code] * 0.7  # Local data gets 70% weight
            
            if pattern_pred and driver_code in pattern_pred:
                score += pattern_pred[driver_code] * 0.3  # Pattern gets 30% weight
            
            combined[driver_code] = score
        
        # Sort by probability
        return dict(sorted(combined.items(), key=lambda x: x[1], reverse=True))
    
    def _analyze_circuit_factors(self, circuit_config: Dict, weather_data: Dict) -> Dict:
        """Circuit analysis for optimization."""
        analysis = {
            'key_success_factors': circuit_config.get('key_factors', []),
            'overtaking_difficulty': circuit_config.get('overtaking_difficulty', 'medium'),
            'qualifying_importance': f"{circuit_config.get('qualifying_importance', 0.7)*100:.0f}%",
            'weather_impact': 'normal'
        }
        
        # Weather analysis
        race_conditions = weather_data.get('race_weekend_analysis', {}).get('race_day_conditions', {})
        if race_conditions:
            weather_impact = race_conditions.get('weather_impact', 'normal_conditions')
            
            impact_map = {
                'high_rain_impact': 'High - Rain favors experienced drivers',
                'medium_rain_risk': 'Medium - Mixed conditions possible',
                'normal_conditions': 'Low - Normal racing conditions',
                'extreme_heat': 'High - Extreme heat impact',
                'high_heat_impact': 'Medium - High temperature impact',
                'cold_conditions': 'Medium - Cold weather challenges'
            }
            
            analysis['weather_impact'] = impact_map.get(weather_impact, 'Normal')
        
        return analysis
    
    def _display_optimized_results(self, predictions: Dict):
        """Display optimized prediction results."""
        
        print(f"\n🏆 OPTIMIZED RACE PREDICTION")
        print(f"{'='*60}")
        
        # Championship context
        leader = next((d for d in predictions['top_predictions'] if d['championship_position'] == 1), {})
        if leader:
            print(f"\n🏆 2025 Championship Leader: {leader.get('driver_name', 'Unknown')} ({leader.get('team', 'Unknown')})")
        
        # Top 10 predictions with percentages
        print(f"\n🥇 TOP 10 RACE PREDICTIONS:")
        for i, pred in enumerate(predictions['top_predictions'][:10], 1):
            emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i:2d}."
            
            name = pred['driver_name'][:15].ljust(15)
            team = pred['team'][:8].ljust(8)
            prob = pred['win_probability']
            champ_pos = pred['championship_position']
            rookie_flag = "🆕" if pred['is_rookie'] else "📈"
            
            print(f"   {emoji} {pred['driver_code']} {name} ({team}) - {prob:.1f}% {rookie_flag} [P{champ_pos}]")
        
        # Model confidence
        confidence = predictions.get('model_confidence', 0)
        confidence_level = "High" if confidence > 3.0 else "Medium" if confidence > 1.5 else "Low"
        print(f"\n📊 Model Confidence: {confidence_level} ({confidence:.1f}% separation)")
        
        # Data sources
        data_sources = predictions.get('data_sources', {})
        print(f"\n📡 Optimized Data Sources:")
        print(f"   Historical Races (2025 drivers only): {data_sources.get('historical_races', 0)}")
        print(f"   Local 2025 Championship Data: ✅")
        print(f"   Redundant API Calls Removed: ✅")
        
        # Circuit analysis
        circuit_analysis = predictions.get('circuit_analysis', {})
        print(f"\n🏁 Circuit Analysis:")
        print(f"   Key Factors: {', '.join(circuit_analysis.get('key_success_factors', []))}")
        print(f"   Qualifying Importance: {circuit_analysis.get('qualifying_importance', 'Unknown')}")
        print(f"   Weather Impact: {circuit_analysis.get('weather_impact', 'Unknown')}")
        
        print(f"\n{'='*60}")
        
        print(f"\n🎯 Prediction completed successfully!")
    
    def _load_circuit_configs(self) -> Dict:
        """Load circuit configurations."""
        try:
            config_path = BASE_DIR / "config" / "circuits.json"
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading circuit configs: {e}")
            return {}
    
    def _integrate_real_qualifying_data(self, features: pd.DataFrame, current_intelligence: Dict) -> pd.DataFrame:
        """Integrate real qualifying data from official F1.com data."""
        
        # Get race weekend data
        race_weekend = current_intelligence.get('race_weekend_data', {})
        sessions = race_weekend.get('sessions', {})
        qualifying_session = sessions.get('Qualifying', {})
        
        if qualifying_session.get('available') and qualifying_session.get('results'):
            logger.info("🏁 Integrating official qualifying results...")
            
            # Parse qualifying results
            for result in qualifying_session['results']:
                driver_code = result.get('driver_code', '')
                position = result.get('position', 20)
                
                if driver_code and driver_code in features.index:
                    features.loc[driver_code, 'grid_position'] = position
                    
                    if position == 1:
                        logger.info(f"🏁 {driver_code} has POLE POSITION")
                    
                    logger.debug(f"🏁 {driver_code} qualifies P{position}")
        
        return features
