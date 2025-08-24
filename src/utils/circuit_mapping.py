"""
Enhanced circuit name mapping and standardization utilities with complete 2025 support.
"""

import json
import logging
from typing import Dict, Optional, List
from pathlib import Path
from config.settings import BASE_DIR

logger = logging.getLogger(__name__)

class CircuitMapper:
    """Enhanced circuit mapper with complete 2025 GP support."""
    
    def __init__(self):
        self.circuits = self._load_circuits()
        self.name_mappings = self._create_comprehensive_mappings()
        
    def get_circuit_key(self, input_name: str) -> Optional[str]:
        """Enhanced circuit key detection for any input variation."""
        if not input_name:
            return None
        
        input_lower = input_name.lower().strip()
        
        # Direct key match first
        direct_match = input_lower.replace(' ', '_').replace('-', '_')
        if direct_match + '_gp' in self.circuits:
            return direct_match + '_gp'
        
        # Comprehensive mapping search
        for circuit_key, names in self.name_mappings.items():
            if input_lower in names:
                logger.info(f"🎯 Mapped '{input_name}' to {circuit_key}")
                return circuit_key
        
        # Partial matching for flexibility
        for circuit_key, names in self.name_mappings.items():
            for name in names:
                if input_lower in name or name in input_lower:
                    logger.info(f"🎯 Partial match '{input_name}' to {circuit_key}")
                    return circuit_key
        
        logger.warning(f"❌ Circuit mapping failed for: {input_name}")
        return None
    
    def get_circuit_info(self, circuit_key: str) -> Dict:
        """Get complete circuit information with coordinates validation."""
        circuit_info = self.circuits.get(circuit_key, {})
        
        # Validate coordinates for weather API
        location = circuit_info.get('location', {})
        coordinates = location.get('coordinates', [])
        
        if len(coordinates) != 2:
            logger.error(f"Invalid coordinates for {circuit_key}: {coordinates}")
            return {}
        
        return circuit_info
    
    def _load_circuits(self) -> Dict:
        """Load circuit configurations with error handling."""
        try:
            config_path = BASE_DIR / "config" / "circuits.json"
            with open(config_path, 'r', encoding='utf-8') as f:
                circuits = json.load(f)
            logger.info(f"✅ Loaded {len(circuits)} circuit configurations")
            return circuits
        except Exception as e:
            logger.error(f"❌ Error loading circuits: {e}")
            return {}
    
    def _create_comprehensive_mappings(self) -> Dict:
        """Create comprehensive name mappings for all 2025 GPs."""
        mappings = {}
        
        # Enhanced mappings for every 2025 GP
        enhanced_mappings = {
            # Australian GP
            ('australian', 'australia', 'melbourne', 'albert park'): 'australian_gp',
            
            # Chinese GP
            ('chinese', 'china', 'shanghai'): 'chinese_gp',
            
            # Japanese GP  
            ('japanese', 'japan', 'suzuka'): 'japanese_gp',
            
            # Bahrain GP
            ('bahrain', 'sakhir', 'bahraini'): 'bahrain_gp',
            
            # Saudi Arabian GP
            ('saudi arabian', 'saudi arabia', 'jeddah', 'saudi'): 'saudi_arabian_gp',
            
            # Miami GP
            ('miami', 'hard rock', 'miami international'): 'miami_gp',
            
            # Emilia Romagna GP
            ('emilia romagna', 'emilia-romagna', 'imola', 'enzo ferrari'): 'emilia_romagna_gp',
            
            # Monaco GP
            ('monaco', 'monte carlo', 'principality'): 'monaco_gp',
            
            # Spanish GP
            ('spanish', 'spain', 'barcelona', 'catalunya', 'catalonia'): 'spanish_gp',
            
            # Canadian GP
            ('canadian', 'canada', 'montreal', 'gilles villeneuve'): 'canadian_gp',
            
            # Austrian GP
            ('austrian', 'austria', 'red bull ring', 'spielberg'): 'austrian_gp',
            
            # British GP
            ('british', 'great britain', 'uk', 'silverstone', 'britain'): 'british_gp',
            
            # Belgian GP
            ('belgian', 'belgium', 'spa', 'spa-francorchamps', 'francorchamps'): 'belgian_gp',
            
            # Hungarian GP
            ('hungarian', 'hungary', 'hungaroring', 'budapest'): 'hungarian_gp',
            
            # Dutch GP
            ('dutch', 'netherlands', 'zandvoort', 'holland'): 'dutch_gp',
            
            # Italian GP
            ('italian', 'italy', 'monza'): 'italian_gp',
            
            # Azerbaijan GP
            ('azerbaijan', 'azerbaijani', 'baku', 'baku city'): 'azerbaijan_gp',
            
            # Singapore GP
            ('singapore', 'marina bay', 'singaporean'): 'singapore_gp',
            
            # United States GP
            ('united states', 'usa', 'austin', 'cota', 'americas', 'us'): 'united_states_gp',
            
            # Mexico City GP
            ('mexico', 'mexico city', 'mexican', 'hermanos rodriguez'): 'mexico_city_gp',
            
            # São Paulo GP
            ('brazil', 'brazilian', 'sao paulo', 'são paulo', 'interlagos'): 'sao_paulo_gp',
            
            # Las Vegas GP
            ('las vegas', 'vegas', 'las vegas strip', 'strip'): 'las_vegas_gp',
            
            # Qatar GP
            ('qatar', 'qatari', 'lusail'): 'qatar_gp',
            
            # Abu Dhabi GP
            ('abu dhabi', 'emirates', 'uae', 'yas marina'): 'abu_dhabi_gp'
        }
        
        # Build comprehensive mappings
        for variations, circuit_key in enhanced_mappings.items():
            names = set()
            
            # Add all variations
            for variation in variations:
                names.add(variation)
                names.add(variation.replace(' ', ''))
                names.add(variation.replace('-', ' '))
                names.add(variation + ' grand prix')
                names.add(variation + ' gp')
            
            # Add official names from config
            if circuit_key in self.circuits:
                circuit_data = self.circuits[circuit_key]
                for official_name in circuit_data.get('official_names', []):
                    names.add(official_name.lower())
                for alias in circuit_data.get('aliases', []):
                    names.add(alias.lower())
            
            mappings[circuit_key] = names
        
        logger.info(f"✅ Created mappings for {len(mappings)} circuits")
        return mappings
    
    def list_available_circuits(self) -> List[str]:
        """Get list of all available 2025 circuits."""
        circuits = []
        for circuit_key, circuit_data in self.circuits.items():
            official_names = circuit_data.get('official_names', [])
            if official_names:
                circuits.append(official_names[0])
        return sorted(circuits)
    
    def suggest_circuit_name(self, input_name: str) -> List[str]:
        """Enhanced circuit name suggestions."""
        if not input_name:
            return []
        
        input_lower = input_name.lower()
        suggestions = []
        
        # Look for partial matches
        for circuit_key, names in self.name_mappings.items():
            circuit_info = self.circuits.get(circuit_key, {})
            official_name = circuit_info.get('official_names', [''])[0]
            
            # Check for any partial match
            for name in names:
                if any(word in name for word in input_lower.split()) or \
                   any(word in input_lower for word in name.split()):
                    if official_name not in suggestions:
                        suggestions.append(official_name)
                    break
        
        return suggestions[:5]
    
    def validate_coordinates(self, circuit_key: str) -> bool:
        """Validate circuit coordinates for weather API."""
        circuit_info = self.circuits.get(circuit_key, {})
        location = circuit_info.get('location', {})
        coordinates = location.get('coordinates', [])
        
        if len(coordinates) != 2:
            return False
        
        lat, lon = coordinates
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return False
        
        return True
    
    def get_weather_coordinates(self, circuit_key: str) -> tuple:
        """Get validated weather coordinates."""
        if not self.validate_coordinates(circuit_key):
            logger.error(f"Invalid coordinates for {circuit_key}")
            return None, None
        
        circuit_info = self.circuits[circuit_key]
        coordinates = circuit_info['location']['coordinates']
        return coordinates[0], coordinates[1]
