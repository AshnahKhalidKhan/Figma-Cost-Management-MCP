import logging
from typing import Annotated

from .._mcp import mcp
from ..config import Config
from ..http_client import RateLimitedClient, make_rest_client
from ..oauth import get_oauth_manager

logger = logging.getLogger(__name__)

_VALID_GROUP_BY = frozenset({"component", "team", "file"})

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


@mcp.tool()
async def get_library_analytics_actions(
    file_key: Annotated[str, "File key of the published library to analyze"],
    group_by: Annotated[
        str | None,
        "Aggregate results by: 'component', 'team', or 'file'. Omit for raw event data.",
    ] = None,
    start_date: Annotated[str | None, "Start date (YYYY-MM-DD). Defaults to 30 days ago."] = None,
    end_date: Annotated[str | None, "End date (YYYY-MM-DD). Defaults to today."] = None,
    cursor: Annotated[str | None, "Pagination cursor from a previous response"] = None,
) -> dict:
    """Get action analytics for a Figma published component library.

    Tracks how often components from this library are inserted, detached, or removed
    in other files. Use group_by to aggregate by component, team, or consuming file.

    Requires Enterprise plan — returns 403 on Pro/Organization.
    Only works on files published as team libraries.

    group_by values:
    - 'component': breakdown per component
    - 'team': breakdown by team using the library
    - 'file': breakdown by file using the library
    """
    if group_by and group_by not in _VALID_GROUP_BY:
        raise ValueError(f"group_by must be one of: {', '.join(sorted(_VALID_GROUP_BY))}")
    params: dict = {}
    if group_by:
        params["group_by"] = group_by
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    if cursor:
        params["cursor"] = cursor
    data = await _get_client().get(
        f"/v1/analytics/libraries/{file_key}/actions",
        params=params or None,
    )
    return {
        "file_key": file_key,
        "group_by": group_by,
        "actions": data.get("rows", data.get("actions", [])),
        "cursor": data.get("next_cursor"),
    }


@mcp.tool()
async def get_library_analytics_usages(
    file_key: Annotated[str, "File key of the published library to analyze"],
    group_by: Annotated[
        str | None,
        "Aggregate results by: 'component', 'team', or 'file'. Omit for raw usage data.",
    ] = None,
    cursor: Annotated[str | None, "Pagination cursor from a previous response"] = None,
) -> dict:
    """Get usage analytics for a Figma published component library.

    Shows the current count of how many times each component from this library
    is used (present as an instance) across all files in the team. This is a
    snapshot of current usage, not a historical event log.

    Requires Enterprise plan — returns 403 on Pro/Organization.
    Only works on files published as team libraries.

    group_by values:
    - 'component': usage count per component
    - 'team': usage aggregated by team
    - 'file': usage aggregated by consuming file
    """
    if group_by and group_by not in _VALID_GROUP_BY:
        raise ValueError(f"group_by must be one of: {', '.join(sorted(_VALID_GROUP_BY))}")
    params: dict = {}
    if group_by:
        params["group_by"] = group_by
    if cursor:
        params["cursor"] = cursor
    data = await _get_client().get(
        f"/v1/analytics/libraries/{file_key}/usages",
        params=params or None,
    )
    return {
        "file_key": file_key,
        "group_by": group_by,
        "usages": data.get("rows", data.get("usages", [])),
        "cursor": data.get("next_cursor"),
    }
