import logging
from typing import Annotated

from .._mcp import mcp
from ..config import Config
from ..http_client import RateLimitedClient, make_rest_client
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


@mcp.tool()
async def get_local_variables(
    file_key: Annotated[str, "Figma file key"],
) -> dict:
    """Get all local variables and variable collections defined in a Figma file.

    Variables are design tokens (colors, numbers, strings, booleans) stored in
    Figma that can be applied to layers and reused across files. Collections group
    variables into modes (e.g., Light/Dark, Mobile/Desktop).

    Returns variable collections (with their modes) and all variables with their
    values per mode. Requires Enterprise plan — returns 403 on Pro/Organization.

    Use this to export your design token system programmatically.
    """
    data = await _get_client().get(f"/v1/files/{file_key}/variables/local")
    meta = data.get("meta", data)
    return {
        "file_key": file_key,
        "variable_collections": meta.get("variableCollections", {}),
        "variables": meta.get("variables", {}),
    }


@mcp.tool()
async def get_published_variables(
    file_key: Annotated[str, "Figma file key of a published variable library"],
) -> dict:
    """Get all published variables from a Figma variable library file.

    Returns variables that have been published to the team library from this file,
    making them available for use in other files. Only variables explicitly published
    appear here — local-only variables are excluded.

    Requires Enterprise plan — returns 403 on Pro/Organization.
    The file must be a published library for this to return data.
    """
    data = await _get_client().get(f"/v1/files/{file_key}/variables/published")
    meta = data.get("meta", data)
    return {
        "file_key": file_key,
        "variable_collections": meta.get("variableCollections", {}),
        "variables": meta.get("variables", {}),
    }
