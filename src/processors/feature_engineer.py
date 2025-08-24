"""
Enhanced Feature engineering for F1 GP predictions - 2025 Real Data Integration.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging
from datetime import datetime

# Import 2025 actual data configuration
from config.settings import (
    ACTIVE_DRIVERS_2025, get_active_driver_codes, is_rookie_driver_2025,
    get_2025_driver_performance, CURRENT_2025_STANDINGS, TEAM_RANKINGS_2025,
    F1_2025_DATA_FILES
)

logger = logging.getLogger(__name__)

class Enhanced2025FeatureEngineer:
    """Feature engineer using REAL 2025 F1 season data."""
    
    def __init__(self):
        self.feature_columns = []
        self.active_driver_codes = set(get_active_driver_codes())
        self.season_2025_data = {}
        self._load_2025_season_data()
        logger.info(f"🏎️  Initialized with REAL 2025 data for {len(self.active_driver_codes)} drivers")
    
    def _load_2025_season_data(self):
        """Load all 2025 season data from CSV files."""
        try:
            # Load race results
            if F1_2025_DATA_FILES['race_results'].exists():
                race_df = pd.read_csv(F1_2025_DATA_FILES['race_results'])
                self.season_2025_data['races'] = race_df
                logger.info(f"✅ Loaded {len(race_df)} race results from 2025 season")
            
            # Load qualifying results
            if F1_2025_DATA_FILES['qualifying_results'].exists():
                quali_df = pd.read_csv(F1_2025_DATA_FILES['qualifying_results'])
                self.season_2025_data['qualifying'] = quali_df
                logger.info(f"✅ Loaded {len(quali_df)} qualifying results from 2025 season")
            
            # Load sprint data
            if F1_2025_DATA_FILES['sprint_results'].exists():
                sprint_df = pd.read_csv(F1_2025_DATA_FILES['sprint_results'])
                self.season_2025_data['sprints'] = sprint_df
                logger.info(f"✅ Loaded {len(sprint_df)} sprint results from 2025 season")
                
            # Load sprint qualifying
            if F1_2025_DATA_FILES['sprint_qualifying'].exists():
                sprint_quali_df = pd.read_csv(F1_2025_DATA_FILES['sprint_qualifying'])
                self.season_2025_data['sprint_qualifying'] = sprint_quali_df
                logger.info(f"✅ Loaded {len(sprint_quali_df)} sprint qualifying results from 2025 season")
                
        except Exception as e:
            logger.error(f"Error loading 2025 season data: {e}")
            self.season_2025_data = {}
    
    def create_prediction_features(self, historical_data: List[Dict], current_intelligence: Dict,
                                 weather_data: Dict, circuit_config: Dict) -> pd.DataFrame:
        """
        Create features using REAL 2025 season data + filtered historical data.
        """
        try:
            logger.info("🔧 Engineering features with REAL 2025 season data...")
            
            # Filter historical data to ONLY include current active drivers
            filtered_historical_data = self._filter_historical_to_active_drivers(historical_data)
            
            # Create features for ONLY active 2025 drivers
            features_data = []
            
            for driver_code in self.active_driver_codes:
                driver_features = self._create_driver_features_real_2025(
                    driver_code=driver_code,
                    historical_data=filtered_historical_data,
                    current_intelligence=current_intelligence,
                    weather_data=weather_data,
                    circuit_config=circuit_config
                )
                
                if driver_features:
                    driver_features['driver_code'] = driver_code
                    # Add driver metadata
                    driver_info = next((d for d in ACTIVE_DRIVERS_2025 if d['code'] == driver_code), {})
                    driver_features['driver_name'] = driver_info.get('name', 'Unknown')
                    driver_features['team_2025'] = driver_info.get('team', 'Unknown')
                    driver_features['is_rookie_2025'] = is_rookie_driver_2025(driver_code)
                    features_data.append(driver_features)
            
            if not features_data:
                logger.error("No valid features created for active 2025 drivers")
                return pd.DataFrame()
            
            # Create DataFrame
            features_df = pd.DataFrame(features_data)
            features_df = features_df.set_index('driver_code')
            
            # Store feature columns
            self.feature_columns = list(features_df.columns)
            
            # Log driver categories
            experienced_drivers = len([f for f in features_data if not f['is_rookie_2025']])
            rookie_drivers = len([f for f in features_data if f['is_rookie_2025']])
            
            logger.info(f"✅ Created {len(features_df)} driver features with REAL 2025 data")
            logger.info(f"   - {experienced_drivers} experienced drivers (historical + 2025 data)")
            logger.info(f"   - {rookie_drivers} rookies (2025 season data only)")
            
            return features_df
            
        except Exception as e:
            logger.error(f"Error creating features with 2025 data: {e}")
            return pd.DataFrame()
    
    def _filter_historical_to_active_drivers(self, historical_data: List[Dict]) -> List[Dict]:
        """Filter historical data to include ONLY drivers active in 2025."""
        filtered_data = []
        
        for race in historical_data:
            filtered_race = race.copy()
            original_drivers = race.get('drivers', {})
            
            # Only keep drivers who are active in 2025
            filtered_drivers = {
                driver_code: driver_data 
                for driver_code, driver_data in original_drivers.items()
                if driver_code in self.active_driver_codes
            }
            
            filtered_race['drivers'] = filtered_drivers
            
            # Update race winner if they're not active in 2025
            race_winner = race.get('race_winner')
            if race_winner and race_winner not in self.active_driver_codes:
                # Find the highest finishing active driver
                active_finishers = [
                    (driver_code, driver_data.get('race_position', 99))
                    for driver_code, driver_data in filtered_drivers.items()
                    if driver_data.get('race_position', 99) < 99
                ]
                if active_finishers:
                    active_finishers.sort(key=lambda x: x[1])
                    filtered_race['race_winner'] = active_finishers[0][0]
                else:
                    filtered_race['race_winner'] = None
            
            filtered_data.append(filtered_race)
        
        logger.info(f"🔍 Historical data filtered to 2025 active drivers only")
        return filtered_data
    
    def _create_driver_features_real_2025(self, driver_code: str, historical_data: List[Dict],
                                        current_intelligence: Dict, weather_data: Dict, 
                                        circuit_config: Dict) -> Optional[Dict]:
        """Create features using REAL 2025 season data."""
        try:
            features = {}
            
            # Check if this is a rookie driver
            is_rookie = is_rookie_driver_2025(driver_code)
            
            if is_rookie:
                logger.debug(f"🆕 Processing rookie: {driver_code} (2025 data only)")
                # Rookies: Use REAL 2025 season performance
                hist_features = self._create_rookie_features_from_2025_data(driver_code)
            else:
                logger.debug(f"📈 Processing experienced driver: {driver_code} (historical + real 2025)")
                # Experienced: Use filtered historical + real 2025 performance
                hist_features = self._create_historical_features(driver_code, historical_data, circuit_config)
            
            features.update(hist_features)
            
            # REAL 2025 current form features
            current_features = self._create_real_2025_form_features(driver_code)
            features.update(current_features)
            
            # Qualifying features (from current intelligence + real 2025 quali data)
            qualifying_features = self._create_qualifying_features_real_2025(
                driver_code, current_intelligence, circuit_config)
            features.update(qualifying_features)
            
            # Weather adaptation features
            weather_features = self._create_weather_features(driver_code, weather_data, circuit_config)
            features.update(weather_features)
            
            # Circuit-specific features
            circuit_features = self._create_circuit_features(driver_code, circuit_config, historical_data)
            features.update(circuit_features)
            
            # Expected performance features
            expected_features = self._create_expected_performance_features(
                driver_code, features, circuit_config, is_rookie)
            features.update(expected_features)
            
            return features
            
        except Exception as e:
            logger.debug(f"Error creating features for {driver_code}: {e}")
            return None
    
    def _create_rookie_features_from_2025_data(self, driver_code: str) -> Dict:
        """Create features for rookies using their REAL 2025 performance."""
        features = {}
        
        # Get real 2025 performance data
        driver_perf = get_2025_driver_performance(driver_code)
        current_position = driver_perf['position']
        current_points = driver_perf['points']
        
        # Calculate average finish from real 2025 race data
        race_finishes = []
        if 'races' in self.season_2025_data:
            driver_races = self.season_2025_data['races'][
                self.season_2025_data['races']['Driver'].str.contains(driver_code, na=False) |
                self.season_2025_data['races']['No'].astype(str) == str(self._get_driver_number(driver_code))
            ]
            
            for _, race in driver_races.iterrows():
                if pd.notna(race['Position']) and race['Position'] != 'NC' and race['Position'] != 'DQ':
                    try:
                        position = int(race['Position'])
                        race_finishes.append(position)
                    except:
                        continue
        
        # Set features based on REAL 2025 performance
        if race_finishes:
            avg_finish = np.mean(race_finishes)
            best_finish = min(race_finishes)
            consistency = 1.0 / (1.0 + np.std(race_finishes))
            points_rate = len([f for f in race_finishes if f <= 10]) / len(race_finishes)
            podium_rate = len([f for f in race_finishes if f <= 3]) / len(race_finishes)
        else:
            # Fallback to championship position
            avg_finish = min(current_position + 2, 20)  # Slight optimistic adjustment
            best_finish = max(1, current_position - 5)
            consistency = 0.5
            points_rate = 0.3 if current_points > 0 else 0.0
            podium_rate = 0.1 if current_position <= 10 else 0.0
        
        features.update({
            'historical_avg_position': avg_finish,
            'historical_best_position': best_finish,
            'historical_consistency': consistency,
            'historical_win_rate': 0.0,  # No wins yet as rookie
            'historical_podium_rate': podium_rate,
            'historical_points_rate': points_rate,
            'historical_quali_avg': min(avg_finish + 1, 20),
            'historical_quali_best': max(1, best_finish),
            'circuit_race_count': 0,  # First time at most circuits
            'circuit_experience': 0.0,
            'circuit_dnf_rate': 0.05,  # Small rookie risk
            'historical_total_points': current_points,
            'rookie_penalty': 0.15,  # Reduced penalty if performing well
            'real_2025_races': len(race_finishes)
        })
        
        logger.debug(f"🆕 Rookie {driver_code}: Real 2025 avg finish P{avg_finish:.1f}, {current_points} pts")
        return features
    
    def _create_real_2025_form_features(self, driver_code: str) -> Dict:
        """Create current form features using REAL 2025 championship data."""
        features = {}
        
        # Get real championship data
        driver_perf = get_2025_driver_performance(driver_code)
        position = driver_perf['position']
        points = driver_perf['points']
        team = driver_perf['team']
        
        features.update({
            'current_championship_position': position,
            'current_points_2025': points,
            'current_team_2025': team,
        })
        
        # Enhanced form score based on real performance
        if is_rookie_driver_2025(driver_code):
            # Rookie form score - reward good performance more
            if position <= 8:  # Points-scoring rookie
                form_score = 0.7 + (0.2 * (9 - position) / 8)  # 0.7-0.9 range
            elif position <= 15:
                form_score = 0.4 + (0.3 * (16 - position) / 7)  # 0.4-0.7 range
            else:
                form_score = 0.2 + (0.2 * (21 - position) / 5)  # 0.2-0.4 range
        else:
            # Experienced driver form score
            form_score = max(0.1, (21 - position) / 20.0)
        
        features['current_form_score'] = form_score
        
        # Team performance based on real 2025 constructor standings
        team_ranking = TEAM_RANKINGS_2025.get(team, 10)
        team_performance = max(0.1, (11 - team_ranking) / 10.0)
        features['current_team_performance'] = team_performance
        
        # Recent momentum (based on points and position)
        if points > 50:
            momentum = 0.8
        elif points > 20:
            momentum = 0.6
        elif points > 5:
            momentum = 0.4
        else:
            momentum = 0.2
        
        features['recent_momentum'] = momentum
        
        logger.debug(f"Real 2025 form for {driver_code}: P{position}, {points} pts, form {form_score:.2f}")
        return features
    
    def _create_qualifying_features_real_2025(self, driver_code: str, current_intelligence: Dict, 
                                            circuit_config: Dict) -> Dict:
        """Create qualifying features using real 2025 quali data + current weekend."""
        features = {}
        
        # Default values
        features.update({
            'qualifying_advantage': 0.0,
            'grid_position': 20,
            'pole_position_bonus': 0.0,
            'front_row_bonus': 0.0,
            'top_5_bonus': 0.0,
            'avg_2025_quali_position': 15.0
        })
        
        # Calculate average qualifying position from real 2025 data
        if 'qualifying' in self.season_2025_data:
            driver_quali = self.season_2025_data['qualifying'][
                self.season_2025_data['qualifying']['Driver'].str.contains(driver_code, na=False) |
                self.season_2025_data['qualifying']['No'].astype(str) == str(self._get_driver_number(driver_code))
            ]
            
            quali_positions = []
            for _, quali in driver_quali.iterrows():
                if pd.notna(quali['Position']) and quali['Position'] != 'NC' and quali['Position'] != 'DQ':
                    try:
                        position = int(quali['Position'])
                        quali_positions.append(position)
                    except:
                        continue
            
            if quali_positions:
                avg_quali = np.mean(quali_positions)
                features['avg_2025_quali_position'] = avg_quali
                logger.debug(f"Real 2025 quali avg for {driver_code}: P{avg_quali:.1f}")
        
        # Get current weekend qualifying from intelligence
        race_weekend = current_intelligence.get('race_weekend_data', {})
        qualifying_session = race_weekend.get('sessions', {}).get('Qualifying', {})
        
        if qualifying_session.get('available'):
            results = qualifying_session.get('results', [])
            pole_driver = qualifying_session.get('pole_position', '')
            
            for result in results:
                result_driver = result.get('driver', '').upper()
                if driver_code.upper() in result_driver or result_driver in driver_code.upper():
                    grid_position = result.get('position', 20)
                    features['grid_position'] = grid_position
                    
                    # Hungarian GP qualifying importance (85%)
                    qualifying_importance = circuit_config.get('qualifying_importance', 0.85)
                    
                    # Calculate advantage
                    position_advantage = max(0.05, (21 - grid_position) / 20.0)
                    features['qualifying_advantage'] = position_advantage * qualifying_importance
                    
                    # Bonuses for Hungarian GP
                    if grid_position == 1:
                        features['pole_position_bonus'] = 0.25
                        logger.info(f"🏁 {driver_code} has POLE POSITION")
                    elif grid_position <= 2:
                        features['front_row_bonus'] = 0.15
                    elif grid_position <= 5:
                        features['top_5_bonus'] = 0.10
                    
                    break
        
        return features
    
    def _get_driver_number(self, driver_code: str) -> int:
        """Get driver number from code."""
        for driver in ACTIVE_DRIVERS_2025:
            if driver['code'] == driver_code:
                return driver['number']
        return 99
    
    # Keep existing methods for historical features, weather, circuit, etc.
    # Just update them to work with the new 2025 data structure
    
    def _create_historical_features(self, driver_code: str, historical_data: List[Dict], 
                                  circuit_config: Dict) -> Dict:
        """Create historical features (for experienced drivers only)."""
        features = {}
        
        # Collect historical results (already filtered to 2025 active drivers)
        race_positions = []
        quali_positions = []
        points_scored = []
        dnf_count = 0
        race_count = 0
        
        for race in historical_data:
            race_drivers = race.get('drivers', {})
            if driver_code in race_drivers:
                driver_data = race_drivers[driver_code]
                race_count += 1
                
                race_pos = driver_data.get('race_position', 99)
                if race_pos != 99:
                    race_positions.append(race_pos)
                else:
                    dnf_count += 1
                
                quali_pos = driver_data.get('qualifying_position', 99)
                if quali_pos != 99:
                    quali_positions.append(quali_pos)
                
                points = driver_data.get('race_points', 0)
                points_scored.append(points)
        
        # Calculate features
        if race_positions:
            features.update({
                'historical_avg_position': np.mean(race_positions),
                'historical_best_position': min(race_positions),
                'historical_consistency': 1.0 / (1.0 + np.std(race_positions)),
                'historical_win_rate': sum(1 for pos in race_positions if pos == 1) / len(race_positions),
                'historical_podium_rate': sum(1 for pos in race_positions if pos <= 3) / len(race_positions),
                'historical_points_rate': sum(1 for pos in race_positions if pos <= 10) / len(race_positions)
            })
        else:
            features.update({
                'historical_avg_position': 12.0,
                'historical_best_position': 15.0,
                'historical_consistency': 0.5,
                'historical_win_rate': 0.0,
                'historical_podium_rate': 0.0,
                'historical_points_rate': 0.3
            })
        
        if quali_positions:
            features.update({
                'historical_quali_avg': np.mean(quali_positions),
                'historical_quali_best': min(quali_positions)
            })
        else:
            features.update({
                'historical_quali_avg': 12.0,
                'historical_quali_best': 15.0
            })
        
        # Experience features
        features.update({
            'circuit_race_count': race_count,
            'circuit_experience': min(race_count / 5.0, 1.0),
            'circuit_dnf_rate': dnf_count / max(race_count, 1),
            'historical_total_points': sum(points_scored),
            'rookie_penalty': 0.0
        })
        
        return features
    
    def _create_weather_features(self, driver_code: str, weather_data: Dict, 
                               circuit_config: Dict) -> Dict:
        """Create weather-related features."""
        features = {
            'weather_advantage': 0.5,
            'rain_specialist': 0.0,
            'heat_tolerance': 0.5,
            'weather_risk_factor': 0.0
        }
        
        race_analysis = weather_data.get('race_weekend_analysis', {})
        
        if race_analysis.get('race_day_conditions'):
            conditions = race_analysis['race_day_conditions']
            temp = conditions.get('temperature', 25)
            rain_prob = conditions.get('rain_probability', 0)
            
            # Rain specialists (based on 2025 performance in wet conditions)
            rain_specialists = ['HAM', 'VER', 'RUS', 'NOR', 'ALO', 'PIA']
            if driver_code in rain_specialists and rain_prob > 30:
                features['rain_specialist'] = min(rain_prob / 100.0, 0.3)
                features['weather_advantage'] += features['rain_specialist']
            
            # Heat tolerance
            if temp > 30:
                heat_tolerant_drivers = ['VER', 'LEC', 'SAI', 'ALO', 'PER', 'HAM']
                if driver_code in heat_tolerant_drivers:
                    features['heat_tolerance'] = 0.8
                    features['weather_advantage'] += 0.1
                else:
                    features['heat_tolerance'] = 0.3
                    features['weather_risk_factor'] += 0.1
            
            # Rookie weather penalty
            if is_rookie_driver_2025(driver_code):
                features['weather_risk_factor'] += 0.1
        
        return features
    
    def _create_circuit_features(self, driver_code: str, circuit_config: Dict, 
                               historical_data: List[Dict]) -> Dict:
        """Create circuit-specific features."""
        features = {}
        
        circuit_type = circuit_config.get('circuit_type', 'mixed')
        
        # Circuit specialists (updated for 2025 form)
        circuit_specialists = {
            'street_circuit': ['HAM', 'LEC', 'VER', 'RUS', 'PIA'],
            'high_speed': ['VER', 'LEC', 'NOR', 'SAI', 'PIA'],
            'technical': ['HAM', 'ALO', 'VER', 'LEC', 'RUS']
        }
        
        specialists = circuit_specialists.get(circuit_type, [])
        advantage = 0.2 if driver_code in specialists else 0.0
        
        # Reduce for rookies
        if is_rookie_driver_2025(driver_code):
            advantage *= 0.5
        
        features['circuit_type_advantage'] = advantage
        
        # Overtaking ability
        overtaking_masters = ['VER', 'HAM', 'LEC', 'NOR', 'ALO', 'PIA']
        overtaking_difficulty = circuit_config.get('overtaking_difficulty', 'medium')
        
        if overtaking_difficulty in ['high', 'very_high'] and driver_code in overtaking_masters:
            features['overtaking_advantage'] = 0.15 if not is_rookie_driver_2025(driver_code) else 0.05
        else:
            features['overtaking_advantage'] = 0.0
        
        # Historical winners (only for experienced drivers)
        if not is_rookie_driver_2025(driver_code):
            circuit_winners = self._get_historical_winners(historical_data)
            if driver_code in circuit_winners:
                wins = circuit_winners[driver_code]
                features['historical_winner_bonus'] = min(wins * 0.1, 0.3)
            else:
                features['historical_winner_bonus'] = 0.0
        else:
            features['historical_winner_bonus'] = 0.0
        
        return features
    
    def _create_expected_performance_features(self, driver_code: str, features: Dict, 
                                            circuit_config: Dict, is_rookie: bool) -> Dict:
        """Create expected performance features."""
        expected_features = {}
        
        # Use actual grid position if available
        grid_position = features.get('grid_position', 20)
        if grid_position < 20:
            expected_features['expected_quali_position'] = grid_position
        else:
            # Use average 2025 qualifying position
            avg_quali_2025 = features.get('avg_2025_quali_position', 15)
            expected_features['expected_quali_position'] = avg_quali_2025
        
        # Expected race position
        quali_importance = circuit_config.get('qualifying_importance', 0.7)
        qualifying_advantage = features.get('qualifying_advantage', 0.0)
        
        expected_race = (expected_features['expected_quali_position'] * quali_importance + 
                        features.get('historical_avg_position', 15) * (1 - quali_importance))
        
        # Apply qualifying advantage
        expected_race = expected_race - (qualifying_advantage * 10)
        
        # Rookie penalty
        if is_rookie:
            rookie_penalty = features.get('rookie_penalty', 0.15)
            expected_race = expected_race + (rookie_penalty * 3)  # Smaller penalty with real data
        
        expected_features['expected_race_position'] = min(20, max(1, expected_race))
        
        # Competitiveness score
        competitiveness = (
            features.get('current_form_score', 0.5) * 0.4 +  # Increased weight for 2025 form
            (21 - features.get('historical_avg_position', 15)) / 20 * 0.2 +
            features.get('weather_advantage', 0.5) * 0.1 +
            features.get('circuit_experience', 0) * 0.05 +
            qualifying_advantage * 0.25
        )
        
        if is_rookie:
            competitiveness *= 0.9  # Smaller penalty with real performance data
        
        expected_features['competitiveness_score'] = min(1.0, max(0.0, competitiveness))
        
        return expected_features
    
    def _get_historical_winners(self, historical_data: List[Dict]) -> Dict:
        """Get historical winners (filtered to 2025 active drivers)."""
        winners = {}
        for race in historical_data:
            winner = race.get('race_winner')
            if winner and winner in self.active_driver_codes:
                winners[winner] = winners.get(winner, 0) + 1
        return winners
    
    def _create_real_2025_form_features(self, driver_code: str) -> Dict:
        """Create current form features using LOCAL 2025 championship data."""
        features = {}
        
        # Get REAL championship data from settings (no API call)
        from config.settings import CURRENT_2025_STANDINGS
        driver_perf = CURRENT_2025_STANDINGS.get(driver_code, {'position': 20, 'points': 0, 'team': 'Unknown'})
        
        position = driver_perf['position']
        points = driver_perf['points']
        team = driver_perf['team']
        
        features.update({
            'current_championship_position': position,
            'current_points_2025': points,
            'current_team_2025': team,
        })
        
        # Enhanced form score based on real performance
        if is_rookie_driver_2025(driver_code):
            # Reward good rookie performance
            if position <= 8:  # Points-scoring rookie
                form_score = 0.7 + (0.2 * (9 - position) / 8)
            elif position <= 15:
                form_score = 0.4 + (0.3 * (16 - position) / 7)
            else:
                form_score = 0.2 + (0.2 * (21 - position) / 5)
        else:
            # Normal form score for experienced drivers
            form_score = max(0.1, (21 - position) / 20.0)
        
        features['current_form_score'] = form_score
        
        # Team performance based on 2025 constructor standings
        from config.settings import TEAM_RANKINGS_2025
        team_ranking = TEAM_RANKINGS_2025.get(team, 10)
        team_performance = max(0.1, (11 - team_ranking) / 10.0)
        features['current_team_performance'] = team_performance
        
        # Recent momentum
        if points > 50:
            momentum = 0.8
        elif points > 20:
            momentum = 0.6
        else:
            momentum = 0.4
        
        features['recent_momentum'] = momentum
        
        logger.debug(f"LOCAL 2025 data for {driver_code}: P{position}, {points} pts, form {form_score:.2f}")
        return features


# Keep compatibility
FeatureEngineer = Enhanced2025FeatureEngineer
