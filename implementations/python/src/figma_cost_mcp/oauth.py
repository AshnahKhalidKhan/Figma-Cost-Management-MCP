import base64
import json
import logging
import secrets
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

_TOKEN_STORE_PATH = Path.home() / ".figma-cost-mcp" / "tokens.json"
_AUTH_URL = "https://www.figma.com/oauth"
_TOKEN_URL = "https://api.figma.com/v1/oauth/token"
_REFRESH_URL = "https://api.figma.com/v1/oauth/refresh"

# Scopes for cost/billing management on Pro plans.
# org:activity_log_read is Enterprise-only and must NOT be included here.
# Activity Logs tools will work via PAT with the appropriate plan, not OAuth.
OAUTH_SCOPES = "current_user:read file_metadata:read"


@dataclass
class TokenData:
    access_token: str
    refresh_token: str
    expires_at: float  # Unix timestamp
    user_id: str

    def is_expired(self) -> bool:
        """Returns True if the token expires within 60 seconds."""
        return time.time() >= self.expires_at - 60


class OAuthManager:
    """Manages the Figma OAuth 2.0 authorization code flow.

    Handles token exchange, persistence, and automatic refresh.
    Tokens persist to ~/.figma-cost-mcp/tokens.json between sessions.
    After the first browser authorization, refresh tokens do not expire —
    subsequent access tokens are refreshed silently using Client ID + Secret.
    """

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._tokens: TokenData | None = None
        self._pending_state: str | None = None

    def get_authorization_url(self, redirect_uri: str | None = None) -> tuple[str, str]:
        """Generate the Figma OAuth authorization URL.

        Returns (authorization_url, state). Pass state to exchange_code() for CSRF protection.
        redirect_uri overrides the configured value — used by the automated flow.
        """
        state = secrets.token_urlsafe(16)
        self._pending_state = state
        params = {
            "client_id": self._client_id,
            "redirect_uri": redirect_uri or self._redirect_uri,
            "scope": OAUTH_SCOPES,
            "state": state,
            "response_type": "code",
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{_AUTH_URL}?{query}", state

    async def exchange_code(self, code: str, state: str, redirect_uri: str | None = None) -> TokenData:
        """Exchange an authorization code for access and refresh tokens.

        Raises ValueError if the state doesn't match (CSRF protection).
        Codes expire 30 seconds after Figma issues them.
        redirect_uri overrides the configured value — must match what was sent in the auth URL.
        """
        if state != self._pending_state:
            raise ValueError("State mismatch — possible CSRF attack. Restart the authorization flow.")
        self._pending_state = None

        async with httpx.AsyncClient() as client:
            response = await client.post(
                _TOKEN_URL,
                headers={
                    "Authorization": f"Basic {self._basic_credentials()}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "redirect_uri": redirect_uri or self._redirect_uri,
                    "code": code,
                    "grant_type": "authorization_code",
                },
            )
            response.raise_for_status()
            data = response.json()

        tokens = TokenData(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_at=time.time() + data["expires_in"],
            user_id=str(data["user_id_string"]),
        )
        self._tokens = tokens
        self._save(tokens)
        logger.info("OAuth tokens obtained for user %s", tokens.user_id)
        return tokens

    async def refresh(self) -> TokenData:
        """Refresh the access token using the stored refresh token.

        Figma refresh tokens do not expire — only the access token changes.
        Client ID + Secret are used to authenticate the refresh request.
        """
        if not self._tokens:
            raise RuntimeError("No tokens to refresh. Complete the authorization flow first.")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                _REFRESH_URL,
                headers={
                    "Authorization": f"Basic {self._basic_credentials()}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={"refresh_token": self._tokens.refresh_token},
            )
            response.raise_for_status()
            data = response.json()

        self._tokens = TokenData(
            access_token=data["access_token"],
            refresh_token=self._tokens.refresh_token,
            expires_at=time.time() + data["expires_in"],
            user_id=self._tokens.user_id,
        )
        self._save(self._tokens)
        logger.info("OAuth token refreshed for user %s", self._tokens.user_id)
        return self._tokens

    async def get_valid_token(self) -> str:
        """Return a valid access token, loading from disk and refreshing if needed."""
        if self._tokens is None:
            self._tokens = self.load_tokens()
        if self._tokens is None:
            raise RuntimeError(
                "Not authenticated with Figma. "
                "Call start_figma_authorization and complete_figma_authorization first."
            )
        if self._tokens.is_expired():
            await self.refresh()
        return self._tokens.access_token

    @property
    def current_user_id(self) -> str | None:
        tokens = self._tokens or self.load_tokens()
        return tokens.user_id if tokens else None

    def load_tokens(self) -> TokenData | None:
        if not _TOKEN_STORE_PATH.exists():
            return None
        try:
            data = json.loads(_TOKEN_STORE_PATH.read_text())
            return TokenData(**data)
        except Exception as exc:
            logger.warning("Failed to load stored tokens: %s", exc)
            return None

    def _save(self, tokens: TokenData) -> None:
        _TOKEN_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _TOKEN_STORE_PATH.write_text(json.dumps(asdict(tokens)))

    def _basic_credentials(self) -> str:
        return base64.b64encode(f"{self._client_id}:{self._client_secret}".encode()).decode()


# Module-level singleton — shared across all tools
_manager: OAuthManager | None = None


def get_oauth_manager() -> OAuthManager:
    global _manager
    if _manager is None:
        from .config import Config
        config = Config.from_env()
        if not config.figma_client_id or not config.figma_client_secret:
            raise RuntimeError(
                "OAuth is not configured. Set FIGMA_CLIENT_ID and FIGMA_CLIENT_SECRET, "
                "or set FIGMA_ACCESS_TOKEN to use a Personal Access Token instead."
            )
        _manager = OAuthManager(
            client_id=config.figma_client_id,
            client_secret=config.figma_client_secret,
            redirect_uri=config.figma_redirect_uri or "https://localhost",
        )
    return _manager


def set_oauth_manager(manager: OAuthManager | None) -> None:
    """Replace the singleton — used in tests."""
    global _manager
    _manager = manager
