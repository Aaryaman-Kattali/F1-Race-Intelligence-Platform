"""
Circuit-specific analysis tools for F1 Grand Prix predictions.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json
from pathlib import Path

from config.settings import BASE_DIR

logger = logging.getLogger(__name__)

class CircuitAnalyzer:
    """Analyze circuit-specific characteristics and performance patterns."""
    
    def __init__(self):
        self.circuits = self._load_circuit_configs()
        self.analysis_cache = {}
    
    def analyze_circuit_characteristics(self, circuit_key: str, historical_data: List[Dict]) -> Dict:
        """
        Comprehensive analysis of circuit characteristics and patterns.
        
        Args:
            circuit_key: Circuit identifier (e.g., 'hungarian_gp')
            historical_data: Historical race data for this circuit
            
        Returns:
            Detailed circuit analysis
        """
        try:
            logger.info(f"🏁 Analyzing circuit characteristics for {circuit_key}")
            
            circuit_config = self.circuits.get(circuit_key, {})
            
            analysis = {
                'circuit_info': self._get_circuit_info(circuit_key, circuit_config),
                'historical_analysis': self._analyze_historical_performance(historical_data, circuit_config),
                'strategic_factors': self._analyze_strategic_factors(historical_data, circuit_config),
                'performance_indicators': self._identify_performance_indicators(historical_data, circuit_config),
                'success_patterns': self._analyze_success_patterns(historical_data),
                'difficulty_assessment': self._assess_circuit_difficulty(circuit_config, historical_data),
                'weather_impact_analysis': self._analyze_weather_patterns(historical_data),
                'overtaking_analysis': self._analyze_overtaking_characteristics(historical_data, circuit_config),
                'analysis_metadata': {
                    'analysis_date': datetime.now().isoformat(),
                    'data_quality': self._assess_data_quality(historical_data),
                    'races_analyzed': len(historical_data)
                }
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing circuit characteristics: {e}")
            return {}
    
    def get_circuit_difficulty_factors(self, circuit_key: str) -> Dict:
        """
        Get specific difficulty factors for a circuit.
        
        Args:
            circuit_key: Circuit identifier
            
        Returns:
            Circuit difficulty factors
        """
        circuit_config = self.circuits.get(circuit_key, {})
        
        return {
            'overtaking_difficulty': self._rate_difficulty(circuit_config.get('overtaking_difficulty', 'medium')),
            'qualifying_importance': circuit_config.get('qualifying_importance', 0.7),
            'weather_sensitivity': circuit_config.get('weather_sensitivity', 0.5),
            'physical_demands': self._assess_physical_demands(circuit_key),
            'technical_complexity': self._assess_technical_complexity(circuit_config),
            'strategy_importance': self._assess_strategy_importance(circuit_config),
            'driver_skill_factor': self._assess_driver_skill_requirement(circuit_config),
            'car_setup_sensitivity': self._assess_setup_sensitivity(circuit_config)
        }
    
    def identify_circuit_specialists(self, historical_data: List[Dict], min_races: int = 3) -> Dict:
        """
        Identify drivers who consistently perform well at this circuit.
        
        Args:
            historical_data: Historical race data
            min_races: Minimum races to qualify as specialist
            
        Returns:
            Circuit specialist analysis
        """
        specialists = {
            'race_winners': {},
            'consistent_performers': {},
            'qualifying_masters': {},
            'comeback_specialists': {},
            'reliability_experts': {}
        }
        
        try:
            driver_stats = self._calculate_driver_statistics(historical_data)
            
            # Identify race winners
            for driver, stats in driver_stats.items():
                if stats['races'] >= min_races:
                    win_rate = stats['wins'] / stats['races']
                    podium_rate = stats['podiums'] / stats['races']
                    points_rate = stats['points_finishes'] / stats['races']
                    
                    # Race winners (high win rate)
                    if win_rate >= 0.3:  # 30% win rate or higher
                        specialists['race_winners'][driver] = {
                            'win_rate': win_rate,
                            'wins': stats['wins'],
                            'races': stats['races'],
                            'dominance_score': win_rate * 0.6 + podium_rate * 0.4
                        }
                    
                    # Consistent performers (high points rate)
                    if points_rate >= 0.7:  # 70% points finish rate
                        specialists['consistent_performers'][driver] = {
                            'points_rate': points_rate,
                            'avg_position': stats['avg_position'],
                            'consistency_score': stats['consistency'],
                            'reliability_score': 1.0 - (stats['dnfs'] / stats['races'])
                        }
                    
                    # Qualifying masters
                    if stats['avg_quali_position'] <= 5:  # Average top 5 qualifier
                        specialists['qualifying_masters'][driver] = {
                            'avg_quali_position': stats['avg_quali_position'],
                            'best_quali': stats['best_quali'],
                            'quali_consistency': stats['quali_consistency']
                        }
                    
                    # Comeback specialists (good at gaining positions)
                    if stats['avg_position_gain'] > 2:  # Average 2+ position gain
                        specialists['comeback_specialists'][driver] = {
                            'avg_position_gain': stats['avg_position_gain'],
                            'best_comeback': stats['best_comeback'],
                            'comeback_frequency': stats['comeback_frequency']
                        }
        
        except Exception as e:
            logger.error(f"Error identifying specialists: {e}")
        
        return specialists
    
    def analyze_team_advantages(self, historical_data: List[Dict]) -> Dict:
        """Analyze which teams have advantages at this circuit."""
        team_analysis = {
            'dominant_teams': {},
            'era_performance': {},
            'current_advantages': {},
            'power_unit_impact': {},
            'aerodynamic_advantages': {}
        }
        
        try:
            team_stats = self._calculate_team_statistics(historical_data)
            
            for team, stats in team_stats.items():
                if stats['races'] >= 3:  # Minimum 3 races
                    win_rate = stats['wins'] / stats['races']
                    podium_rate = stats['podiums'] / stats['races']
                    
                    if win_rate > 0.2 or podium_rate > 0.4:  # Strong performance threshold
                        team_analysis['dominant_teams'][team] = {
                            'win_rate': win_rate,
                            'podium_rate': podium_rate,
                            'avg_position': stats['avg_position'],
                            'performance_trend': self._calculate_team_trend(team, historical_data)
                        }
            
            # Analyze by era (group by years)
            team_analysis['era_performance'] = self._analyze_team_eras(historical_data)
        
        except Exception as e:
            logger.error(f"Error analyzing team advantages: {e}")
        
        return team_analysis
    
    def predict_circuit_impact_factors(self, weather_data: Dict, circuit_key: str) -> Dict:
        """
        Predict how current conditions will impact race at this circuit.
        
        Args:
            weather_data: Current weather forecast
            circuit_key: Circuit identifier
            
        Returns:
            Impact factor predictions
        """
        circuit_config = self.circuits.get(circuit_key, {})
        
        impact_factors = {
            'weather_impact': self._assess_weather_impact(weather_data, circuit_config),
            'temperature_effects': self._assess_temperature_effects(weather_data, circuit_config),
            'rain_impact': self._assess_rain_impact(weather_data, circuit_config),
            'wind_effects': self._assess_wind_effects(weather_data, circuit_config),
            'track_evolution': self._predict_track_evolution(weather_data, circuit_config),
            'tire_strategy_impact': self._predict_tire_strategy_impact(weather_data, circuit_config),
            'overall_unpredictability': self._calculate_unpredictability_factor(weather_data, circuit_config)
        }
        
        return impact_factors
    
    def _get_circuit_info(self, circuit_key: str, circuit_config: Dict) -> Dict:
        """Extract basic circuit information."""
        return {
            'circuit_key': circuit_key,
            'official_name': circuit_config.get('official_names', ['Unknown'])[0],
            'location': circuit_config.get('location', {}),
            'circuit_type': circuit_config.get('circuit_type', 'mixed'),
            'key_characteristics': circuit_config.get('key_factors', []),
            'typical_weather': circuit_config.get('typical_weather', {})
        }
    
    def _analyze_historical_performance(self, historical_data: List[Dict], circuit_config: Dict) -> Dict:
        """Analyze historical performance patterns."""
        analysis = {
            'total_races': len(historical_data),
            'years_covered': [],
            'winner_diversity': 0,
            'dominant_periods': [],
            'performance_trends': {}
        }
        
        try:
            if historical_data:
                years = [race.get('year') for race in historical_data if race.get('year')]
                analysis['years_covered'] = sorted(years)
                
                # Winner diversity
                winners = [race.get('race_winner') for race in historical_data if race.get('race_winner')]
                unique_winners = set(winners)
                analysis['winner_diversity'] = len(unique_winners) / len(winners) if winners else 0
                
                # Identify dominant periods
                analysis['dominant_periods'] = self._identify_dominant_periods(historical_data)
                
                # Performance trends over time
                analysis['performance_trends'] = self._analyze_performance_trends(historical_data)
        
        except Exception as e:
            logger.error(f"Error analyzing historical performance: {e}")
        
        return analysis
    
    def _analyze_strategic_factors(self, historical_data: List[Dict], circuit_config: Dict) -> Dict:
        """Analyze strategic factors and their importance."""
        strategic_factors = {
            'pit_stop_impact': self._analyze_pit_stop_impact(historical_data),
            'tire_strategy_importance': self._analyze_tire_strategy_importance(historical_data),
            'safety_car_impact': self._analyze_safety_car_impact(historical_data),
            'drs_effectiveness': self._analyze_drs_effectiveness(historical_data, circuit_config),
            'track_position_value': self._analyze_track_position_value(historical_data, circuit_config)
        }
        
        return strategic_factors
    
    def _identify_performance_indicators(self, historical_data: List[Dict], circuit_config: Dict) -> Dict:
        """Identify key performance indicators for this circuit."""
        indicators = {
            'qualifying_correlation': self._calculate_qualifying_race_correlation(historical_data),
            'practice_predictiveness': self._analyze_practice_predictiveness(historical_data),
            'sector_importance': self._analyze_sector_importance(historical_data),
            'speed_trap_relevance': self._analyze_speed_trap_relevance(historical_data),
            'consistency_vs_pace': self._analyze_consistency_vs_pace(historical_data)
        }
        
        return indicators
    
    def _analyze_success_patterns(self, historical_data: List[Dict]) -> Dict:
        """Analyze patterns in successful performances."""
        patterns = {
            'winning_starting_positions': [],
            'winning_characteristics': {},
            'upset_victories': [],
            'consistency_patterns': {}
        }
        
        try:
            for race in historical_data:
                winner = race.get('race_winner')
                if winner and winner in race.get('drivers', {}):
                    driver_data = race['drivers'][winner]
                    quali_pos = driver_data.get('qualifying_position', 99)
                    
                    if quali_pos != 99:
                        patterns['winning_starting_positions'].append(quali_pos)
                        
                        # Identify upset victories (winners starting outside top 3)
                        if quali_pos > 3:
                            patterns['upset_victories'].append({
                                'year': race.get('year'),
                                'winner': winner,
                                'starting_position': quali_pos,
                                'position_gain': quali_pos - 1
                            })
            
            # Analyze winning starting positions
            if patterns['winning_starting_positions']:
                positions = patterns['winning_starting_positions']
                patterns['winning_characteristics'] = {
                    'avg_starting_position': np.mean(positions),
                    'pole_win_percentage': (sum(1 for pos in positions if pos == 1) / len(positions)) * 100,
                    'front_row_win_percentage': (sum(1 for pos in positions if pos <= 2) / len(positions)) * 100,
                    'top_5_win_percentage': (sum(1 for pos in positions if pos <= 5) / len(positions)) * 100
                }
        
        except Exception as e:
            logger.error(f"Error analyzing success patterns: {e}")
        
        return patterns
    
    def _assess_circuit_difficulty(self, circuit_config: Dict, historical_data: List[Dict]) -> Dict:
        """Assess overall circuit difficulty."""
        difficulty = {
            'overall_rating': 0.0,
            'difficulty_factors': {},
            'driver_skill_requirement': 0.0,
            'setup_sensitivity': 0.0,
            'unpredictability_factor': 0.0
        }
        
        try:
            # Base difficulty from config
            overtaking_diff = self._rate_difficulty(circuit_config.get('overtaking_difficulty', 'medium'))
            quali_importance = circuit_config.get('qualifying_importance', 0.7)
            weather_sensitivity = circuit_config.get('weather_sensitivity', 0.5)
            
            # Calculate from historical data
            if historical_data:
                winner_diversity = len(set(race.get('race_winner') for race in historical_data if race.get('race_winner'))) / len(historical_data)
                upset_rate = self._calculate_upset_rate(historical_data)
                
                difficulty['unpredictability_factor'] = (winner_diversity + upset_rate) / 2
            
            # Combine factors
            difficulty['overall_rating'] = (
                overtaking_diff * 0.3 +
                quali_importance * 0.25 +
                weather_sensitivity * 0.2 +
                difficulty.get('unpredictability_factor', 0.5) * 0.25
            )
            
            difficulty['difficulty_factors'] = {
                'overtaking_difficulty': overtaking_diff,
                'qualifying_importance': quali_importance,
                'weather_sensitivity': weather_sensitivity,
                'winner_unpredictability': difficulty.get('unpredictability_factor', 0.5)
            }
        
        except Exception as e:
            logger.error(f"Error assessing circuit difficulty: {e}")
        
        return difficulty
    
    def _calculate_driver_statistics(self, historical_data: List[Dict]) -> Dict:
        """Calculate comprehensive driver statistics."""
        driver_stats = {}
        
        for race in historical_data:
            for driver_code, driver_data in race.get('drivers', {}).items():
                if driver_code not in driver_stats:
                    driver_stats[driver_code] = {
                        'races': 0, 'wins': 0, 'podiums': 0, 'points_finishes': 0, 'dnfs': 0,
                        'positions': [], 'quali_positions': [], 'position_gains': []
                    }
                
                stats = driver_stats[driver_code]
                stats['races'] += 1
                
                race_pos = driver_data.get('race_position', 99)
                quali_pos = driver_data.get('qualifying_position', 99)
                
                if race_pos != 99:
                    stats['positions'].append(race_pos)
                    if race_pos == 1:
                        stats['wins'] += 1
                    if race_pos <= 3:
                        stats['podiums'] += 1
                    if race_pos <= 10:
                        stats['points_finishes'] += 1
                    
                    if quali_pos != 99:
                        position_gain = quali_pos - race_pos
                        stats['position_gains'].append(position_gain)
                else:
                    stats['dnfs'] += 1
                
                if quali_pos != 99:
                    stats['quali_positions'].append(quali_pos)
        
        # Calculate derived statistics
        for driver, stats in driver_stats.items():
            if stats['positions']:
                stats['avg_position'] = np.mean(stats['positions'])
                stats['consistency'] = 1.0 / (1.0 + np.std(stats['positions']))
            else:
                stats['avg_position'] = 20
                stats['consistency'] = 0
            
            if stats['quali_positions']:
                stats['avg_quali_position'] = np.mean(stats['quali_positions'])
                stats['best_quali'] = min(stats['quali_positions'])
                stats['quali_consistency'] = 1.0 / (1.0 + np.std(stats['quali_positions']))
            else:
                stats['avg_quali_position'] = 20
                stats['best_quali'] = 20
                stats['quali_consistency'] = 0
            
            if stats['position_gains']:
                stats['avg_position_gain'] = np.mean(stats['position_gains'])
                stats['best_comeback'] = max(stats['position_gains'])
                stats['comeback_frequency'] = sum(1 for gain in stats['position_gains'] if gain > 0) / len(stats['position_gains'])
            else:
                stats['avg_position_gain'] = 0
                stats['best_comeback'] = 0
                stats['comeback_frequency'] = 0
        
        return driver_stats
    
    def _calculate_team_statistics(self, historical_data: List[Dict]) -> Dict:
        """Calculate team performance statistics."""
        team_stats = {}
        
        for race in historical_data:
            for driver_code, driver_data in race.get('drivers', {}).items():
                team = driver_data.get('team', 'Unknown')
                
                if team not in team_stats:
                    team_stats[team] = {
                        'races': 0, 'wins': 0, 'podiums': 0, 'points_finishes': 0,
                        'positions': [], 'years': set()
                    }
                
                stats = team_stats[team]
                stats['races'] += 1
                stats['years'].add(race.get('year'))
                
                race_pos = driver_data.get('race_position', 99)
                if race_pos != 99:
                    stats['positions'].append(race_pos)
                    if race_pos == 1:
                        stats['wins'] += 1
                    if race_pos <= 3:
                        stats['podiums'] += 1
                    if race_pos <= 10:
                        stats['points_finishes'] += 1
        
        # Calculate derived statistics
        for team, stats in team_stats.items():
            if stats['positions']:
                stats['avg_position'] = np.mean(stats['positions'])
                stats['consistency'] = 1.0 / (1.0 + np.std(stats['positions']))
            else:
                stats['avg_position'] = 15
                stats['consistency'] = 0
            
            stats['years_active'] = len(stats['years'])
        
        return team_stats
    
    def _rate_difficulty(self, difficulty_str: str) -> float:
        """Convert difficulty string to numeric rating."""
        ratings = {
            'very_low': 0.2, 'low': 0.4, 'medium': 0.6,
            'high': 0.8, 'very_high': 1.0, 'nearly_impossible': 1.0
        }
        return ratings.get(difficulty_str, 0.6)
    
    def _assess_physical_demands(self, circuit_key: str) -> float:
        """Assess physical demands of the circuit."""
        high_demand_circuits = ['singapore_gp', 'monaco_gp', 'hungarian_gp', 'brazilian_gp']
        medium_demand_circuits = ['spanish_gp', 'austrian_gp', 'abu_dhabi_gp']
        
        if circuit_key in high_demand_circuits:
            return 0.9
        elif circuit_key in medium_demand_circuits:
            return 0.6
        else:
            return 0.4
    
    def _assess_technical_complexity(self, circuit_config: Dict) -> float:
        """Assess technical complexity of the circuit."""
        circuit_type = circuit_config.get('circuit_type', 'mixed')
        
        complexity_ratings = {
            'technical': 0.9,
            'street_circuit': 0.8,
            'mixed': 0.6,
            'high_speed': 0.4
        }
        
        return complexity_ratings.get(circuit_type, 0.6)
    
    def _assess_strategy_importance(self, circuit_config: Dict) -> float:
        """Assess importance of strategy at this circuit."""
        overtaking_difficulty = self._rate_difficulty(circuit_config.get('overtaking_difficulty', 'medium'))
        weather_sensitivity = circuit_config.get('weather_sensitivity', 0.5)
        
        return (overtaking_difficulty + weather_sensitivity) / 2
    
    def _assess_driver_skill_requirement(self, circuit_config: Dict) -> float:
        """Assess driver skill requirement for this circuit."""
        circuit_type = circuit_config.get('circuit_type', 'mixed')
        overtaking_difficulty = self._rate_difficulty(circuit_config.get('overtaking_difficulty', 'medium'))
        
        skill_requirements = {
            'street_circuit': 0.9,
            'technical': 0.8,
            'mixed': 0.6,
            'high_speed': 0.5
        }
        
        base_skill = skill_requirements.get(circuit_type, 0.6)
        return (base_skill + overtaking_difficulty) / 2
    
    def _assess_setup_sensitivity(self, circuit_config: Dict) -> float:
        """Assess car setup sensitivity for this circuit."""
        circuit_type = circuit_config.get('circuit_type', 'mixed')
        key_factors = circuit_config.get('key_factors', [])
        
        setup_sensitive_factors = ['aerodynamics', 'suspension', 'setup_optimization']
        sensitivity_count = sum(1 for factor in key_factors if any(sensitive in factor for sensitive in setup_sensitive_factors))
        
        base_sensitivity = 0.7 if circuit_type == 'technical' else 0.5
        factor_sensitivity = min(sensitivity_count * 0.1, 0.3)
        
        return min(base_sensitivity + factor_sensitivity, 1.0)
    
    def _load_circuit_configs(self) -> Dict:
        """Load circuit configurations from JSON file."""
        try:
            config_path = BASE_DIR / "config" / "circuits.json"
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading circuit configs: {e}")
            return {}
    
    def _assess_data_quality(self, historical_data: List[Dict]) -> str:
        """Assess quality of historical data."""
        if len(historical_data) >= 7:
            return 'excellent'
        elif len(historical_data) >= 5:
            return 'good'
        elif len(historical_data) >= 3:
            return 'fair'
        else:
            return 'limited'
    
    # Placeholder methods for complex analysis (would be implemented with more detailed logic)
    def _identify_dominant_periods(self, historical_data: List[Dict]) -> List[Dict]:
        """Identify periods of dominance by drivers or teams."""
        return []  # Placeholder
    
    def _analyze_performance_trends(self, historical_data: List[Dict]) -> Dict:
        """Analyze performance trends over time."""
        return {}  # Placeholder
    
    def _calculate_team_trend(self, team: str, historical_data: List[Dict]) -> str:
        """Calculate team performance trend."""
        return 'stable'  # Placeholder
    
    def _analyze_team_eras(self, historical_data: List[Dict]) -> Dict:
        """Analyze team performance by era."""
        return {}  # Placeholder
    
    def _calculate_upset_rate(self, historical_data: List[Dict]) -> float:
        """Calculate rate of upset victories."""
        return 0.2  # Placeholder
    
    # Weather and track condition analysis methods (placeholders)
    def _assess_weather_impact(self, weather_data: Dict, circuit_config: Dict) -> Dict:
        return {'impact_level': 'medium'}
    
    def _assess_temperature_effects(self, weather_data: Dict, circuit_config: Dict) -> Dict:
        return {'temperature_impact': 'normal'}
    
    def _assess_rain_impact(self, weather_data: Dict, circuit_config: Dict) -> Dict:
        return {'rain_impact': 'high' if weather_data.get('rain_probability', 0) > 50 else 'low'}
    
    def _assess_wind_effects(self, weather_data: Dict, circuit_config: Dict) -> Dict:
        return {'wind_impact': 'minimal'}
    
    def _predict_track_evolution(self, weather_data: Dict, circuit_config: Dict) -> Dict:
        return {'evolution_factor': 'normal'}
    
    def _predict_tire_strategy_impact(self, weather_data: Dict, circuit_config: Dict) -> Dict:
        return {'strategy_importance': 'high'}
    
    def _calculate_unpredictability_factor(self, weather_data: Dict, circuit_config: Dict) -> float:
        return 0.3
    
    # Strategic analysis placeholder methods
    def _analyze_pit_stop_impact(self, historical_data: List[Dict]) -> Dict:
        return {'pit_stop_importance': 'medium'}
    
    def _analyze_tire_strategy_importance(self, historical_data: List[Dict]) -> Dict:
        return {'tire_strategy_impact': 'high'}
    
    def _analyze_safety_car_impact(self, historical_data: List[Dict]) -> Dict:
        return {'safety_car_frequency': 'medium'}
    
    def _analyze_drs_effectiveness(self, historical_data: List[Dict], circuit_config: Dict) -> Dict:
        return {'drs_effectiveness': 'medium'}
    
    def _analyze_track_position_value(self, historical_data: List[Dict], circuit_config: Dict) -> Dict:
        return {'track_position_importance': circuit_config.get('qualifying_importance', 0.7)}
    
    def _calculate_qualifying_race_correlation(self, historical_data: List[Dict]) -> float:
        return 0.7  # Placeholder
    
    def _analyze_practice_predictiveness(self, historical_data: List[Dict]) -> Dict:
        return {'practice_correlation': 0.6}
    
    def _analyze_sector_importance(self, historical_data: List[Dict]) -> Dict:
        return {'sector_weights': [0.33, 0.33, 0.34]}
    
    def _analyze_speed_trap_relevance(self, historical_data: List[Dict]) -> Dict:
        return {'speed_trap_correlation': 0.5}
    
    def _analyze_consistency_vs_pace(self, historical_data: List[Dict]) -> Dict:
        return {'consistency_importance': 0.6, 'pace_importance': 0.4}
    
    def _analyze_weather_patterns(self, historical_data: List[Dict]) -> Dict:
        """Analyze historical weather patterns at this circuit."""
        weather_analysis = {
            'rain_frequency': 0.0,
            'temperature_patterns': {},
            'weather_upset_correlation': 0.0
        }
        
        try:
            rain_races = 0
            temperatures = []
            
            for race in historical_data:
                weather_data = race.get('weather', {})
                if weather_data.get('available'):
                    if weather_data.get('rainfall', False):
                        rain_races += 1
                    
                    temp = weather_data.get('air_temp_avg')
                    if temp:
                        temperatures.append(temp)
            
            if historical_data:
                weather_analysis['rain_frequency'] = rain_races / len(historical_data)
            
            if temperatures:
                weather_analysis['temperature_patterns'] = {
                    'avg_temperature': np.mean(temperatures),
                    'temperature_range': [min(temperatures), max(temperatures)],
                    'temperature_variance': np.var(temperatures)
                }
        
        except Exception as e:
            logger.error(f"Error analyzing weather patterns: {e}")
        
        return weather_analysis
    
    def _analyze_overtaking_characteristics(self, historical_data: List[Dict], circuit_config: Dict) -> Dict:
        """Analyze overtaking patterns and characteristics."""
        overtaking_analysis = {
            'average_position_changes': 0.0,
            'front_runner_advantage': 0.0,
            'comeback_difficulty': circuit_config.get('overtaking_difficulty', 'medium'),
            'drs_zones_effectiveness': self._rate_difficulty(circuit_config.get('overtaking_difficulty', 'medium'))
        }
        
        try:
            position_changes = []
            front_runner_wins = 0
            total_winners = 0
            
            for race in historical_data:
                winner = race.get('race_winner')
                if winner and winner in race.get('drivers', {}):
                    total_winners += 1
                    driver_data = race['drivers'][winner]
                    quali_pos = driver_data.get('qualifying_position', 99)
                    
                    if quali_pos != 99:
                        position_change = quali_pos - 1  # Positions gained to win
                        position_changes.append(position_change)
                        
                        if quali_pos <= 2:  # Started on front row
                            front_runner_wins += 1
            
            if position_changes:
                overtaking_analysis['average_position_changes'] = np.mean(position_changes)
            
            if total_winners > 0:
                overtaking_analysis['front_runner_advantage'] = front_runner_wins / total_winners
        
        except Exception as e:
            logger.error(f"Error analyzing overtaking characteristics: {e}")
        
        return overtaking_analysis
