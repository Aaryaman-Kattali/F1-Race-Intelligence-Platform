"""
Process current season data from Perplexity intelligence.
"""

import logging
from typing import Dict, List, Optional
import re
from datetime import datetime

logger = logging.getLogger(__name__)

class CurrentProcessor:
    """Process current 2025 F1 season data."""
    
    def __init__(self):
        self.driver_mappings = self._create_driver_mappings()
    
    def process_current_intelligence(self, intelligence_data: Dict) -> Dict:
        """
        Process current F1 intelligence data into structured format.
        
        Args:
            intelligence_data: Raw data from Perplexity API
            
        Returns:
            Processed current season data
        """
        try:
            processed_data = {
                'standings': self._process_standings(intelligence_data.get('standings', {})),
                'recent_form': self._process_form_analysis(intelligence_data.get('recent_form', {})),
                'team_updates': self._process_team_updates(intelligence_data.get('team_updates', {})),
                'circuit_specific': self._process_circuit_intelligence(intelligence_data.get('circuit_specific', {})),
                'processed_timestamp': datetime.now().isoformat()
            }
            
            return processed_data
            
        except Exception as e:
            logger.error(f"Error processing current intelligence: {e}")
            return {'error': str(e)}
    
    def _process_standings(self, standings_data: Dict) -> Dict:
        """Process championship standings data."""
        processed_standings = {
            'drivers': [],
            'constructors': [],
            'races_completed': 0,
            'last_updated': datetime.now().isoformat()
        }
        
        try:
            # Process driver standings
            drivers = standings_data.get('drivers', [])
            for driver in drivers:
                driver_code = self._normalize_driver_code(driver.get('name', ''))
                if not driver_code:
                    driver_code = driver.get('code', 'UNK')
                
                processed_driver = {
                    'code': driver_code,
                    'name': driver.get('name', ''),
                    'position': int(driver.get('position', 0)),
                    'points': float(driver.get('points', 0)),
                    'team': self._normalize_team_name(driver.get('team', '')),
                    'form_score': self._calculate_form_score(driver.get('position', 15))
                }
                processed_standings['drivers'].append(processed_driver)
            
            # Process constructor standings
            constructors = standings_data.get('constructors', [])
            for constructor in constructors:
                processed_constructor = {
                    'team': self._normalize_team_name(constructor.get('team', '')),
                    'position': int(constructor.get('position', 0)),
                    'points': float(constructor.get('points', 0)),
                    'performance_tier': self._classify_team_performance(constructor.get('position', 10))
                }
                processed_standings['constructors'].append(processed_constructor)
            
            processed_standings['races_completed'] = standings_data.get('races_completed', 0)
            
        except Exception as e:
            logger.error(f"Error processing standings: {e}")
        
        return processed_standings
    
    def _process_form_analysis(self, form_data: Dict) -> Dict:
        """Process recent form analysis."""
        processed_form = {
            'drivers_in_form': [],
            'drivers_struggling': [],
            'team_trends': {},
            'momentum_analysis': {},
            'reliability_issues': []
        }
        
        try:
            if form_data.get('analysis_available'):
                # Parse form analysis text (this would be enhanced with NLP)
                analysis_text = form_data.get('momentum_analysis', '')
                
                # Extract drivers in form (simplified pattern matching)
                in_form_patterns = [
                    r'(\w{3})\s+(?:is|has been)\s+(?:performing|driving)\s+(?:well|excellently)',
                    r'(\w{3})\s+(?:showing|demonstrating)\s+(?:strong|excellent)\s+form',
                    r'(?:strong|good)\s+form.*?(\w{3})'
                ]
                
                for pattern in in_form_patterns:
                    matches = re.findall(pattern, analysis_text, re.IGNORECASE)
                    for match in matches:
                        driver_code = match.upper()
                        if len(driver_code) == 3 and driver_code not in processed_form['drivers_in_form']:
                            processed_form['drivers_in_form'].append(driver_code)
                
                # Extract struggling drivers
                struggling_patterns = [
                    r'(\w{3})\s+(?:struggling|having\s+difficulty)',
                    r'(\w{3})\s+(?:underperforming|disappointing)',
                    r'poor.*?form.*?(\w{3})'
                ]
                
                for pattern in struggling_patterns:
                    matches = re.findall(pattern, analysis_text, re.IGNORECASE)
                    for match in matches:
                        driver_code = match.upper()
                        if len(driver_code) == 3 and driver_code not in processed_form['drivers_struggling']:
                            processed_form['drivers_struggling'].append(driver_code)
            
        except Exception as e:
            logger.error(f"Error processing form analysis: {e}")
        
        return processed_form
    
    def _process_team_updates(self, team_data: Dict) -> Dict:
        """Process team updates and news."""
        processed_updates = {
            'driver_changes': [],
            'technical_updates': [],
            'reliability_updates': [],
            'personnel_changes': [],
            'penalties': []
        }
        
        try:
            if team_data.get('updates_available'):
                update_text = team_data.get('update_text', '')
                
                # Extract driver changes
                driver_change_patterns = [
                    r'(\w+)\s+(?:replaces|replacing|joins|leaves)',
                    r'driver\s+change.*?(\w+)',
                    r'(\w+)\s+out.*?(?:injury|illness)'
                ]
                
                for pattern in driver_change_patterns:
                    matches = re.findall(pattern, update_text, re.IGNORECASE)
                    for match in matches:
                        processed_updates['driver_changes'].append({
                            'description': match,
                            'impact': 'medium'  # Would be enhanced with sentiment analysis
                        })
                
                # Extract technical updates
                tech_patterns = [
                    r'(?:upgrade|update|development).*?(\w+)',
                    r'(?:aerodynamic|engine|suspension).*?(?:improvement|change)',
                    r'new.*?(?:floor|wing|sidepod)'
                ]
                
                for pattern in tech_patterns:
                    matches = re.findall(pattern, update_text, re.IGNORECASE)
                    for match in matches:
                        processed_updates['technical_updates'].append({
                            'description': match,
                            'expected_impact': 'positive'
                        })
            
        except Exception as e:
            logger.error(f"Error processing team updates: {e}")
        
        return processed_updates
    
    def _process_circuit_intelligence(self, circuit_data: Dict) -> Dict:
        """Process circuit-specific intelligence."""
        processed_circuit = {
            'circuit_specialists': [],
            'team_advantages': {},
            'recent_developments': [],
            'confidence_factors': {}
        }
        
        try:
            if circuit_data.get('circuit_analysis_available'):
                analysis_text = circuit_data.get('analysis_text', '')
                
                # Extract circuit specialists
                specialist_patterns = [
                    r'(\w{3})\s+(?:excels|performs well|strong).*?(?:at|on)\s+(?:this|the)\s+(?:circuit|track)',
                    r'(?:good|strong).*?(?:at|on).*?(?:this|the).*?(?:circuit|track).*?(\w{3})',
                    r'(\w{3}).*?(?:specialist|expert).*?(?:at|on)'
                ]
                
                for pattern in specialist_patterns:
                    matches = re.findall(pattern, analysis_text, re.IGNORECASE)
                    for match in matches:
                        driver_code = match.upper()
                        if len(driver_code) == 3:
                            processed_circuit['circuit_specialists'].append(driver_code)
            
        except Exception as e:
            logger.error(f"Error processing circuit intelligence: {e}")
        
        return processed_circuit
    
    def _normalize_driver_code(self, driver_name: str) -> str:
        """Convert driver name to 3-letter code with dynamic assignment for new drivers."""
        if not driver_name:
            return ""

        # Check if already a 3-letter code
        name_clean = driver_name.strip().upper()
        if len(name_clean) == 3 and name_clean.isalpha():
            return name_clean

        # Check existing mapping first
        name_lower = driver_name.lower().strip()
        if name_lower in self.driver_mappings:
            return self.driver_mappings[name_lower]

        # Dynamic assignment for new drivers
        return self._generate_driver_code(driver_name)
    
    def _generate_driver_code(self, driver_name: str) -> str:
        """Generate 3-letter code for new drivers."""
        parts = driver_name.strip().split()
        
        if len(parts) >= 2:
            # Use first 3 letters of last name
            last_name = parts[-1]
            code = last_name[:3].upper()
        else:
            # Single name - use first 3 letters
            code = driver_name[:3].upper()
        
        # Ensure 3 characters
        if len(code) < 3:
            code = code.ljust(3, 'X')
        
        return code
    
    def _normalize_team_name(self, team_name: str) -> str:
        """Normalize team name to standard format."""
        if not team_name:
            return "Unknown"
        
        team_mappings = {
            'red bull racing': 'Red Bull Racing',
            'red bull': 'Red Bull Racing',
            'rbr': 'Red Bull Racing',
            'ferrari': 'Ferrari',
            'scuderia ferrari': 'Ferrari',
            'mercedes': 'Mercedes',
            'mercedes-amg': 'Mercedes',
            'mclaren': 'McLaren',
            'aston martin': 'Aston Martin',
            'alpine': 'Alpine',
            'williams': 'Williams',
            'alphatauri': 'AlphaTauri',
            'alfa romeo': 'Alfa Romeo',
            'haas': 'Haas F1 Team',
            'haas f1': 'Haas F1 Team'
        }
        
        team_lower = team_name.lower().strip()
        return team_mappings.get(team_lower, team_name.title())
    
    def _calculate_form_score(self, championship_position: int) -> float:
        """Calculate form score based on championship position."""
        # Higher position = better form (normalized 0-1)
        return max(0.1, (21 - championship_position) / 20.0)
    
    def _classify_team_performance(self, position: int) -> str:
        """Classify team performance tier."""
        if position <= 2:
            return 'top_tier'
        elif position <= 5:
            return 'upper_midfield'
        elif position <= 7:
            return 'midfield'
        else:
            return 'lower_tier'
    
    def _create_driver_mappings(self) -> Dict[str, str]:
        """Create comprehensive driver name to code mappings including 2025 rookies."""
        return {
            # Existing drivers...
            'max verstappen': 'VER',
            'lewis hamilton': 'HAM',
            'charles leclerc': 'LEC',
            'george russell': 'RUS',
            'carlos sainz': 'SAI',
            'lando norris': 'NOR',
            'oscar piastri': 'PIA',
            'fernando alonso': 'ALO',
            'lance stroll': 'STR',
            'sergio perez': 'PER',
            'pierre gasly': 'GAS',
            'esteban ocon': 'OCO',
            'alexander albon': 'ALB',
            'kevin magnussen': 'MAG',
            'nico hulkenberg': 'HUL',
            'valtteri bottas': 'BOT',
            'zhou guanyu': 'ZHO',
            'yuki tsunoda': 'TSU',
            'daniel ricciardo': 'RIC',
            
            # 2025 Expected New/Changed Drivers
            'isack hadjar': 'HAD',
            'hadjar': 'HAD',
            'jack doohan': 'DOO',
            'doohan': 'DOO',
            'gabriel bortoleto': 'BOR',
            'bortoleto': 'BOR',
            'kimi antonelli': 'ANT',
            'antonelli': 'ANT',
            'ollie bearman': 'BEA',
            'bearman': 'BEA',
            'franco colapinto': 'COL',
            'colapinto': 'COL',
            
            # Potential returnees
            'mick schumacher': 'MSC',
            'schumacher': 'MSC',
            'nyck de vries': 'DEV',
            'de vries': 'DEV',
        }
