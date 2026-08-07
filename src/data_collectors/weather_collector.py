"""
Enhanced OpenWeatherMap API integration with complete circuit coordinate support.
"""

import requests
import logging
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
import json

from config.settings import OPENWEATHER_API_KEY

logger = logging.getLogger(__name__)


class WeatherCollector:
    """Enhanced weather collector with robust coordinate handling."""

    def __init__(self):
        self.api_key = OPENWEATHER_API_KEY
        self.base_url = "https://api.openweathermap.org/data/2.5"

        # Validate API key on initialization
        if not self.api_key:
            logger.warning("⚠️ OpenWeatherMap API key not configured")
        else:
            logger.info("✅ OpenWeatherMap API initialized")

    def get_race_weekend_weather(self, circuit_info: Dict) -> Dict:
        """Enhanced weather forecast for race weekend with proper coordinate extraction."""
        if not self.api_key:
            logger.warning("❌ OpenWeatherMap API key not configured")
            return self._get_fallback_weather(circuit_info)

        # Enhanced coordinate extraction
        coordinates = self._extract_coordinates(circuit_info)
        if not coordinates:
            logger.error("❌ Failed to extract valid coordinates")
            return self._get_fallback_weather(circuit_info)

        lat, lon = coordinates
        city = circuit_info.get("location", {}).get("city", "Unknown")
        country = circuit_info.get("location", {}).get("country", "Unknown")

        logger.info(
            f"🌤️ Getting weather forecast for {city}, {country} ({lat:.4f}, {lon:.4f})"
        )

        weather_data = {
            "current_weather": self._get_current_weather(lat, lon),
            "forecast": self._get_weather_forecast(lat, lon),
            "race_weekend_analysis": {},
            "location": {"city": city, "country": country, "coordinates": [lat, lon]},
            "timestamp": datetime.now().isoformat(),
        }

        # Analyze race weekend conditions
        weather_data["race_weekend_analysis"] = self._analyze_race_weekend_weather(
            weather_data["forecast"], circuit_info
        )

        return weather_data

    def _extract_coordinates(self, circuit_info: Dict) -> Optional[Tuple[float, float]]:
        """Enhanced coordinate extraction with validation."""
        try:
            location = circuit_info.get("location", {})
            coordinates = location.get("coordinates", [])

            if not coordinates or len(coordinates) != 2:
                logger.error(f"Invalid coordinates format: {coordinates}")
                return None

            lat, lon = float(coordinates[0]), float(coordinates[1])

            # Validate coordinate ranges
            if not (-90 <= lat <= 90):
                logger.error(f"Invalid latitude: {lat}")
                return None

            if not (-180 <= lon <= 180):
                logger.error(f"Invalid longitude: {lon}")
                return None

            return lat, lon

        except (ValueError, TypeError) as e:
            logger.error(f"Error extracting coordinates: {e}")
            return None

    def _get_current_weather(self, lat: float, lon: float) -> Dict:
        """Get current weather with enhanced error handling."""
        try:
            url = f"{self.base_url}/weather"
            params = {"lat": lat, "lon": lon, "appid": self.api_key, "units": "metric"}

            response = requests.get(url, params=params, timeout=15)

            if response.status_code == 200:
                data = response.json()

                current_weather = {
                    "temperature": data["main"]["temp"],
                    "feels_like": data["main"]["feels_like"],
                    "humidity": data["main"]["humidity"],
                    "pressure": data["main"]["pressure"],
                    "wind_speed": data["wind"]["speed"],
                    "wind_direction": data["wind"].get("deg", 0),
                    "visibility": data.get("visibility", 10000) / 1000,
                    "weather_condition": data["weather"][0]["main"],
                    "weather_description": data["weather"][0]["description"],
                    "clouds": data["clouds"]["all"],
                    "rain": data.get("rain", {}).get("1h", 0),
                    "available": True,
                }

                logger.info(
                    f"✅ Current weather: {current_weather['temperature']:.1f}°C, {current_weather['weather_description']}"
                )
                return current_weather

            elif response.status_code == 401:
                logger.error("❌ Invalid OpenWeatherMap API key")
                return {"available": False, "error": "Invalid API key"}
            elif response.status_code == 429:
                logger.error("❌ OpenWeatherMap API rate limit exceeded")
                return {"available": False, "error": "Rate limit exceeded"}
            else:
                logger.error(f"❌ OpenWeather API error: {response.status_code}")
                return {"available": False, "error": f"HTTP {response.status_code}"}

        except requests.exceptions.Timeout:
            logger.error("❌ Weather API request timeout")
            return {"available": False, "error": "Request timeout"}
        except Exception as e:
            logger.error(f"❌ Error getting current weather: {e}")
            return {"available": False, "error": str(e)}

    def _get_weather_forecast(self, lat: float, lon: float) -> Dict:
        """Enhanced 5-day weather forecast."""
        try:
            url = f"{self.base_url}/forecast"
            params = {"lat": lat, "lon": lon, "appid": self.api_key, "units": "metric"}

            response = requests.get(url, params=params, timeout=15)

            if response.status_code == 200:
                data = response.json()

                forecast_data = {
                    "available": True,
                    "daily_forecasts": [],
                    "hourly_forecasts": [],
                }

                # Process hourly forecasts
                daily_data = {}

                for item in data["list"]:
                    dt = datetime.fromtimestamp(item["dt"])
                    date_key = dt.date()

                    forecast_item = {
                        "datetime": dt.isoformat(),
                        "temperature": item["main"]["temp"],
                        "feels_like": item["main"]["feels_like"],
                        "humidity": item["main"]["humidity"],
                        "pressure": item["main"]["pressure"],
                        "wind_speed": item["wind"]["speed"],
                        "wind_direction": item["wind"].get("deg", 0),
                        "weather_condition": item["weather"][0]["main"],
                        "weather_description": item["weather"][0]["description"],
                        "clouds": item["clouds"]["all"],
                        "rain_probability": item.get("pop", 0) * 100,
                        "rain_volume": item.get("rain", {}).get("3h", 0),
                    }

                    forecast_data["hourly_forecasts"].append(forecast_item)

                    # Aggregate daily data
                    if date_key not in daily_data:
                        daily_data[date_key] = {
                            "date": str(date_key),
                            "temperatures": [],
                            "humidity": [],
                            "wind_speeds": [],
                            "rain_probability": [],
                            "rain_volume": [],
                            "conditions": [],
                        }

                    daily_data[date_key]["temperatures"].append(item["main"]["temp"])
                    daily_data[date_key]["humidity"].append(item["main"]["humidity"])
                    daily_data[date_key]["wind_speeds"].append(item["wind"]["speed"])
                    daily_data[date_key]["rain_probability"].append(
                        item.get("pop", 0) * 100
                    )
                    daily_data[date_key]["rain_volume"].append(
                        item.get("rain", {}).get("3h", 0)
                    )
                    daily_data[date_key]["conditions"].append(
                        item["weather"][0]["main"]
                    )

                # Create daily summaries
                for date_key, day_data in daily_data.items():
                    daily_summary = {
                        "date": day_data["date"],
                        "temp_min": min(day_data["temperatures"]),
                        "temp_max": max(day_data["temperatures"]),
                        "temp_avg": sum(day_data["temperatures"])
                        / len(day_data["temperatures"]),
                        "humidity_avg": sum(day_data["humidity"])
                        / len(day_data["humidity"]),
                        "wind_speed_avg": sum(day_data["wind_speeds"])
                        / len(day_data["wind_speeds"]),
                        "rain_probability_max": max(day_data["rain_probability"]),
                        "rain_volume_total": sum(day_data["rain_volume"]),
                        "dominant_condition": max(
                            set(day_data["conditions"]),
                            key=day_data["conditions"].count,
                        ),
                    }
                    forecast_data["daily_forecasts"].append(daily_summary)

                logger.info(
                    f"✅ Forecast: {len(forecast_data['daily_forecasts'])} days, {len(forecast_data['hourly_forecasts'])} hourly entries"
                )
                return forecast_data

            else:
                logger.error(f"❌ Forecast API error: {response.status_code}")
                return {"available": False, "error": f"HTTP {response.status_code}"}

        except Exception as e:
            logger.error(f"❌ Error getting weather forecast: {e}")
            return {"available": False, "error": str(e)}

    def _analyze_race_weekend_weather(self, forecast: Dict, circuit_info: Dict) -> Dict:
        """Enhanced race weekend weather analysis."""
        if not forecast.get("available"):
            return {"analysis_available": False}

        analysis = {
            "race_day_conditions": {},
            "practice_conditions": {},
            "qualifying_conditions": {},
            "weather_advantage_drivers": [],
            "weather_risk_factors": [],
            "strategy_implications": [],
        }

        try:
            daily_forecasts = forecast.get("daily_forecasts", [])

            if len(daily_forecasts) >= 3:
                # Assume race weekend structure
                practice_day = daily_forecasts[0]  # Friday
                qualifying_day = daily_forecasts[1]  # Saturday
                race_day = daily_forecasts[2]  # Sunday

                # Race day analysis
                analysis["race_day_conditions"] = {
                    "temperature": race_day["temp_avg"],
                    "temp_min": race_day["temp_min"],
                    "temp_max": race_day["temp_max"],
                    "rain_probability": race_day["rain_probability_max"],
                    "wind_speed": race_day["wind_speed_avg"],
                    "conditions": race_day["dominant_condition"],
                    "weather_impact": self._assess_weather_impact(
                        race_day, circuit_info
                    ),
                }

                # Practice and qualifying conditions
                analysis["practice_conditions"] = {
                    "temperature": practice_day["temp_avg"],
                    "rain_probability": practice_day["rain_probability_max"],
                    "conditions": practice_day["dominant_condition"],
                }

                analysis["qualifying_conditions"] = {
                    "temperature": qualifying_day["temp_avg"],
                    "rain_probability": qualifying_day["rain_probability_max"],
                    "conditions": qualifying_day["dominant_condition"],
                }

                # Strategy implications
                analysis["strategy_implications"] = self._get_strategy_implications(
                    race_day, circuit_info
                )

                # Weather specialists
                analysis["weather_advantage_drivers"] = self._get_weather_specialists(
                    race_day, circuit_info
                )

                logger.info(
                    f"✅ Weather analysis complete: {race_day['temp_avg']:.1f}°C, {race_day['rain_probability_max']:.0f}% rain"
                )

        except Exception as e:
            logger.error(f"❌ Error analyzing race weekend weather: {e}")
            analysis["analysis_available"] = False

        return analysis

    def _assess_weather_impact(self, race_day: Dict, circuit_info: Dict) -> str:
        """Assess weather impact on race performance."""
        temp = race_day["temp_avg"]
        rain_prob = race_day["rain_probability_max"]

        circuit_weather_sensitivity = circuit_info.get("weather_sensitivity", 0.5)

        if rain_prob > 60:
            return "high_rain_impact"
        elif rain_prob > 30:
            return "medium_rain_risk"
        elif temp > 35:
            return "extreme_heat"
        elif temp > 30 and circuit_weather_sensitivity > 0.6:
            return "high_heat_impact"
        elif temp < 15:
            return "cold_conditions"
        else:
            return "normal_conditions"

    def _get_strategy_implications(
        self, race_day: Dict, circuit_info: Dict
    ) -> List[str]:
        """Get weather-based strategy implications."""
        implications = []

        temp = race_day["temp_avg"]
        rain_prob = race_day["rain_probability_max"]

        if rain_prob > 50:
            implications.extend(
                [
                    "Wet weather tire strategy crucial",
                    "Grid position less important",
                    "Driver skill and experience key factors",
                ]
            )
        elif rain_prob > 20:
            implications.extend(
                ["Weather window strategy important", "Flexible pit stop plans needed"]
            )

        if temp > 30:
            implications.extend(
                [
                    "Higher tire degradation expected",
                    "Cooling and reliability crucial",
                    "Physical driver endurance important",
                ]
            )
        elif temp < 15:
            implications.extend(
                [
                    "Tire warm-up challenges expected",
                    "Setup adjustments needed for cold conditions",
                ]
            )

        return implications

    def _get_weather_specialists(self, race_day: Dict, circuit_info: Dict) -> List[str]:
        """Identify weather-advantaged drivers."""
        specialists = []

        rain_prob = race_day["rain_probability_max"]
        temp = race_day["temp_avg"]

        if rain_prob > 40:
            specialists.extend(
                [
                    "Rain specialists have advantage",
                    "Experience in changeable conditions valuable",
                ]
            )

        if temp > 30:
            specialists.extend(
                [
                    "Heat-tolerant drivers favored",
                    "Teams with superior cooling systems advantaged",
                ]
            )

        return specialists

    def _get_fallback_weather(self, circuit_info: Dict) -> Dict:
        """Enhanced fallback weather data."""
        logger.warning("⚠️ Using fallback weather data")

        typical_weather = circuit_info.get("typical_weather", {})
        city = circuit_info.get("location", {}).get("city", "Unknown")

        return {
            "current_weather": {
                "available": False,
                "temperature": sum(typical_weather.get("temperature_range", [20, 25]))
                / 2,
                "error": "Using typical conditions",
            },
            "forecast": {"available": False},
            "race_weekend_analysis": {
                "analysis_available": False,
                "fallback_conditions": {
                    "typical_temperature_range": typical_weather.get(
                        "temperature_range", [20, 25]
                    ),
                    "typical_rain_probability": typical_weather.get(
                        "rain_probability", 0.3
                    )
                    * 100,
                    "heat_impact": typical_weather.get("heat_impact", "medium"),
                },
            },
            "location": circuit_info.get("location", {}),
            "timestamp": datetime.now().isoformat(),
            "source": "fallback_data",
        }

    def test_api_connection(self) -> bool:
        """Test OpenWeatherMap API connection."""
        if not self.api_key:
            return False

        try:
            # Test with London coordinates
            response = requests.get(
                f"{self.base_url}/weather",
                params={"lat": 51.5074, "lon": -0.1278, "appid": self.api_key},
                timeout=10,
            )
            return response.status_code == 200
        except:
            return False
