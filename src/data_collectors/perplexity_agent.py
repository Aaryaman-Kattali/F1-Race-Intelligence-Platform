"""
Perplexity API integration for current F1 intelligence with intelligent text parsing.
"""

import requests
import json
import logging
import re
from typing import Dict, List, Optional
from datetime import datetime
import time
import re

from config.settings import PERPLEXITY_API_KEY, CURRENT_SEASON

logger = logging.getLogger(__name__)


class PerplexityAgent:
    """Collect current F1 intelligence using Perplexity API with intelligent text parsing."""

    def __init__(self):
        self.api_key = PERPLEXITY_API_KEY
        self.base_url = "https://api.perplexity.ai/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def get_current_standings_and_form(self, circuit_name: str) -> Dict:
        """Get current 2025 F1 intelligence for specific circuit with transparency."""

        if not self.api_key:
            logger.warning("Perplexity API key not configured")
            return self._get_fallback_data()

        logger.info(f"🔍 Getting current F1 intelligence for {circuit_name}")

        # Make the 3 API calls with detailed logging
        driver_data = self._get_current_driver_standings()
        team_data = self._get_current_team_standings()
        weekend_data = self._get_race_weekend_data(circuit_name)

        # TRANSPARENCY: Log what we actually got
        self._log_collected_data(driver_data, team_data, weekend_data)

        intelligence = {
            "driver_standings": driver_data,
            "team_standings": team_data,
            "race_weekend_data": weekend_data,
            "timestamp": datetime.now().isoformat(),
            "source": "perplexity_sonar_pro",
        }

        return intelligence

    def _log_collected_data(
        self, driver_data: Dict, team_data: Dict, weekend_data: Dict
    ):
        """Log transparency about what data was actually collected with TOP 10 details."""

        print("\n" + "=" * 60)
        print("🔍 PERPLEXITY API DATA TRANSPARENCY")
        print("=" * 60)

        # Driver standings transparency - TOP 10
        print(f"\n📊 DRIVER STANDINGS DATA:")
        if driver_data.get("standings_available"):
            drivers = driver_data.get("drivers", [])
            print(f"   ✅ Retrieved data for {len(drivers)} drivers")
            for i, driver in enumerate(drivers[:10], 1):  # TOP 10
                print(
                    f"   {i:2d}. {driver.get('name', 'Unknown')} ({driver.get('code', '???')}) - {driver.get('points', 0)} pts"
                )
            if len(drivers) > 10:
                print(f"   ... and {len(drivers)-10} more drivers")
        else:
            print("   ❌ No driver standings data available")
            print(
                f"   Raw response preview: {driver_data.get('raw_response', 'No response')[:200]}..."
            )

        # Team standings transparency - ALL 10 TEAMS
        print(f"\n🏁 TEAM STANDINGS DATA:")
        if team_data.get("standings_available"):
            teams = team_data.get("constructors", [])
            print(f"   ✅ Retrieved data for {len(teams)} teams")
            for i, team in enumerate(teams, 1):  # ALL TEAMS
                print(
                    f"   {i:2d}. {team.get('team', 'Unknown')} - {team.get('points', 0)} pts"
                )
        else:
            print("   ❌ No team standings data available")
            print(
                f"   Raw response preview: {team_data.get('raw_response', 'No response')[:200]}..."
            )

        # Enhanced Race weekend data transparency - TOP 10 for each session
        print(f"\n🏎️  RACE WEEKEND DATA:")
        if weekend_data.get("weekend_data_available"):
            sessions = weekend_data.get("sessions", {})

            # Display each session with TOP 10 results
            for session_name, session_data in sessions.items():
                print(f"\n   🏁 {session_name.upper()} RESULTS:")

                if session_data.get("available"):
                    if session_name == "Qualifying":
                        # Display qualifying with pole position and grid
                        pole_driver = session_data.get("pole_position", "Unknown")
                        pole_time = session_data.get("pole_time", "")
                        print(f"      🥇 POLE POSITION: {pole_driver} - {pole_time}")

                        # Display qualifying results if available
                        results = session_data.get("results", [])
                        if len(results) > 1:
                            print(f"      📊 TOP 10 QUALIFYING:")
                            for i, result in enumerate(results[:10], 1):
                                driver = result.get("driver", "Unknown")
                                time = result.get("time", "")
                                print(f"         {i:2d}. {driver} - {time}")

                    else:
                        # Display practice sessions
                        fastest_driver = session_data.get("fastest_driver", "Unknown")
                        fastest_time = session_data.get("fastest_time", "")
                        print(f"      ⚡ FASTEST: {fastest_driver} - {fastest_time}")

                        # Display practice results if available
                        results = session_data.get("results", [])
                        if len(results) > 1:
                            print(f"      📊 TOP 10 {session_name.upper()}:")
                            for i, result in enumerate(results[:10], 1):
                                driver = result.get("driver", "Unknown")
                                time = result.get("time", "")
                                print(f"         {i:2d}. {driver} - {time}")
                else:
                    print(f"      ❌ No {session_name} data available")
        else:
            print("   ❌ No race weekend data available")
            print(
                f"   Raw response preview: {weekend_data.get('raw_response', 'No response')[:200]}..."
            )

        print("=" * 60)

    def _get_current_driver_standings(self) -> Dict:
        """Get current 2025 F1 driver championship standings."""
        prompt = f"""
        Current Formula 1 {CURRENT_SEASON} driver championship standings:
        
        Please provide the complete and up-to-date driver standings with:
        1. All 20 current F1 drivers in championship order
        2. Driver names and their 3-letter codes (VER, HAM, LEC, etc.)
        3. Current points for each driver
        4. Championship positions (1st, 2nd, 3rd, etc.)
        5. Current teams for each driver
        6. Number of races completed so far in {CURRENT_SEASON}
        
        Include any new drivers who joined in {CURRENT_SEASON} season.
        Format the response clearly with driver positions, names, codes, teams, and points.
        """

        response = self._query_perplexity(prompt, "driver_standings")

        if response:
            return self._parse_driver_standings(response)
        else:
            return self._get_fallback_driver_standings()

    def _get_current_team_standings(self) -> Dict:
        """Get current 2025 F1 constructor championship standings."""
        prompt = f"""
        Current Formula 1 {CURRENT_SEASON} constructor/team championship standings:
        
        Please provide the complete and up-to-date constructor standings with:
        1. All 10 F1 teams in championship order
        2. Team names (Red Bull Racing, Ferrari, Mercedes, McLaren, etc.)
        3. Current constructor points for each team
        4. Championship positions (1st, 2nd, 3rd, etc.)
        5. Number of races completed so far in {CURRENT_SEASON}
        6. Any notable team performance trends
        
        Format the response clearly with team positions, names, and points.
        """

        response = self._query_perplexity(prompt, "team_standings")

        if response:
            return self._parse_team_standings(response)
        else:
            return self._get_fallback_team_standings()

    def _get_race_weekend_data(self, circuit_name: str) -> Dict:
        """Get current 2025 race weekend practice and qualifying data."""
        # Extract GP name for cleaner prompt
        gp_clean = circuit_name.replace("Grand Prix", "GP").replace(
            "Hungarian Grand Prix", "Hungarian GP"
        )

        prompt = f"""
        Formula 1 2025 Hungarian Grand Prix QUALIFYING and PRACTICE session results:
    
        I need the specific session results including:
        1. QUALIFYING RESULTS: Who got pole position? What was the pole time? Full Q1, Q2, Q3 results with times
        2. Grid positions 1-20 for the race start
        3. Practice session fastest times (FP1, FP2, FP3 fastest drivers and times)
        4. Any penalties affecting grid positions
        
        Please search for official F1 timing data, Formula1.com results, or motorsport news sources.
        The race has concluded so this data should be available.
        
        Focus on POLE POSITION winner and starting grid order specifically.
        """

        response = self._query_perplexity(prompt, f"race_weekend_{gp_clean}")

        if response:
            return self._parse_race_weekend_data(response)
        else:
            return self._get_fallback_race_weekend_data()

    def _query_perplexity(self, prompt: str, query_type: str) -> Optional[str]:
        """Make API call to Perplexity using supported models."""
        try:
            payload = {
                "model": "sonar-pro",  # ✅ Valid Perplexity model
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert Formula 1 analyst with access to real-time F1 data. Provide current, accurate, and detailed F1 information. Include specific numbers, positions, times, and points.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,
                "max_tokens": 2000,
                "stream": False,
            }

            logger.info(f"   🔍 Querying Perplexity (sonar-pro) for {query_type}")

            response = requests.post(
                self.base_url, headers=self.headers, json=payload, timeout=20
            )

            response.raise_for_status()

            result = response.json()
            content = result["choices"][0]["message"]["content"]
            logger.info(
                f"   ✅ Successfully retrieved {query_type} data from Perplexity"
            )
            return content

        except requests.exceptions.HTTPError as e:
            logger.error(
                f"HTTP error for {query_type}: {e.response.status_code} - {e.response.text}"
            )
            return None
        except Exception as e:
            logger.error(f"Error querying Perplexity for {query_type}: {e}")
            return None

    def _parse_driver_standings(self, response: str) -> Dict:
        """Enhanced driver standings parser with better pattern matching."""

        drivers = []
        races_completed = 0

        logger.info(
            f"📊 Raw driver standings response length: {len(response)} characters"
        )

        if not response or len(response) < 50:
            return self._get_fallback_driver_standings()

        try:
            # Extract races completed first
            races_match = re.search(
                r"after\s*(\d+)\s*races?\s*completed", response, re.IGNORECASE
            )
            if races_match:
                races_completed = int(races_match.group(1))
                logger.info(f"📊 Found {races_completed} races completed")

            # Enhanced patterns based on the actual response format
            patterns = [
                # "1. Oscar Piastri (PIA) - McLaren - 266 points"
                r"(\d+)\.?\s*([A-Za-z\s]+?)\s*\(([A-Z]{3})\)\s*[-–]\s*([A-Za-z\s]+?)\s*[-–]\s*(\d+)\s*points?",
                # "P1: Oscar Piastri (McLaren) - 266 pts"
                r"P(\d+):?\s*([A-Za-z\s]+?)\s*\(([A-Za-z\s]+?)\)\s*[-–]\s*(\d+)\s*(?:pts|points?)",
                # "1. Oscar Piastri - McLaren - 266"
                r"(\d+)\.?\s*([A-Za-z\s]+?)\s*[-–]\s*([A-Za-z\s]+?)\s*[-–]\s*(\d+)(?:\s*points?)?",
                # Multi-line format parsing
                r"(?:^|\n)\s*(\d+)\.?\s*([A-Za-z\s]+?)(?:\s*\(([A-Z]{3})\))?\s*[-–:]?\s*([A-Za-z\s]*?)\s*[-–:]?\s*(\d+)\s*(?:pts|points?)",
            ]

            # Show raw response for debugging
            logger.info(f"📊 Response preview: {response[:300]}...")

            for pattern_idx, pattern in enumerate(patterns):
                matches = re.findall(pattern, response, re.IGNORECASE | re.MULTILINE)

                if matches:
                    logger.info(
                        f"📊 Pattern {pattern_idx + 1} found {len(matches)} matches"
                    )

                    for match in matches[:20]:  # Top 20 drivers
                        try:
                            # Extract position and points (always present)
                            position = int(match[0])
                            name = self._clean_name(match[1])

                            # Points are usually the last numeric value
                            points = 0
                            for item in reversed(match):
                                if item.isdigit():
                                    points = int(item)
                                    break

                            # Extract code and team from remaining fields
                            code = ""
                            team = ""

                            for item in match[2:]:
                                if len(item) == 3 and item.isupper():
                                    code = item
                                elif any(
                                    team_word in item.lower()
                                    for team_word in [
                                        "red bull",
                                        "ferrari",
                                        "mercedes",
                                        "mclaren",
                                        "aston",
                                        "alpine",
                                    ]
                                ):
                                    team = self._clean_team_name(item)

                            # Generate code if not found
                            if not code:
                                code = self._generate_driver_code(name)

                            # Set unknown team if not found
                            if not team:
                                team = "Unknown"

                            # Validate data
                            if (
                                1 <= position <= 25
                                and points >= 0
                                and name != "Unknown"
                            ):
                                drivers.append(
                                    {
                                        "position": position,
                                        "name": name,
                                        "code": code,
                                        "points": points,
                                        "team": team,
                                    }
                                )
                                logger.debug(
                                    f"📊 Parsed: {position}. {name} ({code}) - {team} - {points} pts"
                                )

                        except (ValueError, IndexError) as e:
                            logger.debug(f"Error parsing driver match {match}: {e}")
                            continue

                    # If we got good matches, break and use them
                    if len(drivers) >= 10:
                        break

            # Sort by position
            if drivers:
                drivers.sort(key=lambda x: x["position"])
                logger.info(f"📊 Successfully parsed {len(drivers)} drivers")

                # Show top 3 for verification
                for i, driver in enumerate(drivers[:3], 1):
                    logger.info(
                        f"📊 P{i}: {driver['name']} ({driver['code']}) - {driver['points']} pts"
                    )

        except Exception as e:
            logger.error(f"Error parsing driver standings: {e}")

        # Return results or enhanced fallback
        if drivers and len(drivers) >= 10:
            return {
                "standings_available": True,
                "drivers": drivers,
                "races_completed": races_completed,
                "source": "perplexity_parsed",
                "raw_response": response,
            }
        else:
            logger.warning(
                f"Only parsed {len(drivers)} drivers, using fallback with response data"
            )
            fallback = self._get_fallback_driver_standings()
            fallback["raw_response"] = response
            fallback["parse_attempt_count"] = len(drivers)
            return fallback

    def _debug_response_format(self, response: str, data_type: str):
        """Debug helper to understand response format."""
        lines = response.split("\n")[:10]  # First 10 lines
        logger.info(f"🔍 {data_type} format analysis:")
        for i, line in enumerate(lines, 1):
            if line.strip():
                logger.info(f"   Line {i}: {line.strip()[:100]}")

    def _parse_team_standings(self, response: str) -> Dict:
        """Extract real constructor standings from Perplexity response."""

        constructors = []
        races_completed = 0

        logger.info(
            f"🏁 Raw team standings response length: {len(response)} characters"
        )

        if not response or len(response) < 50:
            return self._get_fallback_team_standings()

        try:
            # Patterns for team standings
            patterns = [
                # "1. McLaren - 516 points"
                r"(\d+)\.?\s*([A-Za-z\s]+?)\s*[-–]\s*(\d+)\s*points?",
                # "P1: Red Bull Racing (297 points)"
                r"P(\d+):?\s*([A-Za-z\s]+?)\s*\((\d+)\s*points?\)",
                # "McLaren: 516 pts"
                r"([A-Za-z\s]+?):\s*(\d+)\s*pts?",
            ]

            for pattern_idx, pattern in enumerate(patterns):
                matches = re.findall(pattern, response, re.IGNORECASE | re.MULTILINE)

                if matches:
                    logger.info(
                        f"🏁 Using team pattern {pattern_idx + 1}: found {len(matches)} matches"
                    )

                    for match in matches[:10]:  # Limit to 10 teams
                        try:
                            if len(match) >= 3:
                                position = int(match[0])
                                team = self._clean_team_name(match[1])
                                points = int(match[2])
                            elif len(match) >= 2:
                                team = self._clean_team_name(match[0])
                                points = int(match[1])
                                position = len(constructors) + 1
                            else:
                                continue

                            # Validate
                            if position > 0 and position <= 10 and points >= 0:
                                constructors.append(
                                    {
                                        "position": position,
                                        "team": team,
                                        "points": points,
                                    }
                                )

                        except (ValueError, IndexError) as e:
                            logger.debug(f"Error parsing team match {match}: {e}")
                            continue

                    if len(constructors) >= 5:
                        break

            # Extract races completed
            races_match = re.search(
                r"(\d+)\s*races?\s*completed|after\s*(\d+)\s*rounds?",
                response,
                re.IGNORECASE,
            )
            if races_match:
                races_completed = int(races_match.group(1) or races_match.group(2))

            if constructors:
                constructors.sort(key=lambda x: x["position"])
                logger.info(
                    f"🏁 Successfully parsed {len(constructors)} teams from standings"
                )

        except Exception as e:
            logger.error(f"Error parsing team standings: {e}")
            return self._get_fallback_team_standings()

        # Return results or fallback
        if constructors:
            return {
                "standings_available": True,
                "constructors": constructors,
                "races_completed": races_completed,
                "source": "perplexity_parsed",
                "raw_response": response,
            }
        else:
            logger.warning("No team standings could be parsed, using fallback")
            fallback = self._get_fallback_team_standings()
            fallback["raw_response"] = response
            return fallback

    def _parse_race_weekend_data(self, response: str) -> Dict:
        """Extract race weekend session data with TOP 10 results for each session."""

        sessions = {
            "FP1": {
                "available": False,
                "results": [],
                "fastest_driver": "",
                "fastest_time": "",
            },
            "FP2": {
                "available": False,
                "results": [],
                "fastest_driver": "",
                "fastest_time": "",
            },
            "FP3": {
                "available": False,
                "results": [],
                "fastest_driver": "",
                "fastest_time": "",
            },
            "Qualifying": {
                "available": False,
                "results": [],
                "pole_position": "",
                "pole_time": "",
            },
        }

        weather_conditions = ""
        incidents = []

        logger.info(f"🏎️  Raw weekend data response length: {len(response)} characters")

        if not response or len(response) < 50:
            return self._get_fallback_race_weekend_data()

        # Debug: Show response format for troubleshooting
        self._debug_response_format(response, "Race Weekend")

        try:
            # Enhanced qualifying parsing for TOP 10 results
            quali_results = []
            pole_driver = ""
            pole_time = ""

            # First, try to get pole position with enhanced patterns
            quali_patterns = [
                # "Pole position: Charles Leclerc (1:15.372)"
                r"pole position:?\s*([A-Za-z\s]+?)\s*\((\d+:\d+\.\d+)\)",
                # "Charles Leclerc took pole position for the 2025 Hungarian Grand Prix with a time of 1:15.372"
                r"([A-Za-z\s]+?)\s+took\s+pole.*?time\s+of\s+(\d+:\d+\.\d+)",
                # "Charles Leclerc secured pole position with a time of 1:15.372"
                r"([A-Za-z\s]+?)\s+secured\s+pole.*?(\d+:\d+\.\d+)",
                # "- Pole Position: Charles Leclerc (Ferrari) – 1:15.372"
                r"Pole Position:?\s*([A-Za-z\s]+?)(?:\s*\([^)]*\))?\s*[-–]\s*(\d+:\d+\.\d+)",
                # "Q3: 1. Charles Leclerc - 1:15.372"
                r"Q3.*?1\.?\s*([A-Za-z\s]+?)\s*[-–]\s*(\d+:\d+\.\d+)",
            ]

            # Find pole position first
            for pattern_idx, pattern in enumerate(quali_patterns):
                match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
                if match:
                    pole_driver = self._clean_name(match.group(1))
                    pole_time = match.group(2) if len(match.groups()) > 1 else ""
                    logger.info(
                        f"🏎️  Found pole position (pattern {pattern_idx + 1}): {pole_driver} - {pole_time}"
                    )
                    break

            # Now extract full TOP 10 qualifying grid with enhanced patterns
            quali_grid_patterns = [
                # Multi-line qualifying results section
                r"(?:Q3.*?Top 10|Qualifying.*?Results|Q3.*?results):(.*?)(?:\n\n|\n[A-Z]|2\.|3\.|FP|Practice|Weather)",
                # Grid positions section
                r"(?:Grid.*?positions|Starting.*?grid):(.*?)(?:\n\n|\n[A-Z]|2\.|3\.|FP)",
                # Q3 section specifically
                r"Q3.*?(?:results|times):(.*?)(?:\n\n|\n[A-Z]|2\.|3\.|FP)",
                # General qualifying section
                r"1\.\s*[A-Za-z\s]+.*?(?:Ferrari|McLaren|Mercedes).*?(\d+:\d+\.\d+)(.*?)(?:\n\n|\n[A-Z]|FP|Practice)",
            ]

            for grid_pattern_idx, grid_pattern in enumerate(quali_grid_patterns):
                match = re.search(grid_pattern, response, re.IGNORECASE | re.DOTALL)
                if match:
                    grid_section = (
                        match.group(1) if len(match.groups()) >= 1 else match.group(0)
                    )
                    logger.info(
                        f"🏎️  Found qualifying section (pattern {grid_pattern_idx + 1}): {len(grid_section)} characters"
                    )

                    # Enhanced position patterns to handle the exact Perplexity format
                    position_patterns = [
                        # "1. Charles Leclerc (Ferrari) – 1:15.372"
                        r"(\d+)\.\s*([A-Za-z\s]+?)\s*\(([A-Za-z\s]+?)\)\s*[-–]\s*(\d+:\d+\.\d+)",
                        # "2. Oscar Piastri (McLaren) – 1:15.398 (+0.026s)"
                        r"(\d+)\.\s*([A-Za-z\s]+?)\s*\(([A-Za-z\s]+?)\)\s*[-–]\s*(\d+:\d+\.\d+)\s*\([+\-][\d.]+s\)",
                        # "3. Lando Norris (McLaren)" (no time)
                        r"(\d+)\.\s*([A-Za-z\s]+?)\s*\(([A-Za-z\s]+?)\)(?:\s*$|\s*\n)",
                        # "1. Charles Leclerc – 1:15.372" (no team in brackets)
                        r"(\d+)\.\s*([A-Za-z\s]+?)\s*[-–]\s*(\d+:\d+\.\d+)",
                        # "P1: Charles Leclerc - 1:15.372"
                        r"P(\d+):?\s*([A-Za-z\s]+?)\s*[-–]\s*(\d+:\d+\.\d+)",
                        # Simple format: "1. Leclerc 1:15.372"
                        r"(\d+)\.\s*([A-Za-z\s]+?)\s+(\d+:\d+\.\d+)",
                        # Just driver name and position "Charles Leclerc" when we have pole time
                        (
                            r"(\d+)\.\s*([A-Za-z\s]+?)(?:\s*\([^)]*\))?\s*$"
                            if pole_time
                            else None
                        ),
                    ]

                    # Remove None patterns
                    position_patterns = [p for p in position_patterns if p is not None]

                    for pos_pattern_idx, pos_pattern in enumerate(position_patterns):
                        position_matches = re.findall(
                            pos_pattern, grid_section, re.IGNORECASE | re.MULTILINE
                        )

                        if position_matches:
                            logger.info(
                                f"🏎️  Found {len(position_matches)} qualifying positions (pattern {pos_pattern_idx + 1})"
                            )

                            for pos_match in position_matches[:10]:  # TOP 10
                                try:
                                    position = int(pos_match[0])
                                    driver = self._clean_name(pos_match[1])

                                    # Extract time if available in the match
                                    time = ""
                                    if len(pos_match) >= 3:
                                        # Check if last element looks like a time
                                        potential_time = pos_match[-1]
                                        if (
                                            ":" in potential_time
                                            and "." in potential_time
                                        ):
                                            time = potential_time
                                        elif (
                                            len(pos_match) >= 4 and ":" in pos_match[-2]
                                        ):
                                            time = pos_match[-2]

                                    # For pole position, use the time we found earlier
                                    if position == 1 and pole_time and not time:
                                        time = pole_time

                                    # For other positions without times, estimate based on pole time
                                    if not time and pole_time:
                                        # Rough estimation: add ~0.1s per position from pole
                                        try:
                                            pole_seconds = self._time_to_seconds(
                                                pole_time
                                            )
                                            estimated_seconds = (
                                                pole_seconds + (position - 1) * 0.1
                                            )
                                            time = self._seconds_to_time(
                                                estimated_seconds
                                            )
                                        except:
                                            time = ""

                                    if 1 <= position <= 20 and driver:
                                        quali_results.append(
                                            {
                                                "position": position,
                                                "driver": driver,
                                                "time": time,
                                            }
                                        )

                                        logger.debug(
                                            f"   P{position}: {driver} - {time if time else 'no time'}"
                                        )

                                except (ValueError, IndexError) as e:
                                    logger.debug(
                                        f"Error parsing qualifying position {pos_match}: {e}"
                                    )
                                    continue

                            if quali_results:
                                break

                    if quali_results:
                        break

            # If we didn't get full grid but have pole position, create basic grid
            if not quali_results and pole_driver:
                quali_results = [
                    {"position": 1, "driver": pole_driver, "time": pole_time}
                ]
                logger.info("🏎️  Created basic grid from pole position data")

            # Set up qualifying session data
            if pole_driver or quali_results:
                # Sort qualifying results by position
                if quali_results:
                    quali_results.sort(key=lambda x: x["position"])
                    if not pole_driver and quali_results:
                        pole_driver = quali_results[0]["driver"]
                        pole_time = quali_results[0]["time"]

                sessions["Qualifying"] = {
                    "available": True,
                    "pole_position": pole_driver,
                    "pole_time": pole_time,
                    "results": quali_results,  # Full TOP 10 grid
                }

                logger.info(
                    f"🏎️  Qualifying data: {pole_driver} on pole, {len(quali_results)} grid positions"
                )

            # Enhanced practice session parsing for TOP 10 results
            for session_num in ["1", "2", "3"]:
                session_name = f"FP{session_num}"
                practice_results = []
                fastest_driver = ""
                fastest_time = ""

                # Look for practice session sections with enhanced patterns
                practice_section_patterns = [
                    rf"(?:FP{session_num}|Free Practice {session_num}|Practice {session_num}).*?(?:Results|times?):(.*?)(?:\n\n|\n[A-Z]|FP|Practice|\d+\.)",
                    rf"(?:Session.*?FP{session_num}|{session_num}\..*?FP{session_num}):(.*?)(?:\n\n|\n[A-Z]|FP)",
                    rf"{session_num}\.\s*FP{session_num}.*?Results(.*?)(?:\n\n|\n[A-Z]|FP)",
                ]

                for section_pattern in practice_section_patterns:
                    match = re.search(
                        section_pattern, response, re.IGNORECASE | re.DOTALL
                    )
                    if match:
                        practice_section = match.group(1)
                        logger.info(
                            f"🏎️  Found {session_name} section: {len(practice_section)} characters"
                        )

                        # Extract practice session results
                        practice_position_patterns = [
                            # "1. Max Verstappen - 1:16.123"
                            r"(\d+)\.?\s*([A-Za-z\s]+?)\s*[-–]\s*(\d+:\d+\.\d+)",
                            # "P1: Verstappen (Red Bull) - 1:16.123"
                            r"P(\d+):?\s*([A-Za-z\s]+?)(?:\s*\([^)]*\))?\s*[-–]\s*(\d+:\d+\.\d+)",
                            # "1. Max Verstappen (Red Bull)"
                            r"(\d+)\.?\s*([A-Za-z\s]+?)(?:\s*\([^)]*\))?(?:\s*$|\s*\n)",
                        ]

                        for pos_pattern in practice_position_patterns:
                            practice_matches = re.findall(
                                pos_pattern,
                                practice_section,
                                re.IGNORECASE | re.MULTILINE,
                            )

                            if practice_matches:
                                logger.info(
                                    f"🏎️  Found {len(practice_matches)} {session_name} results"
                                )

                                for p_match in practice_matches[:10]:  # TOP 10
                                    try:
                                        position = int(p_match[0])
                                        driver = self._clean_name(p_match[1])
                                        time = (
                                            p_match[2]
                                            if len(p_match) > 2
                                            and ":" in str(p_match[2])
                                            else ""
                                        )

                                        if 1 <= position <= 20 and driver:
                                            practice_results.append(
                                                {
                                                    "position": position,
                                                    "driver": driver,
                                                    "time": time,
                                                }
                                            )

                                            # Set fastest driver (P1)
                                            if position == 1:
                                                fastest_driver = driver
                                                fastest_time = time
                                    except (ValueError, IndexError) as e:
                                        logger.debug(
                                            f"Error parsing {session_name} position {p_match}: {e}"
                                        )
                                        continue

                                if practice_results:
                                    break

                        if practice_results:
                            break

                # If no section found, try individual session patterns
                if not practice_results:
                    individual_patterns = [
                        # "FP1: Max Verstappen fastest (1:16.123)"
                        rf"(FP{session_num}).*?([A-Za-z\s]+?)\s+fastest.*?(\d+:\d+\.\d+)",
                        # "Practice 1: Hamilton tops with 1:16.456"
                        rf"Practice\s+{session_num}.*?([A-Za-z\s]+?).*?(?:tops|fastest).*?(\d+:\d+\.\d+)",
                        # "Session FP1: Verstappen 1:16.123"
                        rf"Session\s+FP{session_num}:?\s*([A-Za-z\s]+?)\s+(\d+:\d+\.\d+)",
                    ]

                    for pattern in individual_patterns:
                        match = re.search(
                            pattern, response, re.IGNORECASE | re.MULTILINE
                        )
                        if match:
                            if len(match.groups()) >= 2:
                                # Extract driver and time from individual pattern
                                if len(match.groups()) == 3:
                                    fastest_driver = self._clean_name(match.group(2))
                                    fastest_time = match.group(3)
                                else:
                                    fastest_driver = self._clean_name(match.group(1))
                                    fastest_time = match.group(2)

                                practice_results = [
                                    {
                                        "position": 1,
                                        "driver": fastest_driver,
                                        "time": fastest_time,
                                    }
                                ]
                                logger.info(
                                    f"🏎️  Found {session_name} fastest: {fastest_driver} - {fastest_time}"
                                )
                                break

                # Set up practice session data if found
                if fastest_driver or practice_results:
                    if practice_results:
                        practice_results.sort(key=lambda x: x["position"])

                    sessions[session_name] = {
                        "available": True,
                        "fastest_driver": fastest_driver,
                        "fastest_time": fastest_time,
                        "results": practice_results,  # TOP 10 results
                    }

                    logger.info(
                        f"🏎️  {session_name} data: {fastest_driver} fastest, {len(practice_results)} results"
                    )

            # Enhanced weather condition patterns
            weather_patterns = [
                r"weather.*?(?:conditions?|was|were):?\s*([^.\n]+)",
                r"conditions?.*?(?:were|was):?\s*([^.\n]+)",
                r"track.*?conditions?:?\s*([^.\n]+)",
                r"session.*?(?:held|run).*?(dry|wet|rain|sunny|cloudy|overcast)",
                r"temperature.*?(\d+).*?degrees?",
                r"(dry|wet|rain|sunny|cloudy|overcast|humid).*?conditions?",
            ]

            for pattern in weather_patterns:
                match = re.search(pattern, response, re.IGNORECASE)
                if match:
                    weather_conditions = match.group(1).strip()
                    if weather_conditions and len(weather_conditions) > 3:
                        logger.info(f"🏎️  Found weather: {weather_conditions}")
                        break

            # Enhanced incident/penalty patterns
            incident_patterns = [
                r"penalty.*?(?:for|to)\s+([A-Za-z\s]+)",
                r"([A-Za-z\s]+?).*?(?:received|given|penalized).*?penalty",
                r"incident.*?(?:involving|with)\s+([A-Za-z\s]+)",
                r"grid penalty.*?(?:for|to)\s+([A-Za-z\s]+)",
                r"warning.*?(?:for|to)\s+([A-Za-z\s]+)",
                r"investigation.*?(?:involving|with)\s+([A-Za-z\s]+)",
            ]

            for pattern in incident_patterns:
                matches = re.findall(pattern, response, re.IGNORECASE)
                for match in matches:
                    incident_text = (
                        match.strip()
                        if isinstance(match, str)
                        else " ".join(match).strip()
                    )
                    if incident_text and len(incident_text) > 2:
                        incidents.append(incident_text)

            # Remove duplicates from incidents
            incidents = list(set(incidents))

            # Race winner detection for concluded races
            if "concluded" in response.lower() or "finished" in response.lower():
                race_winner_patterns = [
                    r"race winner:?\s*([A-Za-z\s]+)",
                    r"victory.*?(?:for|to)\s+([A-Za-z\s]+)",
                    r"([A-Za-z\s]+?)\s+won.*?race",
                    r"first place:?\s*([A-Za-z\s]+)",
                    r"winner.*?([A-Za-z\s]+)",
                ]

                for pattern in race_winner_patterns:
                    match = re.search(pattern, response, re.IGNORECASE)
                    if match:
                        race_winner = self._clean_name(match.group(1))
                        if race_winner:
                            sessions["Race_Winner"] = {
                                "available": True,
                                "winner": race_winner,
                            }
                            logger.info(f"🏎️  Found race winner: {race_winner}")
                            break

        except Exception as e:
            logger.error(f"Error parsing race weekend data: {e}")
            # Log first few lines of response for debugging
            lines = response.split("\n")[:5]
            for i, line in enumerate(lines, 1):
                if line.strip():
                    logger.error(f"   Response line {i}: {line.strip()[:100]}")

        # Determine if we have valid weekend data
        weekend_data_available = any(
            session["available"] for session in sessions.values()
        )

        result = {
            "weekend_data_available": weekend_data_available,
            "sessions": sessions,
            "weather_conditions": weather_conditions,
            "incidents_penalties": incidents,
            "source": "perplexity_parsed",
            "raw_response": response,
        }

        if weekend_data_available:
            available_sessions = [
                name for name, data in sessions.items() if data["available"]
            ]
            logger.info(
                f"🏎️  Successfully parsed weekend data: {', '.join(available_sessions)}"
            )

            # Log summary of parsed data
            for session_name, session_data in sessions.items():
                if session_data.get("available"):
                    results_count = len(session_data.get("results", []))
                    if session_name == "Qualifying":
                        pole = session_data.get("pole_position", "Unknown")
                        pole_time = session_data.get("pole_time", "")
                        logger.info(
                            f"   {session_name}: {pole} on pole ({pole_time}), {results_count} grid positions"
                        )
                    else:
                        fastest = session_data.get("fastest_driver", "Unknown")
                        fastest_time = session_data.get("fastest_time", "")
                        logger.info(
                            f"   {session_name}: {fastest} fastest ({fastest_time}), {results_count} results"
                        )
        else:
            logger.warning("No race weekend data could be parsed, using fallback")
            logger.warning(f"Response preview: {response[:500]}...")
            fallback = self._get_fallback_race_weekend_data()
            fallback["raw_response"] = response
            return fallback

        return result

    # Helper methods for time conversion
    def _time_to_seconds(self, time_str: str) -> float:
        """Convert time string to seconds."""
        try:
            parts = time_str.split(":")
            minutes = int(parts[0])
            seconds = float(parts[1])
            return minutes * 60 + seconds
        except:
            return 0.0

    def _seconds_to_time(self, seconds: float) -> str:
        """Convert seconds to time string."""
        try:
            minutes = int(seconds // 60)
            secs = seconds % 60
            return f"{minutes}:{secs:06.3f}"
        except:
            return ""

    # Helper methods for parsing
    def _clean_name(self, name: str) -> str:
        """Clean and standardize driver names."""
        if not name:
            return "Unknown"

        # Remove extra whitespace and common prefixes
        name = re.sub(r"\s+", " ", name.strip())
        name = re.sub(r"^(P\d+:?|Position\s+\d+:?)", "", name, flags=re.IGNORECASE)

        return name.title()

    def _clean_team_name(self, team: str) -> str:
        """Clean and standardize team names."""
        if not team:
            return "Unknown"

        team = re.sub(r"\s+", " ", team.strip())

        # Standardize team names
        team_mappings = {
            "red bull": "Red Bull Racing",
            "ferrari": "Ferrari",
            "mercedes": "Mercedes",
            "mclaren": "McLaren",
            "aston martin": "Aston Martin",
            "alpine": "Alpine",
            "williams": "Williams",
            "haas": "Haas F1 Team",
            "sauber": "Sauber",
            "alphatauri": "AlphaTauri",
            "vcarb": "VCARB",
        }

        team_lower = team.lower()
        for key, value in team_mappings.items():
            if key in team_lower:
                return value

        return team.title()

    def _extract_driver_code(self, name: str, context: str) -> str:
        """Extract or generate 3-letter driver code."""

        # Look for existing code in context
        code_match = re.search(r"\b([A-Z]{3})\b", context)
        if code_match:
            return code_match.group(1)

        # Generate from name
        return self._generate_driver_code(name)

    def _generate_driver_code(self, name: str) -> str:
        """Generate 3-letter code from driver name."""
        if not name:
            return "UNK"

        # Known mappings
        known_codes = {
            "max verstappen": "VER",
            "lewis hamilton": "HAM",
            "charles leclerc": "LEC",
            "george russell": "RUS",
            "carlos sainz": "SAI",
            "lando norris": "NOR",
            "oscar piastri": "PIA",
            "fernando alonso": "ALO",
            "sergio perez": "PER",
            "lance stroll": "STR",
            "pierre gasly": "GAS",
            "esteban ocon": "OCO",
            "alexander albon": "ALB",
            "logan sargeant": "SAR",
            "kevin magnussen": "MAG",
            "nico hulkenberg": "HUL",
            "valtteri bottas": "BOT",
            "zhou guanyu": "ZHO",
            "yuki tsunoda": "TSU",
            "daniel ricciardo": "RIC",
        }

        name_lower = name.lower().strip()
        if name_lower in known_codes:
            return known_codes[name_lower]

        # Generate from last name
        parts = name.split()
        if len(parts) >= 2:
            return parts[-1][:3].upper()
        else:
            return name[:3].upper()

    def _extract_team_name(self, match_tuple) -> str:
        """Extract team name from regex match tuple."""
        # Look for team name in different positions of the match
        for item in match_tuple:
            if any(
                team_word in item.lower()
                for team_word in [
                    "bull",
                    "ferrari",
                    "mercedes",
                    "mclaren",
                    "aston",
                    "alpine",
                    "williams",
                    "haas",
                    "sauber",
                ]
            ):
                return self._clean_team_name(item)

        return "Unknown"

    def _extract_races_completed(self, response: str) -> int:
        """Extract number of completed races from response."""
        patterns = [
            r"(\d+)\s*races?\s*completed",
            r"after\s*(\d+)\s*rounds?",
            r"round\s*(\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                return int(match.group(1))

        return 0

    # Fallback data methods (unchanged)
    def _get_fallback_data(self) -> Dict:
        """Enhanced fallback data for 3-API structure."""
        logger.warning("Using fallback data - Perplexity API not available")

        return {
            "driver_standings": self._get_fallback_driver_standings(),
            "team_standings": self._get_fallback_team_standings(),
            "race_weekend_data": self._get_fallback_race_weekend_data(),
            "source": "fallback",
            "timestamp": datetime.now().isoformat(),
        }

    def _get_fallback_driver_standings(self) -> Dict:
        """Fallback driver championship standings."""
        return {
            "standings_available": False,
            "drivers": [
                {
                    "code": "PIA",
                    "name": "Oscar Piastri",
                    "team": "McLaren",
                    "points": 266,
                    "position": 1,
                },
                {
                    "code": "NOR",
                    "name": "Lando Norris",
                    "team": "McLaren",
                    "points": 250,
                    "position": 2,
                },
                {
                    "code": "VER",
                    "name": "Max Verstappen",
                    "team": "Red Bull Racing",
                    "points": 185,
                    "position": 3,
                },
                {
                    "code": "LEC",
                    "name": "Charles Leclerc",
                    "team": "Ferrari",
                    "points": 162,
                    "position": 4,
                },
                {
                    "code": "RUS",
                    "name": "George Russell",
                    "team": "Mercedes",
                    "points": 143,
                    "position": 5,
                },
                {
                    "code": "HAM",
                    "name": "Lewis Hamilton",
                    "team": "Mercedes",
                    "points": 109,
                    "position": 6,
                },
                {
                    "code": "SAI",
                    "name": "Carlos Sainz Jr",
                    "team": "Ferrari",
                    "points": 83,
                    "position": 7,
                },
                {
                    "code": "ALO",
                    "name": "Fernando Alonso",
                    "team": "Aston Martin",
                    "points": 70,
                    "position": 8,
                },
                {
                    "code": "PER",
                    "name": "Sergio Perez",
                    "team": "Red Bull Racing",
                    "points": 60,
                    "position": 9,
                },
                {
                    "code": "STR",
                    "name": "Lance Stroll",
                    "team": "Aston Martin",
                    "points": 35,
                    "position": 10,
                },
            ],
            "races_completed": 13,
            "source": "fallback_data",
        }

    def _get_fallback_team_standings(self) -> Dict:
        """Fallback constructor standings."""
        return {
            "standings_available": False,
            "constructors": [
                {"team": "McLaren", "points": 516, "position": 1},
                {"team": "Red Bull Racing", "points": 297, "position": 2},
                {"team": "Ferrari", "points": 245, "position": 3},
                {"team": "Mercedes", "points": 252, "position": 4},
                {"team": "Aston Martin", "points": 105, "position": 5},
                {"team": "Alpine", "points": 49, "position": 6},
                {"team": "Williams", "points": 17, "position": 7},
                {"team": "Haas F1 Team", "points": 15, "position": 8},
                {"team": "VCARB", "points": 14, "position": 9},
                {"team": "Sauber", "points": 4, "position": 10},
            ],
            "races_completed": 13,
            "source": "fallback_data",
        }

    def _get_fallback_race_weekend_data(self) -> Dict:
        """Fallback race weekend data."""
        return {
            "weekend_data_available": False,
            "sessions": {
                "FP1": {
                    "available": False,
                    "results": [],
                    "fastest_driver": "",
                    "fastest_time": "",
                },
                "FP2": {
                    "available": False,
                    "results": [],
                    "fastest_driver": "",
                    "fastest_time": "",
                },
                "FP3": {
                    "available": False,
                    "results": [],
                    "fastest_driver": "",
                    "fastest_time": "",
                },
                "Qualifying": {
                    "available": False,
                    "pole_position": "",
                    "pole_time": "",
                    "results": [],
                },
            },
            "weather_conditions": "Conditions unknown",
            "incidents_penalties": [],
            "source": "fallback_data",
        }

    def get_race_weekend_data(self, gp_name: str) -> Dict:
        """Enhanced race weekend data using official F1.com data as primary source."""
        try:
            logger.info(f"🔍 Getting race weekend data for {gp_name}")

            # Try official F1.com data first
            from .formula1_web_collector import Formula1WebCollector

            f1_collector = Formula1WebCollector()

            official_data = f1_collector.get_all_session_data(gp_name)

            if official_data and any(
                session.get("session_available", False)
                for session in official_data.values()
            ):
                logger.info("✅ Using official F1.com data")
                return self._format_official_data(official_data)

            # Fallback to Perplexity if official data unavailable
            logger.info("⚠️ Official data unavailable, using Perplexity fallback")
            return self._get_perplexity_fallback_data(gp_name)

        except Exception as e:
            logger.warning(f"Race weekend data unavailable: {e}")
            return {}

    def _format_official_data(self, official_data: Dict) -> Dict:
        """Format official F1.com data to match expected structure."""
        return {
            "weekend_data_available": True,
            "data_source": "official_f1_website",
            "sessions": {
                "FP1": self._format_session(official_data.get("practice_1", {})),
                "FP2": self._format_session(official_data.get("practice_2", {})),
                "FP3": self._format_session(official_data.get("practice_3", {})),
                "Qualifying": self._format_qualifying_session(
                    official_data.get("qualifying", {})
                ),
            },
        }

    def _format_session(self, session_data: Dict) -> Dict:
        """Format practice session data."""
        if not session_data.get("session_available"):
            return {"available": False}

        return {
            "available": True,
            "fastest_driver": session_data.get("fastest_driver", ""),
            "fastest_time": session_data.get("fastest_time", ""),
            "results": session_data.get("results", [])[:10],  # Top 10
        }

    def _format_qualifying_session(self, qualifying_data: Dict) -> Dict:
        """Format qualifying session data."""
        if not qualifying_data.get("available"):
            return {"available": False}

        return {
            "available": True,
            "pole_position": qualifying_data.get("pole_position", ""),
            "pole_time": qualifying_data.get("pole_time", ""),
            "results": qualifying_data.get("results", [])[:10],  # Top 10
        }

    def _standardize_gp_name(self, gp_name: str) -> str:
        """Standardize GP name for queries."""
        # Remove common variations
        clean_name = gp_name.replace("Grand Prix", "GP").replace("grand prix", "GP")

        # Map common names to full GP names
        gp_mappings = {
            "hungarian": "Hungarian Grand Prix",
            "dutch": "Dutch Grand Prix",
            "monaco": "Monaco Grand Prix",
            "silverstone": "British Grand Prix",
            "monza": "Italian Grand Prix",
            "spa": "Belgian Grand Prix",
            "zandvoort": "Dutch Grand Prix",
            "hungaroring": "Hungarian Grand Prix",
            "abu dhabi": "Abu Dhabi Grand Prix",
            "yas marina": "Abu Dhabi Grand Prix",
            "miami": "Miami Grand Prix",
            "austin": "United States Grand Prix",
            "cota": "United States Grand Prix",
            "suzuka": "Japanese Grand Prix",
            "melbourne": "Australian Grand Prix",
            "bahrain": "Bahrain Grand Prix",
            "jeddah": "Saudi Arabian Grand Prix",
            "imola": "Emilia Romagna Grand Prix",
            "barcelona": "Spanish Grand Prix",
            "montreal": "Canadian Grand Prix",
            "paul ricard": "French Grand Prix",
            "red bull ring": "Austrian Grand Prix",
            "singapore": "Singapore Grand Prix",
            "brazil": "Brazilian Grand Prix",
            "interlagos": "Brazilian Grand Prix",
            "vegas": "Las Vegas Grand Prix",
            "qatar": "Qatar Grand Prix",
        }

        # Check for mapping
        name_lower = clean_name.lower().strip()
        for key, full_name in gp_mappings.items():
            if key in name_lower:
                return full_name

        # If no mapping found, ensure "Grand Prix" is in the name
        if "grand prix" not in clean_name.lower() and "gp" not in clean_name.lower():
            return f"{clean_name} Grand Prix"

        return clean_name

    def _parse_race_weekend_response(self, response: str, gp_name: str) -> Dict:
        """Parse race weekend response for any GP."""
        parsed_data = {
            "weekend_data_available": True,
            "sessions": {
                "Qualifying": {"available": False},
                "FP1": {"available": False},
                "FP2": {"available": False},
                "FP3": {"available": False},
            },
        }

        try:
            # Look for qualifying data
            if "pole position" in response.lower() or "qualifying" in response.lower():
                quali_data = self._extract_qualifying_data(response, gp_name)
                if quali_data:
                    parsed_data["sessions"]["Qualifying"] = quali_data

        except Exception as e:
            logger.debug(f"Error parsing race weekend response: {e}")

        return parsed_data

    def _extract_qualifying_data(self, response: str, gp_name: str) -> Dict:
        """Extract qualifying data from response."""
        import re

        quali_data = {
            "available": False,
            "pole_position": "",
            "pole_time": "",
            "results": [],
        }

        try:
            # Find pole position
            pole_patterns = [
                r"(\w+\s+\w+).*?pole position.*?(\d+:\d+\.\d+)",
                r"pole position.*?(\w+\s+\w+).*?(\d+:\d+\.\d+)",
                r"1\.\s*(\w+\s+\w+).*?(\d+:\d+\.\d+)",
            ]

            for pattern in pole_patterns:
                match = re.search(pattern, response, re.IGNORECASE)
                if match:
                    pole_driver = match.group(1).strip()
                    pole_time = match.group(2).strip()

                    quali_data["pole_position"] = pole_driver
                    quali_data["pole_time"] = pole_time
                    quali_data["available"] = True

                    # Add to results
                    quali_data["results"].append(
                        {"position": 1, "driver": pole_driver, "time": pole_time}
                    )

                    logger.info(f"🏁 Found pole position: {pole_driver} - {pole_time}")
                    break

            # Extract grid positions 1-10
            grid_patterns = [
                r"(\d+)\.\s*(\w+\s+\w+).*?(\d+:\d+\.\d+)",
                r"P(\d+).*?(\w+\s+\w+)",
                r"(\d+)(?:st|nd|rd|th).*?(\w+\s+\w+)",
            ]

            for pattern in grid_patterns:
                matches = re.finditer(pattern, response, re.IGNORECASE)
                for match in matches:
                    try:
                        position = int(match.group(1))
                        driver = match.group(2).strip()
                        time = match.group(3).strip() if len(match.groups()) > 2 else ""

                        if (
                            position <= 10 and position > 1
                        ):  # Skip P1 as it's already added
                            quali_data["results"].append(
                                {"position": position, "driver": driver, "time": time}
                            )
                    except (ValueError, IndexError):
                        continue

            # Sort results by position
            quali_data["results"] = sorted(
                quali_data["results"], key=lambda x: x["position"]
            )

        except Exception as e:
            logger.debug(f"Error extracting qualifying data: {e}")

        return quali_data
