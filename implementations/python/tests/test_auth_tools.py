import json
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx

from figma_cost_mcp.oauth import OAuthManager, TokenData, _TOKEN_URL, set_oauth_manager
from figma_cost_mcp.tools import auth

_TOKEN_RESPONSE = {
    "access_token": "access-abc",
    "refresh_token": "refresh-xyz",
    "expires_in": 7776000,
    "token_type": "bearer",
    "user_id_string": "user-999",
}


@pytest.fixture(autouse=True)
def inject_mock_manager() -> None:
    manager = OAuthManager("client-id", "client-secret", "https://localhost")
    set_oauth_manager(manager)
    yield
    set_oauth_manager(None)


@pytest.mark.asyncio
async def test_start_authorization_returns_url() -> None:
    result = await auth.start_figma_authorization()
    assert "authorization_url" in result
    assert "state" in result
    assert "figma.com/oauth" in result["authorization_url"]
    assert result["state"]


@pytest.mark.asyncio
async def test_start_authorization_url_contains_scopes() -> None:
    result = await auth.start_figma_authorization()
    assert "current_user:read" in result["authorization_url"]
    assert "file_metadata:read" in result["authorization_url"]


@pytest.mark.asyncio
async def test_complete_authorization_success() -> None:
    start_result = await auth.start_figma_authorization()
    state = start_result["state"]
    with respx.mock:
        respx.post(_TOKEN_URL).mock(return_value=httpx.Response(200, json=_TOKEN_RESPONSE))
        from figma_cost_mcp.oauth import get_oauth_manager
        with patch.object(get_oauth_manager(), "_save"):
            result = await auth.complete_figma_authorization(code="auth-code", state=state)
    assert result["authenticated"] is True
    assert result["user_id"] == "user-999"
    assert result["expires_in_days"] > 0


@pytest.mark.asyncio
async def test_complete_authorization_wrong_state_raises() -> None:
    await auth.start_figma_authorization()
    with pytest.raises(ValueError, match="State mismatch"):
        await auth.complete_figma_authorization(code="code", state="wrong-state")


@pytest.mark.asyncio
async def test_check_auth_status_unauthenticated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FIGMA_ACCESS_TOKEN", "")
    nonexistent = tmp_path / "tokens.json"
    with patch("figma_cost_mcp.tools.auth._TOKEN_STORE_PATH", nonexistent):
        result = await auth.check_figma_auth_status()
    assert result["authenticated"] is False
    assert "authorize_figma" in result["message"]


@pytest.mark.asyncio
async def test_check_auth_status_authenticated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FIGMA_ACCESS_TOKEN", "")
    token_file = tmp_path / "tokens.json"
    token_file.write_text(json.dumps({
        "access_token": "valid-token",
        "refresh_token": "refresh-xyz",
        "expires_at": time.time() + 86400 * 30,
        "user_id": "user-999",
    }))
    with patch("figma_cost_mcp.tools.auth._TOKEN_STORE_PATH", token_file):
        result = await auth.check_figma_auth_status()
    assert result["authenticated"] is True
    assert result["user_id"] == "user-999"
    assert result["token_valid"] is True


@pytest.mark.asyncio
async def test_check_auth_status_expired_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FIGMA_ACCESS_TOKEN", "")
    token_file = tmp_path / "tokens.json"
    token_file.write_text(json.dumps({
        "access_token": "old-token",
        "refresh_token": "refresh-xyz",
        "expires_at": time.time() - 100,
        "user_id": "user-999",
    }))
    with patch("figma_cost_mcp.tools.auth._TOKEN_STORE_PATH", token_file):
        result = await auth.check_figma_auth_status()
    assert result["authenticated"] is True
    assert result["token_valid"] is False


@pytest.fixture
def _oauth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIGMA_CLIENT_ID", "client-id")
    monkeypatch.setenv("FIGMA_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("FIGMA_REDIRECT_URI", "https://localhost")
    monkeypatch.setenv("FIGMA_ACCESS_TOKEN", "")
    monkeypatch.setenv("FIGMA_SCIM_TOKEN", "")
    monkeypatch.setenv("FIGMA_ORG_ID", "org-1")


@pytest.mark.asyncio
async def test_authorize_figma_completes_full_flow(
    monkeypatch: pytest.MonkeyPatch, _oauth_env: None
) -> None:
    monkeypatch.setenv("FIGMA_CALLBACK_PORT", "19876")
    fixed_state = "fixed-test-state"

    with (
        patch("figma_cost_mcp.tools.auth.webbrowser.open"),
        patch("figma_cost_mcp.oauth.secrets.token_urlsafe", return_value=fixed_state),
        patch(
            "figma_cost_mcp.tools.auth.capture_oauth_callback",
            new=AsyncMock(return_value=("auth-code", fixed_state)),
        ),
        respx.mock,
    ):
        respx.post(_TOKEN_URL).mock(return_value=httpx.Response(200, json=_TOKEN_RESPONSE))
        from figma_cost_mcp.oauth import get_oauth_manager
        with patch.object(get_oauth_manager(), "_save"):
            result = await auth.authorize_figma(timeout=5)

    assert result["authenticated"] is True
    assert "Authorization complete" in result["message"]
    assert result["redirect_uri_used"] == "http://localhost:19876"


@pytest.mark.asyncio
async def test_authorize_figma_opens_browser(
    monkeypatch: pytest.MonkeyPatch, _oauth_env: None
) -> None:
    monkeypatch.setenv("FIGMA_CALLBACK_PORT", "19877")
    fixed_state = "fixed-test-state-2"
    opened_urls: list[str] = []

    with (
        patch("figma_cost_mcp.tools.auth.webbrowser.open", side_effect=opened_urls.append),
        patch("figma_cost_mcp.oauth.secrets.token_urlsafe", return_value=fixed_state),
        patch(
            "figma_cost_mcp.tools.auth.capture_oauth_callback",
            new=AsyncMock(return_value=("auth-code", fixed_state)),
        ),
        respx.mock,
    ):
        respx.post(_TOKEN_URL).mock(return_value=httpx.Response(200, json=_TOKEN_RESPONSE))
        from figma_cost_mcp.oauth import get_oauth_manager
        with patch.object(get_oauth_manager(), "_save"):
            await auth.authorize_figma(timeout=5)

    assert len(opened_urls) == 1
    assert "figma.com/oauth" in opened_urls[0]
