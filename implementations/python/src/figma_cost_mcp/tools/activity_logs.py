import logging
from typing import Annotated, Any

from .._mcp import mcp
from ..config import Config
from ..http_client import RateLimitedClient, make_rest_client
from ..models.activity_logs import BILLING_ACTION_TYPES, USER_MGMT_ACTION_TYPES
from ..oauth import get_oauth_manager

logger = logging.getLogger(__name__)

_client: RateLimitedClient | None = None
_org_id: str | None = None


def _get_client_and_org() -> tuple[RateLimitedClient, str]:
    global _client, _org_id
    if _client is None:
        config = Config.from_env()
        if config.figma_access_token:
            _client = make_rest_client(token=config.figma_access_token)
        else:
            _client = make_rest_client(token_provider=get_oauth_manager().get_valid_token)
        _org_id = config.figma_org_id
    return _client, _org_id  # type: ignore[return-value]


def _set_client(client: RateLimitedClient | None, org_id: str | None) -> None:
    global _client, _org_id
    _client = client
    _org_id = org_id


def _build_params(
    org_id: str,
    event_types: list[str],
    limit: int,
    start_time: str | None,
    end_time: str | None,
    cursor: str | None,
) -> dict[str, Any]:
    params: dict[str, Any] = {"org_id": org_id, "limit": limit, "event_type": event_types}
    if start_time:
        params["start_time"] = start_time
    if end_time:
        params["end_time"] = end_time
    if cursor:
        params["cursor"] = cursor
    return params


@mcp.tool()
async def get_billing_activity_logs(
    start_time: Annotated[str | None, "ISO 8601 start timestamp e.g. 2024-01-01T00:00:00Z"] = None,
    end_time: Annotated[str | None, "ISO 8601 end timestamp"] = None,
    limit: Annotated[int, "Max entries to return (max 1000)"] = 100,
    cursor: Annotated[str | None, "Pagination cursor from previous response"] = None,
) -> dict:
    """Retrieve billing-related activity logs for the Figma organization.

    Covers: seat type changes, license group membership, seat upgrade workflows,
    workspace membership changes, renewal events, and default license type changes.
    Requires Organization or Enterprise plan.
    """
    client, org_id = _get_client_and_org()
    params = _build_params(org_id, list(BILLING_ACTION_TYPES), limit, start_time, end_time, cursor)
    return await client.get("/v1/activity_logs", params=params)


@mcp.tool()
async def get_user_management_activity_logs(
    start_time: Annotated[str | None, "ISO 8601 start timestamp"] = None,
    end_time: Annotated[str | None, "ISO 8601 end timestamp"] = None,
    limit: Annotated[int, "Max entries to return (max 1000)"] = 100,
    cursor: Annotated[str | None, "Pagination cursor from previous response"] = None,
) -> dict:
    """Retrieve user management activity logs for the Figma organization.

    Covers: user creation/deletion, permission changes, and SCIM-provisioned user events.
    Requires Organization or Enterprise plan.
    """
    client, org_id = _get_client_and_org()
    params = _build_params(org_id, list(USER_MGMT_ACTION_TYPES), limit, start_time, end_time, cursor)
    return await client.get("/v1/activity_logs", params=params)


@mcp.tool()
async def get_activity_logs(
    event_types: Annotated[
        list[str] | None,
        "Specific action types to filter by. Leave empty for all billing and user management events.",
    ] = None,
    start_time: Annotated[str | None, "ISO 8601 start timestamp"] = None,
    end_time: Annotated[str | None, "ISO 8601 end timestamp"] = None,
    limit: Annotated[int, "Max entries to return (max 1000)"] = 100,
    cursor: Annotated[str | None, "Pagination cursor from previous response"] = None,
) -> dict:
    """Retrieve activity logs with optional event type filtering and time range.

    When event_types is empty, returns all billing and user management events combined.
    Requires Organization or Enterprise plan.
    """
    client, org_id = _get_client_and_org()
    types = event_types or list(BILLING_ACTION_TYPES | USER_MGMT_ACTION_TYPES)
    params = _build_params(org_id, types, limit, start_time, end_time, cursor)
    return await client.get("/v1/activity_logs", params=params)
