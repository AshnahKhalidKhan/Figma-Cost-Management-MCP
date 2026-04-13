import time
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
    manager = OAuthManager("client-id", "client-secret", "https://example.com/cb")
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
    assert "org:activity_log_read" in result["authorization_url"]


@pytest.mark.asyncio
async def test_complete_authorization_success() -> None:
    # First generate a state
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
    await auth.start_figma_authorization()  # sets pending state
    with pytest.raises(ValueError, match="State mismatch"):
        await auth.complete_figma_authorization(code="code", state="wrong-state")


@pytest.mark.asyncio
async def test_check_auth_status_unauthenticated() -> None:
    from figma_cost_mcp.oauth import get_oauth_manager
    with patch.object(get_oauth_manager(), "load_tokens", return_value=None):
        result = await auth.check_figma_auth_status()
    assert result["authenticated"] is False
    assert "start_figma_authorization" in result["message"]


@pytest.mark.asyncio
async def test_check_auth_status_authenticated() -> None:
    from figma_cost_mcp.oauth import get_oauth_manager
    manager = get_oauth_manager()
    manager._tokens = TokenData(
        access_token="valid-token",
        refresh_token="refresh-xyz",
        expires_at=time.time() + 86400 * 30,  # 30 days
        user_id="user-999",
    )
    result = await auth.check_figma_auth_status()
    assert result["authenticated"] is True
    assert result["user_id"] == "user-999"
    assert result["token_valid"] is True
    assert result["expires_in_days"] > 0


@pytest.mark.asyncio
async def test_check_auth_status_expired_token() -> None:
    from figma_cost_mcp.oauth import get_oauth_manager
    manager = get_oauth_manager()
    manager._tokens = TokenData(
        access_token="old-token",
        refresh_token="refresh-xyz",
        expires_at=time.time() - 100,
        user_id="user-999",
    )
    result = await auth.check_figma_auth_status()
    assert result["authenticated"] is True
    assert result["token_valid"] is False
