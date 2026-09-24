"""tenant1-agents reference agent - looks up current weather for a city.

Contrast with any file under `modular_agents/agents/`: this imports the ADK,
one helper from the runtime package, and the tenant's own tools. Nothing else.
"""

from google.adk.agents import LlmAgent
from tools.weather import convert_temperature, get_weather

from neurostack_runtime.service import tenant_model

root_agent = LlmAgent(
    name="tenant_weather_agent",
    model=tenant_model(),
    description="Looks up current weather for a city and converts temperatures.",
    instruction=(
        "You are a weather assistant. Use get_weather to look up current "
        "conditions for a city the user names, and convert_temperature only "
        "when the user asks for a unit get_weather did not already give them. "
        "Always call a tool rather than inventing weather data yourself, and "
        "report exactly what the tool returned."
    ),
    tools=[get_weather, convert_temperature],
)
