"""
Process historical FastF1 data for circuit-specific analysis.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class HistoricalProcessor:
    """Process historical race data for pattern analysis."""

    def __init__(self):
        pass

    def analyze_historical_patterns(
        self, historical_data: List[Dict], circuit_config: Dict
    ) -> Dict:
        """
        Analyze historical patterns for circuit-specific insights.

        Args:
            historical_data: List of historical race data
            circuit_config: Circuit configuration

        Returns:
            Analyzed patterns and insights
        """
        try:
            analysis = {
                "winner_patterns": self._analyze_winner_patterns(historical_data),
                "qualifying_impact": self._analyze_qualifying_impact(
                    historical_data, circuit_config
                ),
                "weather_impact": self._analyze_weather_impact(historical_data),
                "team_performance": self._analyze_team_performance(historical_data),
                "driver_specialists": self._identify_circuit_specialists(
                    historical_data
                ),
                "overtaking_analysis": self._analyze_overtaking_patterns(
                    historical_data
                ),
                "strategic_insights": self._analyze_strategic_patterns(historical_data),
                "reliability_factors": self._analyze_reliability_patterns(
                    historical_data
                ),
            }

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing historical patterns: {e}")
            return {}

    def _analyze_winner_patterns(self, historical_data: List[Dict]) -> Dict:
        """Analyze patterns in race winners."""
        winner_analysis = {
            "winners_by_year": {},
            "dominant_drivers": {},
            "team_dominance": {},
            "winning_characteristics": {},
        }

        try:
            for race in historical_data:
                year = race.get("year")
                winner = race.get("race_winner")

                if winner and year:
                    # Track winners by year
                    winner_analysis["winners_by_year"][year] = winner

                    # Count driver wins
                    if winner in winner_analysis["dominant_drivers"]:
                        winner_analysis["dominant_drivers"][winner] += 1
                    else:
                        winner_analysis["dominant_drivers"][winner] = 1

                    # Analyze winner characteristics
                    driver_data = race.get("drivers", {}).get(winner, {})
                    if driver_data:
                        quali_pos = driver_data.get("qualifying_position", 99)
                        team = driver_data.get("team", "Unknown")

                        # Track team wins
                        if team in winner_analysis["team_dominance"]:
                            winner_analysis["team_dominance"][team] += 1
                        else:
                            winner_analysis["team_dominance"][team] = 1

                        # Analyze starting positions of winners
                        if (
                            "qualifying_positions"
                            not in winner_analysis["winning_characteristics"]
                        ):
                            winner_analysis["winning_characteristics"][
                                "qualifying_positions"
                            ] = []

                        if quali_pos != 99:
                            winner_analysis["winning_characteristics"][
                                "qualifying_positions"
                            ].append(quali_pos)

            # Calculate statistics
            quali_positions = winner_analysis["winning_characteristics"].get(
                "qualifying_positions", []
            )
            if quali_positions:
                winner_analysis["winning_characteristics"]["avg_winning_quali_pos"] = (
                    np.mean(quali_positions)
                )
                winner_analysis["winning_characteristics"]["pole_win_rate"] = sum(
                    1 for pos in quali_positions if pos == 1
                ) / len(quali_positions)
                winner_analysis["winning_characteristics"]["front_row_win_rate"] = sum(
                    1 for pos in quali_positions if pos <= 2
                ) / len(quali_positions)

        except Exception as e:
            logger.error(f"Error analyzing winner patterns: {e}")

        return winner_analysis

    def _analyze_qualifying_impact(
        self, historical_data: List[Dict], circuit_config: Dict
    ) -> Dict:
        """Analyze the impact of qualifying position on race results."""
        quali_analysis = {
            "pole_to_win_rate": 0.0,
            "front_row_advantage": 0.0,
            "position_correlation": 0.0,
            "qualifying_importance_score": 0.0,
        }

        try:
            quali_positions = []
            race_positions = []
            pole_wins = 0
            front_row_wins = 0
            total_races = 0

            for race in historical_data:
                winner = race.get("race_winner")
                if not winner:
                    continue

                total_races += 1
                driver_data = race.get("drivers", {}).get(winner, {})

                quali_pos = driver_data.get("qualifying_position", 99)
                race_pos = driver_data.get("race_position", 99)

                if quali_pos != 99 and race_pos != 99:
                    quali_positions.append(quali_pos)
                    race_positions.append(race_pos)

                    if quali_pos == 1:
                        pole_wins += 1
                    if quali_pos <= 2:
                        front_row_wins += 1

            if total_races > 0:
                quali_analysis["pole_to_win_rate"] = pole_wins / total_races
                quali_analysis["front_row_advantage"] = front_row_wins / total_races

                # Calculate correlation between qualifying and race position
                if len(quali_positions) > 1:
                    correlation = np.corrcoef(quali_positions, race_positions)[0, 1]
                    quali_analysis["position_correlation"] = (
                        correlation if not np.isnan(correlation) else 0.0
                    )

                # Calculate qualifying importance score
                circuit_quali_importance = circuit_config.get(
                    "qualifying_importance", 0.7
                )
                historical_importance = (
                    quali_analysis["pole_to_win_rate"]
                    + quali_analysis["front_row_advantage"]
                ) / 2
                quali_analysis["qualifying_importance_score"] = (
                    circuit_quali_importance + historical_importance
                ) / 2

        except Exception as e:
            logger.error(f"Error analyzing qualifying impact: {e}")

        return quali_analysis

    def _analyze_weather_impact(self, historical_data: List[Dict]) -> Dict:
        """Analyze weather impact on race results."""
        weather_analysis = {
            "rain_races": [],
            "weather_specialists": {},
            "temperature_impact": {},
            "weather_upset_rate": 0.0,
        }

        try:
            rain_race_count = 0
            total_races = len(historical_data)

            for race in historical_data:
                weather_data = race.get("weather", {})
                winner = race.get("race_winner")

                # Check for rain conditions
                if weather_data.get("rainfall", False):
                    rain_race_count += 1
                    weather_analysis["rain_races"].append(
                        {
                            "year": race.get("year"),
                            "winner": winner,
                            "conditions": "wet",
                        }
                    )

                    # Track rain specialists
                    if winner:
                        if winner in weather_analysis["weather_specialists"]:
                            weather_analysis["weather_specialists"][winner] += 1
                        else:
                            weather_analysis["weather_specialists"][winner] = 1

                # Analyze temperature impact
                if weather_data.get("available"):
                    temp = weather_data.get("air_temp_avg", 25)
                    temp_category = (
                        "hot" if temp > 30 else "cold" if temp < 15 else "moderate"
                    )

                    if temp_category not in weather_analysis["temperature_impact"]:
                        weather_analysis["temperature_impact"][temp_category] = []

                    weather_analysis["temperature_impact"][temp_category].append(
                        {"winner": winner, "temperature": temp}
                    )

            # Calculate weather upset rate
            if rain_race_count > 0:
                weather_analysis["weather_upset_rate"] = rain_race_count / total_races

        except Exception as e:
            logger.error(f"Error analyzing weather impact: {e}")

        return weather_analysis

    def _analyze_team_performance(self, historical_data: List[Dict]) -> Dict:
        """Analyze team performance patterns at this circuit."""
        team_analysis = {"team_wins": {}, "team_consistency": {}, "era_dominance": {}}

        try:
            team_results = {}

            for race in historical_data:
                year = race.get("year")
                drivers = race.get("drivers", {})

                for driver_code, driver_data in drivers.items():
                    team = driver_data.get("team", "Unknown")
                    race_pos = driver_data.get("race_position", 99)

                    if team not in team_results:
                        team_results[team] = []

                    team_results[team].append(
                        {"year": year, "driver": driver_code, "position": race_pos}
                    )

            # Analyze team performance
            for team, results in team_results.items():
                wins = sum(1 for result in results if result["position"] == 1)
                podiums = sum(1 for result in results if result["position"] <= 3)
                points_finishes = sum(
                    1 for result in results if result["position"] <= 10
                )

                team_analysis["team_wins"][team] = {
                    "wins": wins,
                    "podiums": podiums,
                    "points_finishes": points_finishes,
                    "total_entries": len(results),
                }

                # Calculate consistency (standard deviation of positions)
                positions = [
                    result["position"] for result in results if result["position"] != 99
                ]
                if positions:
                    team_analysis["team_consistency"][team] = {
                        "avg_position": np.mean(positions),
                        "consistency_score": 1.0 / (1.0 + np.std(positions)),
                    }

        except Exception as e:
            logger.error(f"Error analyzing team performance: {e}")

        return team_analysis

    def _identify_circuit_specialists(self, historical_data: List[Dict]) -> Dict:
        """Identify drivers who consistently perform well at this circuit."""
        specialists = {
            "performance_specialists": {},
            "qualifying_specialists": {},
            "consistency_masters": {},
        }

        try:
            driver_performance = {}

            for race in historical_data:
                drivers = race.get("drivers", {})

                for driver_code, driver_data in drivers.items():
                    if driver_code not in driver_performance:
                        driver_performance[driver_code] = {
                            "race_positions": [],
                            "quali_positions": [],
                            "appearances": 0,
                        }

                    race_pos = driver_data.get("race_position", 99)
                    quali_pos = driver_data.get("qualifying_position", 99)

                    if race_pos != 99:
                        driver_performance[driver_code]["race_positions"].append(
                            race_pos
                        )
                    if quali_pos != 99:
                        driver_performance[driver_code]["quali_positions"].append(
                            quali_pos
                        )

                    driver_performance[driver_code]["appearances"] += 1

            # Identify specialists (minimum 3 appearances)
            for driver, perf in driver_performance.items():
                if perf["appearances"] >= 3:
                    race_positions = perf["race_positions"]
                    quali_positions = perf["quali_positions"]

                    if race_positions:
                        avg_race = np.mean(race_positions)
                        consistency = 1.0 / (1.0 + np.std(race_positions))

                        specialists["performance_specialists"][driver] = {
                            "avg_position": avg_race,
                            "best_finish": min(race_positions),
                            "appearances": perf["appearances"],
                        }

                        specialists["consistency_masters"][driver] = {
                            "consistency_score": consistency,
                            "avg_position": avg_race,
                        }

                    if quali_positions:
                        avg_quali = np.mean(quali_positions)
                        specialists["qualifying_specialists"][driver] = {
                            "avg_quali_position": avg_quali,
                            "best_quali": min(quali_positions),
                        }

        except Exception as e:
            logger.error(f"Error identifying specialists: {e}")

        return specialists

    def _analyze_overtaking_patterns(self, historical_data: List[Dict]) -> Dict:
        """Analyze overtaking and position change patterns."""
        overtaking_analysis = {
            "average_position_changes": 0.0,
            "comeback_victories": [],
            "front_runner_dominance": 0.0,
        }

        try:
            total_position_changes = []
            comeback_wins = 0
            front_runner_wins = 0
            total_winners = 0

            for race in historical_data:
                winner = race.get("race_winner")
                if not winner:
                    continue

                total_winners += 1
                driver_data = race.get("drivers", {}).get(winner, {})
                quali_pos = driver_data.get("qualifying_position", 99)
                race_pos = driver_data.get("race_position", 1)

                if quali_pos != 99:
                    position_change = quali_pos - race_pos
                    total_position_changes.append(position_change)

                    if quali_pos > 5:  # Started outside top 5
                        comeback_wins += 1
                        overtaking_analysis["comeback_victories"].append(
                            {
                                "year": race.get("year"),
                                "winner": winner,
                                "start_position": quali_pos,
                            }
                        )

                    if quali_pos <= 2:  # Started on front row
                        front_runner_wins += 1

            if total_position_changes:
                overtaking_analysis["average_position_changes"] = np.mean(
                    total_position_changes
                )

            if total_winners > 0:
                overtaking_analysis["front_runner_dominance"] = (
                    front_runner_wins / total_winners
                )

        except Exception as e:
            logger.error(f"Error analyzing overtaking patterns: {e}")

        return overtaking_analysis

    def _analyze_strategic_patterns(self, historical_data: List[Dict]) -> Dict:
        """Analyze strategic patterns and pit stop impact."""
        strategy_analysis = {
            "typical_strategies": {},
            "safety_car_impact": {},
            "tire_strategy_importance": 0.5,
        }

        # This would be enhanced with more detailed pit stop and strategy data
        # For now, return basic structure

        return strategy_analysis

    def _analyze_reliability_patterns(self, historical_data: List[Dict]) -> Dict:
        """Analyze reliability and DNF patterns."""
        reliability_analysis = {
            "dnf_rates": {},
            "reliability_impact": 0.0,
            "common_failure_causes": [],
        }

        try:
            total_entries = {}
            dnf_counts = {}

            for race in historical_data:
                drivers = race.get("drivers", {})

                for driver_code, driver_data in drivers.items():
                    status = driver_data.get("race_status", "Finished")

                    if driver_code not in total_entries:
                        total_entries[driver_code] = 0
                        dnf_counts[driver_code] = 0

                    total_entries[driver_code] += 1

                    if (
                        status != "Finished"
                        and driver_data.get("race_position", 1) == 99
                    ):
                        dnf_counts[driver_code] += 1

            # Calculate DNF rates
            for driver in total_entries:
                if total_entries[driver] > 0:
                    dnf_rate = dnf_counts[driver] / total_entries[driver]
                    reliability_analysis["dnf_rates"][driver] = {
                        "dnf_rate": dnf_rate,
                        "total_races": total_entries[driver],
                        "dnfs": dnf_counts[driver],
                    }

            # Calculate overall reliability impact
            if total_entries:
                total_dnfs = sum(dnf_counts.values())
                total_races = sum(total_entries.values())
                reliability_analysis["reliability_impact"] = (
                    total_dnfs / total_races if total_races > 0 else 0.0
                )

        except Exception as e:
            logger.error(f"Error analyzing reliability patterns: {e}")

        return reliability_analysis
