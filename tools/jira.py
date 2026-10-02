"""Jira tools for the reference tenant, using the tenant's own credentials.

The runtime-side counterpart of ``modular_agents/tools/jira_tools.py``. There the
control plane looks up and resolves the credential itself; here the tool asks
for it by key and the runtime resolves the tenant's stored reference from their
own Secrets Manager. The agent must declare each key in its ``agent.json``::

    {"credentials": ["JIRA_API_TOKEN", "JIRA_URL", "JIRA_USERNAME"]}

Never put a credential value in a tool result or a log line.
"""

import requests

from errors import CredentialError
from registry import tool_category, tool_tags, tool_timeout
from service import tenant_credential

#: Connect, read. A hung Jira call would otherwise hold a tool worker thread
#: for good, and a thread cannot be killed.
REQUEST_TIMEOUT_SECONDS = (5, 30)

#: The harness stops waiting for a tool after this long (its default is 30s).
#: Each request above may take up to 35s, and update_jira_ticket makes up to
#: four in a row, so the default would cut it off between the comment and the
#: transition. The worker keeps running after the harness gives up, so the model
#: would be told to retry a write that is still in flight.
TOOL_TIMEOUT_SECONDS = 120


def _jira() -> tuple[str, tuple[str, str]]:
    """Base URL and basic-auth pair for the tenant's Jira."""
    base_url = tenant_credential("JIRA_URL").rstrip("/")
    auth = (tenant_credential("JIRA_USERNAME"), tenant_credential("JIRA_API_TOKEN"))
    return base_url, auth


def _credential_failure(exc: CredentialError) -> dict:
    # The message names keys and ARNs only, never a value.
    return {
        "success": False,
        "message": (
            f"Jira credentials are not available: {exc}. A tenant admin must "
            "configure them on the Credentials page; never paste a token into chat."
        ),
        "data": {},
    }


def _adf_paragraph(text: str) -> dict:
    """A comment body in Atlassian Document Format."""
    return {
        "body": {
            "type": "doc",
            "version": 1,
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": text}]}
            ],
        }
    }


def _adf_text(node: object) -> str:
    """Plain text from an ADF node, walking nested paragraphs."""
    if not isinstance(node, dict):
        return ""
    if node.get("type") == "text":
        return str(node.get("text") or "")
    return "".join(_adf_text(child) for child in node.get("content") or [])


def _http_failure(exc: requests.exceptions.RequestException) -> dict:
    code = getattr(getattr(exc, "response", None), "status_code", None)
    if code == 404:
        message = "Ticket not found."
    elif code in (401, 403):
        message = "Jira rejected the tenant's credentials."
    else:
        message = f"Jira request failed: {type(exc).__name__}"
    return {"success": False, "message": message, "data": {}}


@tool_category("JIRA")
@tool_tags("jira", "ticket", "fetch")
@tool_timeout(TOOL_TIMEOUT_SECONDS)
def fetch_ticket(ticket_id: str) -> dict:
    """Retrieve a Jira ticket by its key.

    Args:
        ticket_id: The ticket key, e.g. PROJ-123.
    """
    try:
        base_url, auth = _jira()
        response = requests.get(
            f"{base_url}/rest/api/3/issue/{ticket_id}",
            auth=auth,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except CredentialError as exc:
        return _credential_failure(exc)
    except requests.exceptions.RequestException as exc:
        return _http_failure(exc)

    fields = response.json().get("fields") or {}
    comments = (fields.get("comment") or {}).get("comments") or []
    return {
        "success": True,
        "message": "Ticket retrieved successfully.",
        "data": {
            "id": ticket_id,
            "summary": fields.get("summary", ""),
            "description": _adf_text(fields.get("description")),
            "priority": (fields.get("priority") or {}).get("name", ""),
            "status": (fields.get("status") or {}).get("name", ""),
            "reporter_email": (fields.get("reporter") or {}).get("emailAddress", ""),
            "created_at": fields.get("created", ""),
            "comments": [_adf_text(comment.get("body")) for comment in comments],
        },
    }


@tool_category("JIRA")
@tool_tags("jira", "ticket", "update", "status")
@tool_timeout(TOOL_TIMEOUT_SECONDS)
def update_jira_ticket(
    ticket_id: str,
    status: str,
    resolution_note: str,
    draft_response: str = "",
) -> dict:
    """Add a resolution note to a Jira ticket and move it to Done if resolved.

    Args:
        ticket_id: The ticket key, e.g. PROJ-123.
        status: The desired status; "resolved" or "closed" transitions to Done/Closed.
        resolution_note: Added to the ticket as a comment.
        draft_response: Optional second comment with a draft reply.
    """
    try:
        base_url, auth = _jira()
        issue_url = f"{base_url}/rest/api/3/issue/{ticket_id}"

        requests.post(
            f"{issue_url}/comment",
            auth=auth,
            json=_adf_paragraph(resolution_note),
            timeout=REQUEST_TIMEOUT_SECONDS,
        ).raise_for_status()

        status_updated = False
        if status.lower() in ("resolved", "closed"):
            transitions = requests.get(
                f"{issue_url}/transitions", auth=auth, timeout=REQUEST_TIMEOUT_SECONDS
            )
            transitions.raise_for_status()
            transition_id = next(
                (
                    item.get("id")
                    for item in transitions.json().get("transitions", [])
                    if str(item.get("name", "")).lower() in ("done", "closed")
                ),
                None,
            )
            if transition_id is None:
                return {
                    "success": False,
                    "message": f"No Done/Closed transition is available for '{status}'.",
                    "data": {
                        "ticket_id": ticket_id,
                        "status_updated": False,
                        "comment_added": True,
                    },
                }
            requests.post(
                f"{issue_url}/transitions",
                auth=auth,
                json={"transition": {"id": transition_id}},
                timeout=REQUEST_TIMEOUT_SECONDS,
            ).raise_for_status()
            status_updated = True

        if draft_response:
            requests.post(
                f"{issue_url}/comment",
                auth=auth,
                json=_adf_paragraph(draft_response),
                timeout=REQUEST_TIMEOUT_SECONDS,
            ).raise_for_status()
    except CredentialError as exc:
        return _credential_failure(exc)
    except requests.exceptions.RequestException as exc:
        return _http_failure(exc)

    return {
        "success": True,
        "message": "Ticket updated successfully.",
        "data": {
            "ticket_id": ticket_id,
            "status_updated": status_updated,
            "comment_added": True,
        },
    }
