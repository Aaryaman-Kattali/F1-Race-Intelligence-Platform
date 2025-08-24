"""
FastF1 data collector for historical F1 race data.
"""

import fastf1
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

from config.settings import FASTF1_CACHE_DIR, HISTORICAL_YEARS

logger = logging.getLogger(__name__)

class FastF1Collector:
    """Collect historical F1 data using FastF1 API."""
    
    def __init__(self):
        # Enable FastF1 cache
        fastf1.Cache.enable_cache(FASTF1_CACHE_DIR)
        
        # Reduce FastF1 logging verbosity
        try:
            fastf1.set_log_level('WARNING')
        except AttributeError:
            pass
    
    def get_circuit_historical_data(self, circuit_name: str) -> List[Dict]:
        """
        Get all historical data for a specific circuit.
        
        Args:
            circuit_name: Name of the GP (e.g., "Hungarian Grand Prix")
            
        Returns:
            List of race data dictionaries
        """
        historical_data = []
        
        logger.info(f"🏁 Collecting historical data for {circuit_name}")
        
        for year in HISTORICAL_YEARS:
            try:
                # Get season schedule
                schedule = self._get_season_schedule(year)
                
                # Find matching race
                race_round = self._find_race_round(circuit_name, schedule)
                
                if race_round:
                    logger.info(f"   📅 Processing {circuit_name} {year} (Round {race_round})")
                    
                    # Collect race weekend data
                    race_data = self._collect_race_weekend_data(year, race_round, circuit_name)
                    
                    if race_data:
                        historical_data.append(race_data)
                        logger.info(f"   ✅ Collected {year} data successfully")
                    else:
                        logger.warning(f"   ❌ No data available for {year}")
                        
            except Exception as e:
                logger.warning(f"   ⚠️  Error collecting {year} data: {e}")
                continue
        
        logger.info(f"🎯 Collected {len(historical_data)} historical races for {circuit_name}")
        return historical_data
    
    def _get_season_schedule(self, year: int) -> List[Dict]:
        """Get F1 season schedule."""
        try:
            schedule = fastf1.get_event_schedule(year)
            events = []
            
            for _, event in schedule.iterrows():
                events.append({
                    'round': event.get('RoundNumber', 0),
                    'race_name': event.get('EventName', ''),
                    'official_name': event.get('OfficialEventName', ''),
                    'location': event.get('Location', ''),
                    'country': event.get('Country', ''),
                    'date': event.get('EventDate')
                })
            
            return events
            
        except Exception as e:
            logger.error(f"Error getting {year} schedule: {e}")
            return []
    
    def _find_race_round(self, target_circuit: str, schedule: List[Dict]) -> Optional[int]:
        """Find the round number for a specific circuit."""
        target_lower = target_circuit.lower()
        
        for event in schedule:
            race_name = event['race_name'].lower()
            official_name = event.get('official_name', '').lower()
            location = event.get('location', '').lower()
            
            # Check multiple name variations
            if (target_lower in race_name or 
                race_name in target_lower or
                target_lower in official_name or
                target_lower in location):
                return event['round']
        
        return None
    
    def _collect_race_weekend_data(self, year: int, race_round: int, circuit_name: str) -> Optional[Dict]:
        """Collect comprehensive race weekend data."""
        try:
            race_data = {
                'year': year,
                'round': race_round,
                'circuit_name': circuit_name,
                'sessions': {},
                'drivers': {},
                'weather': {},
                'race_winner': None
            }
            
            # Collect Race session (most important)
            race_session = self._get_session_data(year, race_round, 'Race')
            if race_session:
                race_data['sessions']['Race'] = race_session
                race_data['race_winner'] = self._extract_race_winner(race_session)
            
            # Collect Qualifying session
            qualifying_session = self._get_session_data(year, race_round, 'Qualifying')
            if qualifying_session:
                race_data['sessions']['Qualifying'] = qualifying_session
            
            # Collect Practice sessions (FP3 most relevant)
            fp3_session = self._get_session_data(year, race_round, 'FP3')
            if fp3_session:
                race_data['sessions']['FP3'] = fp3_session
            
            # Extract driver performance data
            race_data['drivers'] = self._extract_driver_data(race_data['sessions'])
            
            # Extract weather data
            if race_session:
                race_data['weather'] = self._extract_weather_data(race_session)
            
            return race_data if race_data['race_winner'] else None
            
        except Exception as e:
            logger.error(f"Error collecting race weekend data for {year} round {race_round}: {e}")
            return None
    
    def _get_session_data(self, year: int, race_round: int, session_type: str) -> Optional[Dict]:
        """Get data for a specific session."""
        try:
            session = fastf1.get_session(year, race_round, session_type)
            session.load()
            
            if session.results.empty:
                return None
            
            session_data = {
                'session_type': session_type,
                'date': session.date,
                'results': self._process_session_results(session.results),
                'laps': self._process_lap_data(session.laps),
                'weather': self._extract_weather_data(session) if hasattr(session, 'weather_data') else {}
            }
            
            return session_data
            
        except Exception as e:
            logger.debug(f"Error getting {session_type} session data: {e}")
            return None
    
    def _process_session_results(self, results: pd.DataFrame) -> List[Dict]:
        """Process session results into clean format."""
        processed_results = []
        
        for _, driver in results.iterrows():
            driver_data = {
                'driver_number': self._safe_get(driver, 'DriverNumber', 0),
                'driver_code': self._safe_get(driver, 'Abbreviation', ''),
                'first_name': self._safe_get(driver, 'FirstName', ''),
                'last_name': self._safe_get(driver, 'LastName', ''),
                'team': self._safe_get(driver, 'TeamName', ''),
                'position': self._safe_get(driver, 'Position', 99),
                'grid_position': self._safe_get(driver, 'GridPosition', 99),
                'time': str(self._safe_get(driver, 'Time', '')),
                'points': self._safe_get(driver, 'Points', 0),
                'status': self._safe_get(driver, 'Status', 'Unknown')
            }
            processed_results.append(driver_data)
        
        return processed_results
    
    def _process_lap_data(self, laps: pd.DataFrame) -> Dict:
        """Process lap data for driver analysis."""
        if laps.empty:
            return {}
        
        lap_analysis = {
            'total_laps': len(laps),
            'drivers': {}
        }
        
        for driver_code in laps['Driver'].unique():
            if pd.isna(driver_code):
                continue
                
            driver_laps = laps[laps['Driver'] == driver_code]
            
            if not driver_laps.empty:
                # Calculate driver metrics
                valid_laps = driver_laps.dropna(subset=['LapTime'])
                
                if not valid_laps.empty:
                    lap_times = valid_laps['LapTime'].dt.total_seconds()
                    
                    lap_analysis['drivers'][driver_code] = {
                        'total_laps': len(driver_laps),
                        'valid_laps': len(valid_laps),
                        'fastest_lap': float(lap_times.min()),
                        'average_lap': float(lap_times.mean()),
                        'consistency': self._calculate_consistency(lap_times),
                        'positions': list(driver_laps['Position'].dropna().unique())
                    }
        
        return lap_analysis
    
    def _extract_weather_data(self, session) -> Dict:
        """Extract weather information from session."""
        try:
            if not hasattr(session, 'weather_data') or session.weather_data.empty:
                return {'available': False}
            
            weather_data = session.weather_data
            
            return {
                'available': True,
                'air_temp_avg': float(weather_data['AirTemp'].mean()),
                'track_temp_avg': float(weather_data['TrackTemp'].mean()),
                'humidity_avg': float(weather_data['Humidity'].mean()),
                'pressure_avg': float(weather_data['Pressure'].mean()),
                'wind_speed_avg': float(weather_data['WindSpeed'].mean()),
                'rainfall': bool(weather_data['Rainfall'].any()),
                'weather_records': len(weather_data)
            }
            
        except Exception as e:
            logger.debug(f"Error extracting weather data: {e}")
            return {'available': False}
    
    def _extract_driver_data(self, sessions: Dict) -> Dict:
        """Extract comprehensive driver data from all sessions."""
        drivers = {}
        
        # Process Race results
        if 'Race' in sessions:
            for driver in sessions['Race']['results']:
                driver_code = driver['driver_code']
                if driver_code:
                    drivers[driver_code] = {
                        'name': f"{driver['first_name']} {driver['last_name']}".strip(),
                        'team': driver['team'],
                        'race_position': driver['position'],
                        'race_points': driver['points'],
                        'race_status': driver['status']
                    }
        
        # Add Qualifying results
        if 'Qualifying' in sessions:
            for driver in sessions['Qualifying']['results']:
                driver_code = driver['driver_code']
                if driver_code in drivers:
                    drivers[driver_code]['qualifying_position'] = driver['position']
                    drivers[driver_code]['qualifying_time'] = driver['time']
        
        # Add lap analysis
        for session_name, session_data in sessions.items():
            if 'laps' in session_data:
                for driver_code, lap_data in session_data['laps'].get('drivers', {}).items():
                    if driver_code in drivers:
                        drivers[driver_code][f'{session_name.lower()}_analysis'] = lap_data
        
        return drivers
    
    def _extract_race_winner(self, race_session: Dict) -> Optional[str]:
        """Extract race winner from race session data."""
        try:
            for driver in race_session['results']:
                if driver['position'] == 1:
                    return driver['driver_code']
            return None
        except Exception:
            return None
    
    def _calculate_consistency(self, lap_times: pd.Series) -> float:
        """Calculate lap time consistency (lower is better)."""
        try:
            if len(lap_times) <= 1:
                return 1.0
            
            # Remove outliers (laps >10% slower than fastest)
            fastest = lap_times.min()
            valid_times = lap_times[lap_times <= fastest * 1.1]
            
            if len(valid_times) <= 1:
                return 0.5
            
            # Calculate coefficient of variation
            cv = valid_times.std() / valid_times.mean()
            
            # Convert to 0-1 scale (1 = most consistent)
            return max(0.0, 1.0 - (cv * 10))
            
        except Exception:
            return 0.5
    
    def _safe_get(self, series_or_dict, key: str, default):
        """Safely get value from pandas Series or dict."""
        try:
            if hasattr(series_or_dict, 'get'):
                return series_or_dict.get(key, default)
            else:
                return getattr(series_or_dict, key, default)
        except (KeyError, AttributeError):
            return default
