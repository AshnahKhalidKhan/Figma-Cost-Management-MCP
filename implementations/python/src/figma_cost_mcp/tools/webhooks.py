import logging
from typing import Annotated

from .._mcp import mcp
from ..config import Config
from ..http_client import RateLimitedClient, make_rest_client
from ..models.webhooks import WEBHOOK_EVENT_TYPES, Webhook, TeamWebhooksResponse
from ..oauth import get_oauth_manager

logger = logging.getLogger(__name__)

_client: RateLimitedClient | None = None


def _get_client() -> RateLimitedClient:
    global _client
    if _client is None:
        config = Config.from_env()
        if config.figma_access_token:
            _client = make_rest_client(token=config.figma_access_token)
        else:
            _client = make_rest_client(token_provider=get_oauth_manager().get_valid_token)
    return _client


def _set_client(client: RateLimitedClient | None) -> None:
    global _client
    _client = client


def _resolve_team_id(team_id: str | None) -> str:
    if team_id:
        return team_id
    env_team_id = Config.from_env().figma_team_id
    if not env_team_id:
        raise ValueError(
            "team_id is required. Set FIGMA_TEAM_ID in your environment, or pass it as a parameter."
        )
    return env_team_id


def _fmt_webhook(w: dict) -> dict:
    return {
        "id": w.get("id"),
        "team_id": w.get("team_id"),
        "event_type": w.get("event_type"),
        "endpoint": w.get("endpoint"),
        "status": w.get("status"),
        "description": w.get("description"),
        "client_id": w.get("client_id"),
    }


@mcp.tool()
async def list_team_webhooks(
    team_id: Annotated[str | None, "Figma team ID. Defaults to FIGMA_TEAM_ID env var."] = None,
) -> dict:
    """List all webhooks configured for a Figma team.

    Returns each webhook's ID, event type, endpoint URL, status (ACTIVE/PAUSED),
    and description. Use webhook IDs with get_webhook, update_webhook, or delete_webhook.

    Supported event types: FILE_UPDATE, FILE_VERSION_UPDATE, FILE_DELETE,
    LIBRARY_PUBLISH, FILE_COMMENT.
    """
    tid = _resolve_team_id(team_id)
    data = await _get_client().get(f"/v2/teams/{tid}/webhooks")
    webhooks = data.get("webhooks", [])
    return {
        "team_id": tid,
        "webhooks": [_fmt_webhook(w) for w in webhooks],
        "total": len(webhooks),
    }


@mcp.tool()
async def get_webhook(
    webhook_id: Annotated[str, "Webhook ID (from list_team_webhooks)"],
) -> dict:
    """Get details for a single Figma webhook by its ID.

    Returns the webhook's event type, endpoint URL, status, passcode, and description.
    """
    data = await _get_client().get(f"/v2/webhooks/{webhook_id}")
    return _fmt_webhook(data)


@mcp.tool()
async def create_webhook(
    event_type: Annotated[
        str,
        "Event that triggers this webhook. One of: FILE_UPDATE, FILE_VERSION_UPDATE, "
        "FILE_DELETE, LIBRARY_PUBLISH, FILE_COMMENT",
    ],
    endpoint: Annotated[str, "HTTPS URL that Figma will POST to when the event fires"],
    passcode: Annotated[str, "Secret included in every webhook payload for signature verification"],
    team_id: Annotated[str | None, "Figma team ID. Defaults to FIGMA_TEAM_ID env var."] = None,
    description: Annotated[str | None, "Human-readable description of this webhook's purpose"] = None,
) -> dict:
    """Create a new Figma webhook to receive real-time file and library events.

    Figma will send an HTTP POST to your endpoint whenever the specified event occurs.
    Include the passcode in your endpoint to verify requests are genuinely from Figma.

    Supported events:
    - FILE_UPDATE: file content changed (debounced ~30s)
    - FILE_VERSION_UPDATE: a named version was saved
    - FILE_DELETE: file was deleted
    - LIBRARY_PUBLISH: team library was published
    - FILE_COMMENT: a comment was added or resolved
    """
    event_upper = event_type.upper()
    if event_upper not in WEBHOOK_EVENT_TYPES:
        raise ValueError(
            f"Invalid event_type '{event_type}'. Must be one of: {', '.join(sorted(WEBHOOK_EVENT_TYPES))}"
        )
    tid = _resolve_team_id(team_id)
    body: dict = {
        "event_type": event_upper,
        "team_id": tid,
        "endpoint": endpoint,
        "passcode": passcode,
    }
    if description:
        body["description"] = description
    data = await _get_client().post("/v2/webhooks", json=body)
    return _fmt_webhook(data)


@mcp.tool()
async def update_webhook(
    webhook_id: Annotated[str, "Webhook ID to update (from list_team_webhooks)"],
    endpoint: Annotated[str | None, "New HTTPS endpoint URL"] = None,
    passcode: Annotated[str | None, "New passcode for signature verification"] = None,
    description: Annotated[str | None, "New description"] = None,
    status: Annotated[str | None, "New status: ACTIVE or PAUSED"] = None,
) -> dict:
    """Update an existing Figma webhook's endpoint, passcode, description, or status.

    Use status=PAUSED to temporarily disable a webhook without deleting it.
    Use status=ACTIVE to re-enable a paused webhook.
    Only provided fields are updated — omit fields you don't want to change.
    """
    body: dict = {}
    if endpoint is not None:
        body["endpoint"] = endpoint
    if passcode is not None:
        body["passcode"] = passcode
    if description is not None:
        body["description"] = description
    if status is not None:
        body["status"] = status.upper()
    if not body:
        raise ValueError("At least one field must be provided to update.")
    data = await _get_client().put(f"/v2/webhooks/{webhook_id}", json=body)
    return _fmt_webhook(data)


@mcp.tool()
async def delete_webhook(
    webhook_id: Annotated[str, "Webhook ID to delete (from list_team_webhooks)"],
) -> dict:
    """Permanently delete a Figma webhook.

    This cannot be undone. The webhook will immediately stop receiving events.
    Use update_webhook with status=PAUSED to temporarily disable instead.
    """
    await _get_client().delete(f"/v2/webhooks/{webhook_id}")
    return {"deleted": True, "webhook_id": webhook_id}


@mcp.tool()
async def get_webhook_requests(
    webhook_id: Annotated[str, "Webhook ID (from list_team_webhooks)"],
) -> dict:
    """Get recent delivery attempts for a Figma webhook.

    Returns the last ~25 delivery attempts with their timestamps, response status codes,
    and any error messages. Use this to debug webhook delivery failures or verify
    that events are being received correctly.
    """
    data = await _get_client().get(f"/v2/webhooks/{webhook_id}/requests")
    requests = data.get("requests", [])
    return {
        "webhook_id": webhook_id,
        "requests": [
            {
                "id": r.get("id"),
                "created_at": r.get("created_at"),
                "sent_at": r.get("sent_at"),
                "response_status": r.get("response_status"),
                "error": r.get("error"),
                "error_reason": r.get("error_reason"),
            }
            for r in requests
        ],
        "total": len(requests),
    }
