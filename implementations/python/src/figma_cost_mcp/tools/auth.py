import json
import time
import logging
import webbrowser
from typing import Annotated

from .._mcp import mcp
from ..config import Config
from ..local_auth_server import capture_oauth_callback
from ..oauth import TokenData, _TOKEN_STORE_PATH, get_oauth_manager, set_oauth_manager

logger = logging.getLogger(__name__)


@mcp.tool()
async def authorize_figma(
    timeout: Annotated[int, "Seconds to wait for browser approval before timing out"] = 120,
) -> dict:
    """Fully automated Figma OAuth authorization — no copy-pasting required.

    1. Starts a local HTTP server on a fixed port (default 8080) to capture the redirect
    2. Opens your browser to the Figma authorization page
    3. Waits for you to click Approve in the browser
    4. Captures the redirect automatically
    5. Exchanges the authorization code for tokens and saves them

    After this completes, all tools authenticate silently. Tokens refresh automatically
    using your Client ID + Secret — you never need to run this again.

    ONE-TIME SETUP: Add http://localhost:{FIGMA_CALLBACK_PORT} to your Figma OAuth app's
    allowed redirect URIs at https://www.figma.com/developers/apps before running.
    The port is fixed (default 8080) so you only do this once.
    """
    config = Config.from_env()
    port = config.figma_callback_port
    redirect_uri = f"http://localhost:{port}"

    manager = get_oauth_manager()
    auth_url, state = manager.get_authorization_url(redirect_uri=redirect_uri)

    logger.info("Opening browser for Figma authorization (callback on port %d)", port)
    webbrowser.open(auth_url)

    code, returned_state = await capture_oauth_callback(port, timeout=timeout)
    tokens = await manager.exchange_code(code, returned_state, redirect_uri=redirect_uri)

    return {
        "authenticated": True,
        "user_id": tokens.user_id,
        "expires_in_days": round((tokens.expires_at - time.time()) / 86400, 1),
        "redirect_uri_used": redirect_uri,
        "message": (
            "Authorization complete. Tokens saved to ~/.figma-cost-mcp/tokens.json. "
            "All tools will now authenticate automatically."
        ),
    }


@mcp.tool()
async def start_figma_authorization() -> dict:
    """Begin the Figma OAuth 2.0 authorization flow.

    Returns an authorization URL to open in a browser. After the user approves,
    Figma redirects to your configured redirect_uri with 'code' and 'state' query params.
    Pass both to complete_figma_authorization to finish authentication.

    After the one-time browser authorization, tokens are persisted and silently
    refreshed using your Client ID + Secret — no further browser interaction needed.

    Scopes requested: current_user:read, file_metadata:read
    """
    manager = get_oauth_manager()
    url, state = manager.get_authorization_url()
    return {
        "authorization_url": url,
        "state": state,
        "next_step": (
            "Open authorization_url in a browser. After approving, Figma redirects to your "
            "redirect_uri with ?code=...&state=... — copy both values and call "
            "complete_figma_authorization(code=..., state=...)"
        ),
    }


@mcp.tool()
async def complete_figma_authorization(
    code: str,
    state: str,
) -> dict:
    """Complete the Figma OAuth flow by exchanging the authorization code for tokens.

    Tokens are persisted to ~/.figma-cost-mcp/tokens.json. The refresh token does not
    expire — future access tokens are refreshed automatically using your Client ID + Secret.

    Args:
        code: Authorization code from the Figma redirect URL's 'code' parameter.
        state: State value from the redirect URL — must match what start_figma_authorization returned.
    """
    manager = get_oauth_manager()
    tokens = await manager.exchange_code(code, state)
    return {
        "authenticated": True,
        "user_id": tokens.user_id,
        "expires_in_days": round((tokens.expires_at - time.time()) / 86400, 1),
        "message": (
            "Authentication successful. Tokens saved to ~/.figma-cost-mcp/tokens.json. "
            "Future access tokens will refresh automatically — no browser needed again."
        ),
    }


@mcp.tool()
async def check_figma_auth_status() -> dict:
    """Check the current Figma OAuth authentication status.

    Shows whether tokens exist, if the access token is valid, and time until next refresh.
    Run authorize_figma if not authenticated.
    """
    config = Config.from_env()

    if config.figma_access_token:
        return {
            "authenticated": True,
            "mode": "personal_access_token",
            "message": "Using FIGMA_ACCESS_TOKEN (Personal Access Token). No OAuth required.",
        }

    token_file = _TOKEN_STORE_PATH
    if not token_file.exists():
        return {
            "authenticated": False,
            "token_file": str(token_file),
            "message": "No tokens found. Run authorize_figma to authenticate.",
        }

    try:
        tokens = TokenData(**json.loads(token_file.read_text()))
    except Exception as exc:
        return {
            "authenticated": False,
            "token_file": str(token_file),
            "message": f"Token file exists but could not be read: {exc}. Run authorize_figma to re-authenticate.",
        }

    seconds_remaining = max(0, int(tokens.expires_at - time.time()))
    return {
        "authenticated": True,
        "mode": "oauth",
        "user_id": tokens.user_id,
        "token_valid": not tokens.is_expired(),
        "expires_in_days": round(seconds_remaining / 86400, 1),
        "expires_in_seconds": seconds_remaining,
        "token_file": str(token_file),
    }
