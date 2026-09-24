"""Weather tools for the tenant1-agents reference tenant.

Calls Open-Meteo's free geocoding and forecast APIs directly - no API key, so
the tool needs nothing beyond `requests`, already on the runtime's tenant
allow-list. A tenant tool imports the decorators by absolute path and nothing
else from NeuroStack - `modular_agents` does not exist in the runtime image.
"""

import requests

from neurostack_runtime import err, get_logger, ok, tool_category, tool_tags

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
REQUEST_TIMEOUT_SECONDS = 10

_logger = get_logger("tools.weather")


@tool_category("Weather")
@tool_tags("lookup", "geocoding", "current-conditions")
def get_weather(city: str) -> dict:
    """Look up current weather conditions for a city.

    Args:
        city: City name to look up, e.g. "Austin" or "Bengaluru".
    """
    try:
        geo_response = requests.get(
            GEOCODING_URL,
            params={"name": city, "count": 1},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        geo_response.raise_for_status()
    except requests.RequestException as exc:
        _logger.error(
            "geocoding request failed",
            extra={"context": {"city": city, "error": str(exc)}},
        )
        return err(f"could not geocode '{city}': {exc}")

    results = geo_response.json().get("results") or []
    if not results:
        return err(f"no location found for '{city}'")

    place = results[0]
    latitude, longitude = place["latitude"], place["longitude"]

    try:
        forecast_response = requests.get(
            FORECAST_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current_weather": "true",
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        forecast_response.raise_for_status()
    except requests.RequestException as exc:
        _logger.error(
            "forecast request failed",
            extra={"context": {"city": city, "error": str(exc)}},
        )
        return err(f"could not fetch weather for '{city}': {exc}")

    current = forecast_response.json().get("current_weather") or {}
    if not current:
        return err(f"no current weather data for '{city}'")

    resolved_name = ", ".join(
        part
        for part in (place.get("name"), place.get("admin1"), place.get("country"))
        if part
    )
    data = {
        "city": resolved_name,
        "latitude": latitude,
        "longitude": longitude,
        "temperature_c": current.get("temperature"),
        "windspeed_kmh": current.get("windspeed"),
        "observed_at": current.get("time"),
    }
    message = f"{resolved_name}: {data['temperature_c']}°C, wind {data['windspeed_kmh']} km/h"
    return ok(message, data)


@tool_category("Weather")
@tool_tags("conversion")
def convert_temperature(celsius: float) -> dict:
    """Convert a Celsius temperature to Fahrenheit.

    Args:
        celsius: Temperature in degrees Celsius.
    """
    fahrenheit = celsius * 9 / 5 + 32
    return ok(
        f"{celsius}°C = {fahrenheit}°F",
        {"celsius": celsius, "fahrenheit": fahrenheit},
    )
