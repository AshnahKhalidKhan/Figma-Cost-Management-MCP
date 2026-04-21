import logging

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
async def get_current_user() -> dict:
    """Get the currently authenticated Figma user's profile.

    Returns the user's ID, handle, email, and profile image URL.
    Useful for confirming which account the MCP is authenticated as.
    """
    return await _get_client().get("/v1/me")
