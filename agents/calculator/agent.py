"""Reference portable agent - what the generator should emit after NS-101.

Contrast with any file under ``modular_agents/agents/``: 131 of the 133 there
import ``modular_agents.core.llm``, ``core.guardrails.*``, ``core.credential_tool``
and friends, none of which exist in the runtime image. This file imports the ADK,
one helper from the runtime package, and the tenant's own tools. Nothing else.

The model comes from ``tenant_model()`` rather than being named here, so which
provider actually serves this agent is a platform decision made at the LiteLLM
proxy - not something baked into a tenant's repository.
"""

from google.adk.agents import LlmAgent
from tools.arithmetic import add_numbers, count_primes

from service import tenant_model

root_agent = LlmAgent(
    name="calculator",
    model=tenant_model(),
    description="Performs arithmetic using the tenant's own tools.",
    instruction=(
        "You are a calculator. Use add_numbers to add two integers and "
        "count_primes to count primes below a limit. Always call a tool rather "
        "than computing the answer yourself, and report what the tool returned."
    ),
    tools=[add_numbers, count_primes],
)
