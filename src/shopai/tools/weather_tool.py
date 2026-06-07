import json
from pathlib import Path
from typing import Type
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import urlopen

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
}

API_REFERENCE_PATH = Path(__file__).parent / "api_reference" / "weather_api.md"


class WeatherByLocationInput(BaseModel):
    """Input schema for weather lookup by location."""

    location: str = Field(
        ...,
        description="City or place name, e.g. 'San Francisco, California' or 'London'",
    )


class WeatherByLocationTool(BaseTool):
    name: str = "weather_by_location"
    description: str = (
        "Fetches current weather and a 3-day forecast for a given location. "
        "Uses the Open-Meteo API (geocoding + forecast). "
        f"API reference: {API_REFERENCE_PATH}. "
        "Returns temperature, feels-like temperature, humidity, precipitation, "
        "wind speed, and weather conditions."
    )
    args_schema: Type[BaseModel] = WeatherByLocationInput

    def _run(self, location: str) -> str:
        try:
            geo_url = (
                "https://geocoding-api.open-meteo.com/v1/search?"
                f"name={quote(location)}&count=1&language=en&format=json"
            )
            with urlopen(geo_url, timeout=10) as response:
                geo_data = json.loads(response.read().decode())

            results = geo_data.get("results")
            if not results:
                return f"No location found for '{location}'. Try a more specific city name."

            place = results[0]
            latitude = place["latitude"]
            longitude = place["longitude"]
            place_name = place.get("name", location)
            country = place.get("country", "")

            forecast_url = (
                "https://api.open-meteo.com/v1/forecast?"
                f"latitude={latitude}&longitude={longitude}"
                "&current=temperature_2m,relative_humidity_2m,apparent_temperature,"
                "precipitation,weather_code,wind_speed_10m"
                "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code"
                "&timezone=auto&forecast_days=3"
            )
            with urlopen(forecast_url, timeout=10) as response:
                forecast_data = json.loads(response.read().decode())

            current = forecast_data.get("current", {})
            daily = forecast_data.get("daily", {})
            current_units = forecast_data.get("current_units", {})
            daily_units = forecast_data.get("daily_units", {})

            current_code = current.get("weather_code")
            current_condition = WEATHER_CODES.get(current_code, f"Code {current_code}")

            daily_forecast = []
            dates = daily.get("time", [])
            for index, date in enumerate(dates):
                code = daily.get("weather_code", [None])[index]
                daily_forecast.append(
                    {
                        "date": date,
                        "temp_max": daily.get("temperature_2m_max", [None])[index],
                        "temp_max_unit": daily_units.get("temperature_2m_max", "°C"),
                        "temp_min": daily.get("temperature_2m_min", [None])[index],
                        "temp_min_unit": daily_units.get("temperature_2m_min", "°C"),
                        "precipitation_sum": daily.get("precipitation_sum", [None])[index],
                        "precipitation_unit": daily_units.get("precipitation_sum", "mm"),
                        "condition": WEATHER_CODES.get(code, f"Code {code}"),
                    }
                )

            payload = {
                "location": f"{place_name}, {country}".strip(", "),
                "coordinates": {"latitude": latitude, "longitude": longitude},
                "current": {
                    "temperature": current.get("temperature_2m"),
                    "temperature_unit": current_units.get("temperature_2m", "°C"),
                    "feels_like": current.get("apparent_temperature"),
                    "feels_like_unit": current_units.get("apparent_temperature", "°C"),
                    "humidity": current.get("relative_humidity_2m"),
                    "humidity_unit": current_units.get("relative_humidity_2m", "%"),
                    "precipitation": current.get("precipitation"),
                    "precipitation_unit": current_units.get("precipitation", "mm"),
                    "wind_speed": current.get("wind_speed_10m"),
                    "wind_speed_unit": current_units.get("wind_speed_10m", "km/h"),
                    "condition": current_condition,
                },
                "daily_forecast": daily_forecast,
                "api_reference": str(API_REFERENCE_PATH),
            }
            return json.dumps(payload, indent=2)

        except HTTPError as error:
            return f"Weather API HTTP error for '{location}': {error.code} {error.reason}"
        except URLError as error:
            return f"Weather API connection error for '{location}': {error.reason}"
        except Exception as error:
            return f"Failed to fetch weather for '{location}': {error}"
