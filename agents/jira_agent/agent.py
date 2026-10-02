"""Reference portable agent that uses a tenant's stored credentials.

Its ``agent.json`` declares the Jira keys; the backend sends references for
exactly those, and the tools read them with ``tenant_credential()``. The agent
never sees a value and never asks the user for one.
"""

from google.adk.agents import LlmAgent
from tools.jira import fetch_ticket, update_jira_ticket

from service import tenant_model

root_agent = LlmAgent(
    name="jira_agent",
    model=tenant_model(),
    description="Fetches and updates Jira tickets using the tenant's own credentials.",
    instruction=(
        "You are a Jira assistant. Use fetch_ticket to read a ticket by its key "
        "and update_jira_ticket to comment on or resolve one. Confirm the change "
        "with the user before calling update_jira_ticket. If a tool reports that "
        "Jira credentials are not available, tell the user a tenant admin must "
        "configure them on the Credentials page. Never ask the user to paste a "
        "token or password into the chat."
    ),
    tools=[fetch_ticket, update_jira_ticket],
)
