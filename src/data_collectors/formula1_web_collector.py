"""
Enhanced Formula 1 website data collector with debugging and persistence.
"""

import requests
import logging
import json
import csv
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
import os

# Import settings for data directory
from config.settings import BASE_DIR

logger = logging.getLogger(__name__)

class Formula1WebCollector:
    """Enhanced F1.com collector with data persistence and debugging."""
    
    def __init__(self):
        self.base_url = "https://www.formula1.com/en/results/2025/races"
        self.race_mappings = self._load_2025_race_mappings()
        
        # Create data persistence directories
        self.data_dir = BASE_DIR / "data" / "f1_parsed_data"
        self.debug_dir = BASE_DIR / "data" / "debug_html"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.debug_dir.mkdir(parents=True, exist_ok=True)
        
    def _load_2025_race_mappings(self) -> Dict:
        """CORRECTED 2025 F1 race ID mappings - Your Updated Version."""
        return {
            'australian_gp': {'id': '1254', 'name': 'australia'},
            'chinese_gp': {'id': '1255', 'name': 'china'},
            'japanese_gp': {'id': '1256', 'name': 'japan'},
            'bahrain_gp': {'id': '1257', 'name': 'bahrain'},
            'saudi_arabian_gp': {'id': '1258', 'name': 'saudi-arabia'},
            'miami_gp': {'id': '1259', 'name': 'miami'},
            'emilia_romagna_gp': {'id': '1260', 'name': 'emilia-romagna'},
            'monaco_gp': {'id': '1261', 'name': 'monaco'},
            'spanish_gp': {'id': '1262', 'name': 'spain'},
            'canadian_gp': {'id': '1263', 'name': 'canada'},
            'austrian_gp': {'id': '1264', 'name': 'austria'},
            'british_gp': {'id': '1277', 'name': 'great-britain'},  # Verified correct
            'belgian_gp': {'id': '1265', 'name': 'belgium'},        # Verified correct
            'hungarian_gp': {'id': '1266', 'name': 'hungary'},      # Verified correct
            'dutch_gp': {'id': '1267', 'name': 'netherlands'},
            'italian_gp': {'id': '1268', 'name': 'italy'},
            'azerbaijan_gp': {'id': '1269', 'name': 'azerbaijan'},
            'singapore_gp': {'id': '1270', 'name': 'singapore'},
            'united_states_gp': {'id': '1271', 'name': 'united-states'},
            'mexico_city_gp': {'id': '1272', 'name': 'mexico'},
            'sao_paulo_gp': {'id': '1273', 'name': 'brazil'},
            'las_vegas_gp': {'id': '1274', 'name': 'las-vegas'},
            'qatar_gp': {'id': '1275', 'name': 'qatar'},
            'abu_dhabi_gp': {'id': '1276', 'name': 'abu-dhabi'}
        }
    
    def get_session_data(self, gp_name: str, session_type: str) -> Dict:
        """Enhanced session data collection with persistence."""
        try:
            circuit_key = self._get_circuit_key(gp_name)
            if not circuit_key:
                logger.error(f"Could not map GP name '{gp_name}' to circuit key")
                return {}
            
            race_info = self.race_mappings.get(circuit_key)
            if not race_info:
                logger.error(f"No race mapping found for {circuit_key}")
                return {}
            
            url = f"{self.base_url}/{race_info['id']}/{race_info['name']}/{session_type}"
            logger.info(f"🔗 Fetching {session_type} data from: {url}")
            
            # Add headers to mimic browser request
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                # Save raw HTML for debugging
                self._save_raw_html(gp_name, session_type, response.text)
                
                # Parse the data
                parsed_data = self._parse_session_data(response.text, session_type)
                
                # Save parsed data
                self._save_parsed_data(gp_name, session_type, parsed_data)
                
                return parsed_data
            else:
                logger.error(f"HTTP {response.status_code} for {url}")
                logger.error(f"Response content preview: {response.text[:500]}...")
                return {}
                
        except Exception as e:
            logger.error(f"Error fetching session data: {e}")
            return {}
    
    def _save_raw_html(self, gp_name: str, session_type: str, html_content: str):
        """Save raw HTML for debugging."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{gp_name.replace(' ', '_')}_{session_type.replace('/', '_')}_{timestamp}.html"
            filepath = self.debug_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.debug(f"💾 Saved raw HTML to: {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving raw HTML: {e}")
    
    def _save_parsed_data(self, gp_name: str, session_type: str, parsed_data: Dict):
        """Save parsed data in multiple formats."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_filename = f"{gp_name.replace(' ', '_')}_{session_type.replace('/', '_')}_{timestamp}"
            
            # Save as JSON
            json_filepath = self.data_dir / f"{base_filename}.json"
            with open(json_filepath, 'w', encoding='utf-8') as f:
                json.dump(parsed_data, f, indent=2, ensure_ascii=False)
            
            # Save as CSV (if results available)
            if parsed_data.get('results'):
                csv_filepath = self.data_dir / f"{base_filename}.csv"
                self._save_as_csv(parsed_data['results'], csv_filepath)
            
            # Save summary as TXT
            txt_filepath = self.data_dir / f"{base_filename}_summary.txt"
            self._save_summary_txt(gp_name, session_type, parsed_data, txt_filepath)
            
            logger.info(f"💾 Saved parsed data to: {json_filepath}")
            
        except Exception as e:
            logger.error(f"Error saving parsed data: {e}")
    
    def _save_as_csv(self, results: List[Dict], filepath: Path):
        """Save results as CSV."""
        try:
            if not results:
                return
            
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                fieldnames = results[0].keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(results)
            
        except Exception as e:
            logger.error(f"Error saving CSV: {e}")
    
    def _save_summary_txt(self, gp_name: str, session_type: str, data: Dict, filepath: Path):
        """Save human-readable summary."""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"F1 DATA EXTRACTION SUMMARY\n")
                f.write(f"=" * 50 + "\n")
                f.write(f"GP: {gp_name}\n")
                f.write(f"Session: {session_type}\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write(f"Data Available: {data.get('available', data.get('session_available', False))}\n")
                f.write(f"\n")
                
                # Session-specific summary
                if session_type == "qualifying":
                    f.write(f"QUALIFYING RESULTS:\n")
                    f.write(f"Pole Position: {data.get('pole_position', 'Unknown')}\n")
                    f.write(f"Pole Time: {data.get('pole_time', 'Unknown')}\n")
                else:
                    f.write(f"PRACTICE RESULTS:\n")
                    f.write(f"Fastest Driver: {data.get('fastest_driver', 'Unknown')}\n")
                    f.write(f"Fastest Time: {data.get('fastest_time', 'Unknown')}\n")
                
                f.write(f"\nTOP 10 RESULTS:\n")
                f.write(f"-" * 30 + "\n")
                
                results = data.get('results', [])
                if results:
                    for i, result in enumerate(results[:10], 1):
                        driver = result.get('driver', 'Unknown')
                        time = result.get('time', 'Unknown')
                        f.write(f"{i:2d}. {driver:<20} {time}\n")
                else:
                    f.write("No results found\n")
                
                f.write(f"\nRAW DATA STRUCTURE:\n")
                f.write(f"-" * 30 + "\n")
                f.write(json.dumps(data, indent=2))
                
        except Exception as e:
            logger.error(f"Error saving summary: {e}")
    
    def _parse_session_data(self, html_content: str, session_type: str) -> Dict:
        """Enhanced parsing with better HTML structure detection."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Debug: Save structure info
            self._log_html_structure(soup, session_type)
            
            if session_type == "qualifying":
                return self._parse_qualifying_data_enhanced(soup)
            else:
                return self._parse_practice_data_enhanced(soup, session_type)
                
        except Exception as e:
            logger.error(f"Error parsing session data: {e}")
            return {}
    
    def _log_html_structure(self, soup: BeautifulSoup, session_type: str):
        """Log HTML structure for debugging."""
        try:
            # Find all tables
            tables = soup.find_all('table')
            logger.info(f"🔍 Found {len(tables)} table(s) in HTML")
            
            # Look for common F1.com classes
            result_tables = soup.find_all('div', class_=lambda x: x and 'result' in x.lower())
            logger.info(f"🔍 Found {len(result_tables)} result div(s)")
            
            # Look for data tables
            data_tables = soup.find_all(['table', 'div'], attrs={'data-test': True})
            logger.info(f"🔍 Found {len(data_tables)} data-test element(s)")
            
            # Check for "no results" indicators
            no_results = soup.find_all(text=lambda text: text and 'no results' in text.lower())
            if no_results:
                logger.warning(f"⚠️  Found 'no results' text in HTML")
            
            # Look for qualifying/practice specific elements
            if session_type == "qualifying":
                pole_elements = soup.find_all(text=lambda text: text and 'pole' in text.lower())
                logger.info(f"🔍 Found {len(pole_elements)} 'pole' references")
            
        except Exception as e:
            logger.debug(f"Error logging HTML structure: {e}")
    
    def _parse_qualifying_data_enhanced(self, soup: BeautifulSoup) -> Dict:
        """Enhanced qualifying data parsing with F1.com 2025 support."""
        results = {
            'available': False,
            'pole_position': '',
            'pole_time': '',
            'results': [],
            'parsing_attempts': [],
            'grid_positions': {}
        }
        
        try:
            # Method 1: Standard table parsing
            table = soup.find('table')
            if table:
                results['parsing_attempts'].append("Method 1: Standard F1.com table found")
                parsed = self._parse_standard_table(table, "qualifying")
                if parsed['results']:
                    results.update(parsed)
                    results['available'] = True
                    
                    # Create grid positions mapping for easy access
                    for result in parsed['results']:
                        driver_code = result['driver_code']
                        if driver_code:
                            results['grid_positions'][driver_code] = result['position']
                    
                    logger.info(f"✅ Qualifying parsing successful: {len(parsed['results'])} results")
                    logger.info(f"🏁 Pole Position: {results['pole_position']} - {results['pole_time']}")
                    return results
            
            results['parsing_attempts'].append("No qualifying table found")
            logger.warning(f"⚠️ No qualifying data extracted")
            
        except Exception as e:
            logger.error(f"Error in enhanced qualifying parsing: {e}")
            results['parsing_attempts'].append(f"Error: {str(e)}")
        
        return results
    
    def _parse_practice_data_enhanced(self, soup: BeautifulSoup, session_type: str) -> Dict:
        """Enhanced practice data parsing."""
        results = {
            'session_available': False,
            'session_name': session_type.title(),
            'results': [],
            'fastest_driver': '',
            'fastest_time': '',
            'parsing_attempts': []
        }
        
        try:
            # Multiple parsing attempts
            table = soup.find('table')
            if table:
                results['parsing_attempts'].append("Standard table found")
                parsed = self._parse_standard_table(table, "practice")
                if parsed['results']:
                    results.update(parsed)
                    results['session_available'] = True
                    logger.info(f"✅ Practice parsing successful: {len(parsed['results'])} results")
                    return results
            
            results['parsing_attempts'].append("No standard table found")
            logger.warning(f"⚠️  No practice data found for {session_type}")
            
        except Exception as e:
            logger.error(f"Error in enhanced practice parsing: {e}")
            results['parsing_attempts'].append(f"Error: {str(e)}")
        
        return results
    
    def _parse_standard_table(self, table, session_type: str) -> Dict:
        """Enhanced F1.com table parsing for 2025 format."""
        results = {'results': [], 'pole_position': '', 'pole_time': '', 'fastest_driver': '', 'fastest_time': ''}
        
        try:
            rows = table.find_all('tr')
            logger.info(f"🔍 Found {len(rows)} rows in table")
            
            if len(rows) <= 1:
                return results
            
            # Skip header row
            data_rows = rows[1:]
            
            for i, row in enumerate(data_rows):
                cells = row.find_all(['td', 'th'])
                
                if len(cells) >= 7:  # F1.com qualifying table has multiple columns
                    try:
                        # Extract data based on F1.com 2025 structure
                        pos_cell = cells[0].get_text(strip=True)
                        number_cell = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                        driver_cell = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                        team_cell = cells[3].get_text(strip=True) if len(cells) > 3 else ""
                        
                        # Get qualifying times (Q1, Q2, Q3)
                        q1_time = cells[4].get_text(strip=True) if len(cells) > 4 else ""
                        q2_time = cells[5].get_text(strip=True) if len(cells) > 5 else ""
                        q3_time = cells[6].get_text(strip=True) if len(cells) > 6 else ""
                        
                        # Choose best time available (priority: Q3 > Q2 > Q1)
                        best_time = ""
                        if q3_time and ':' in q3_time and 'NC' not in q3_time:
                            best_time = q3_time
                        elif q2_time and ':' in q2_time and 'NC' not in q2_time:
                            best_time = q2_time
                        elif q1_time and ':' in q1_time and 'NC' not in q1_time:
                            best_time = q1_time
                        
                        if pos_cell.isdigit() and driver_cell:
                            position = int(pos_cell)
                            
                            # Extract driver code (usually last 3 chars before team info)
                            driver_code = ""
                            if len(driver_cell) >= 3:
                                # Look for 3-letter code pattern
                                import re
                                code_match = re.search(r'([A-Z]{3})$', driver_cell)
                                if code_match:
                                    driver_code = code_match.group(1)
                                    driver_name = driver_cell[:-3].strip()
                                else:
                                    driver_code = driver_cell[-3:]
                                    driver_name = driver_cell[:-3] if len(driver_cell) > 3 else driver_cell
                            else:
                                driver_name = driver_cell
                                driver_code = driver_cell[:3] if len(driver_cell) >= 3 else driver_cell
                            
                            result = {
                                'position': position,
                                'driver': driver_name,
                                'driver_code': driver_code,
                                'team': team_cell,
                                'number': number_cell,
                                'time': best_time,
                                'q1': q1_time,
                                'q2': q2_time,
                                'q3': q3_time
                            }
                            results['results'].append(result)
                            
                            # Set pole position (position 1)
                            if position == 1:
                                if session_type == "qualifying":
                                    results['pole_position'] = driver_name
                                    results['pole_time'] = best_time
                                    logger.info(f"🏁 POLE POSITION: {driver_name} ({driver_code}) - {best_time}")
                                else:
                                    results['fastest_driver'] = driver_name
                                    results['fastest_time'] = best_time
                            
                            logger.debug(f"✅ Parsed: P{position} {driver_name} ({driver_code}) - {best_time}")
                            
                    except (ValueError, IndexError) as e:
                        logger.debug(f"Error parsing row {i+1}: {e}")
                        continue
            
            logger.info(f"✅ Successfully parsed {len(results['results'])} results")
            
        except Exception as e:
            logger.error(f"Error in standard table parsing: {e}")
        
        return results
    
    def _get_circuit_key(self, gp_name: str) -> Optional[str]:
        """Enhanced circuit key mapping with all 2025 GPs."""
        gp_lower = gp_name.lower().strip()
        
        mappings = {
            # All 2025 GP mappings
            'australian': 'australian_gp',
            'australia': 'australian_gp',
            'melbourne': 'australian_gp',
            'chinese': 'chinese_gp',
            'china': 'chinese_gp',
            'shanghai': 'chinese_gp',
            'japanese': 'japanese_gp',
            'japan': 'japanese_gp',
            'suzuka': 'japanese_gp',
            'bahrain': 'bahrain_gp',
            'sakhir': 'bahrain_gp',
            'saudi arabian': 'saudi_arabian_gp',
            'saudi arabia': 'saudi_arabian_gp',
            'jeddah': 'saudi_arabian_gp',
            'miami': 'miami_gp',
            'emilia romagna': 'emilia_romagna_gp',
            'imola': 'emilia_romagna_gp',
            'monaco': 'monaco_gp',
            'monte carlo': 'monaco_gp',
            'spanish': 'spanish_gp',
            'spain': 'spanish_gp',
            'barcelona': 'spanish_gp',
            'canadian': 'canadian_gp',
            'canada': 'canadian_gp',
            'montreal': 'canadian_gp',
            'austrian': 'austrian_gp',
            'austria': 'austrian_gp',
            'red bull ring': 'austrian_gp',
            'british': 'british_gp',
            'great britain': 'british_gp',
            'silverstone': 'british_gp',
            'belgian': 'belgian_gp',
            'belgium': 'belgian_gp',
            'spa': 'belgian_gp',
            'hungarian': 'hungarian_gp',
            'hungary': 'hungarian_gp',
            'hungaroring': 'hungarian_gp',
            'budapest': 'hungarian_gp',
            'dutch': 'dutch_gp',
            'netherlands': 'dutch_gp',
            'zandvoort': 'dutch_gp',
            'italian': 'italian_gp',
            'italy': 'italian_gp',
            'monza': 'italian_gp',
            'azerbaijan': 'azerbaijan_gp',
            'baku': 'azerbaijan_gp',
            'singapore': 'singapore_gp',
            'marina bay': 'singapore_gp',
            'united states': 'united_states_gp',
            'usa': 'united_states_gp',
            'austin': 'united_states_gp',
            'cota': 'united_states_gp',
            'mexico': 'mexico_city_gp',
            'mexico city': 'mexico_city_gp',
            'brazil': 'sao_paulo_gp',
            'sao paulo': 'sao_paulo_gp',
            'interlagos': 'sao_paulo_gp',
            'las vegas': 'las_vegas_gp',
            'vegas': 'las_vegas_gp',
            'qatar': 'qatar_gp',
            'lusail': 'qatar_gp',
            'abu dhabi': 'abu_dhabi_gp',
            'yas marina': 'abu_dhabi_gp'
        }
        
        for key, circuit_key in mappings.items():
            if key in gp_lower:
                return circuit_key
        
        return None

    def get_practice_1_data(self, gp_name: str) -> Dict:
        """Get Practice 1 data with persistence."""
        return self.get_session_data(gp_name, "practice/1")

    def get_practice_2_data(self, gp_name: str) -> Dict:
        """Get Practice 2 data with persistence."""
        return self.get_session_data(gp_name, "practice/2")

    def get_practice_3_data(self, gp_name: str) -> Dict:
        """Get Practice 3 data with persistence."""
        return self.get_session_data(gp_name, "practice/3")

    def get_qualifying_data(self, gp_name: str) -> Dict:
        """Get qualifying data with persistence."""
        return self.get_session_data(gp_name, "qualifying")

    def get_race_results(self, gp_name: str) -> Dict:
        """Get race results with persistence."""
        return self.get_session_data(gp_name, "race-result")
