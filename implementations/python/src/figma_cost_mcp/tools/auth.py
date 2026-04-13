import time
import logging
from typing import Annotated

from .._mcp import mcp
from ..oauth import OAuthManager, get_oauth_manager, set_oauth_manager

logger = logging.getLogger(__name__)


@mcp.tool()
async def start_figma_authorization() -> dict:
    """Begin the Figma OAuth 2.0 authorization flow.

    Returns an authorization URL to open in a browser. After the user approves,
    Figma redirects to your configured redirect_uri with 'code' and 'state' query params.
    Pass both to complete_figma_authorization to finish authentication.

    Scopes requested: org:activity_log_read, current_user:read
    """
    manager = get_oauth_manager()
    url, state = manager.get_authorization_url()
    return {
        "authorization_url": url,
        "state": state,
        "next_step": (
            "Open authorization_url in a browser. After approving, Figma will redirect to your "
            "redirect_uri with ?code=...&state=... — copy both values and call "
            "complete_figma_authorization(code=..., state=...)"
        ),
    }


@mcp.tool()
async def complete_figma_authorization(
    code: Annotated[str, "Authorization code from the Figma redirect URL's 'code' parameter"],
    state: Annotated[str, "State value from the redirect URL — must match what start_figma_authorization returned"],
) -> dict:
    """Complete the Figma OAuth flow by exchanging the authorization code for tokens.

    Tokens are persisted to ~/.figma-cost-mcp/tokens.json and auto-refreshed on expiry.
    Access tokens expire after 90 days; refresh tokens do not expire.
    """
    manager = get_oauth_manager()
    tokens = await manager.exchange_code(code, state)
    return {
        "authenticated": True,
        "user_id": tokens.user_id,
        "expires_in_days": round((tokens.expires_at - time.time()) / 86400, 1),
        "message": "Authentication successful. Tokens saved and will auto-refresh before expiry.",
    }


@mcp.tool()
async def check_figma_auth_status() -> dict:
    """Check the current Figma OAuth authentication status.

    Shows whether tokens exist, if they're valid, and how long until expiry.
    Run start_figma_authorization if not authenticated.
    """
    manager = get_oauth_manager()
    tokens = manager._tokens or manager.load_tokens()
    if not tokens:
        return {
            "authenticated": False,
            "message": "No tokens found. Run start_figma_authorization to authenticate.",
        }
    seconds_remaining = max(0, int(tokens.expires_at - time.time()))
    return {
        "authenticated": True,
        "user_id": tokens.user_id,
        "token_valid": not tokens.is_expired(),
        "expires_in_days": round(seconds_remaining / 86400, 1),
        "expires_in_seconds": seconds_remaining,
    }
