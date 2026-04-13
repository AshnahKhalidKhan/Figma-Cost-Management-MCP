import json
import time
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
import respx

from figma_cost_mcp.oauth import (
    OAuthManager,
    TokenData,
    _REFRESH_URL,
    _TOKEN_URL,
    OAUTH_SCOPES,
)

_CLIENT_ID = "test-client-id"
_CLIENT_SECRET = "test-client-secret"
_REDIRECT_URI = "https://example.com/callback"

_TOKEN_RESPONSE = {
    "access_token": "access-abc",
    "refresh_token": "refresh-xyz",
    "expires_in": 7776000,  # 90 days
    "token_type": "bearer",
    "user_id_string": "user-999",
}

_REFRESH_RESPONSE = {
    "access_token": "access-new",
    "token_type": "bearer",
    "expires_in": 7776000,
}


@pytest.fixture
def manager() -> OAuthManager:
    return OAuthManager(_CLIENT_ID, _CLIENT_SECRET, _REDIRECT_URI)


def test_get_authorization_url_contains_client_id(manager: OAuthManager) -> None:
    url, state = manager.get_authorization_url()
    assert f"client_id={_CLIENT_ID}" in url
    assert f"redirect_uri={_REDIRECT_URI}" in url
    assert "response_type=code" in url
    assert f"state={state}" in url


def test_get_authorization_url_includes_required_scopes(manager: OAuthManager) -> None:
    url, _ = manager.get_authorization_url()
    for scope in OAUTH_SCOPES.split():
        assert scope in url


def test_get_authorization_url_returns_unique_states(manager: OAuthManager) -> None:
    _, state1 = manager.get_authorization_url()
    manager2 = OAuthManager(_CLIENT_ID, _CLIENT_SECRET, _REDIRECT_URI)
    _, state2 = manager2.get_authorization_url()
    assert state1 != state2


@pytest.mark.asyncio
async def test_exchange_code_success(manager: OAuthManager) -> None:
    _, state = manager.get_authorization_url()
    with respx.mock:
        respx.post(_TOKEN_URL).mock(return_value=httpx.Response(200, json=_TOKEN_RESPONSE))
        with patch.object(manager, "_save"):
            tokens = await manager.exchange_code("auth-code-123", state)
    assert tokens.access_token == "access-abc"
    assert tokens.refresh_token == "refresh-xyz"
    assert tokens.user_id == "user-999"
    assert tokens.expires_at > time.time()


@pytest.mark.asyncio
async def test_exchange_code_rejects_wrong_state(manager: OAuthManager) -> None:
    manager.get_authorization_url()  # sets pending state
    with pytest.raises(ValueError, match="State mismatch"):
        await manager.exchange_code("auth-code-123", "wrong-state")


@pytest.mark.asyncio
async def test_exchange_code_sends_basic_auth(manager: OAuthManager) -> None:
    _, state = manager.get_authorization_url()
    with respx.mock:
        route = respx.post(_TOKEN_URL).mock(return_value=httpx.Response(200, json=_TOKEN_RESPONSE))
        with patch.object(manager, "_save"):
            await manager.exchange_code("code", state)
    auth_header = route.calls[0].request.headers["Authorization"]
    assert auth_header.startswith("Basic ")


@pytest.mark.asyncio
async def test_refresh_updates_access_token(manager: OAuthManager) -> None:
    manager._tokens = TokenData(
        access_token="old-token",
        refresh_token="refresh-xyz",
        expires_at=time.time() + 100,
        user_id="user-999",
    )
    with respx.mock:
        respx.post(_REFRESH_URL).mock(return_value=httpx.Response(200, json=_REFRESH_RESPONSE))
        with patch.object(manager, "_save"):
            tokens = await manager.refresh()
    assert tokens.access_token == "access-new"
    assert tokens.refresh_token == "refresh-xyz"  # not rotated


@pytest.mark.asyncio
async def test_refresh_raises_without_tokens(manager: OAuthManager) -> None:
    with pytest.raises(RuntimeError, match="No tokens to refresh"):
        await manager.refresh()


@pytest.mark.asyncio
async def test_get_valid_token_returns_token_when_fresh(manager: OAuthManager) -> None:
    manager._tokens = TokenData(
        access_token="valid-token",
        refresh_token="refresh-xyz",
        expires_at=time.time() + 3600,
        user_id="user-999",
    )
    token = await manager.get_valid_token()
    assert token == "valid-token"


@pytest.mark.asyncio
async def test_get_valid_token_refreshes_when_expired(manager: OAuthManager) -> None:
    manager._tokens = TokenData(
        access_token="old-token",
        refresh_token="refresh-xyz",
        expires_at=time.time() - 10,  # already expired
        user_id="user-999",
    )
    with respx.mock:
        respx.post(_REFRESH_URL).mock(return_value=httpx.Response(200, json=_REFRESH_RESPONSE))
        with patch.object(manager, "_save"):
            token = await manager.get_valid_token()
    assert token == "access-new"


@pytest.mark.asyncio
async def test_get_valid_token_raises_when_not_authenticated(manager: OAuthManager) -> None:
    with patch.object(manager, "load_tokens", return_value=None):
        with pytest.raises(RuntimeError, match="Not authenticated"):
            await manager.get_valid_token()


def test_token_data_is_expired_when_past_expiry() -> None:
    tokens = TokenData("t", "r", expires_at=time.time() - 10, user_id="u")
    assert tokens.is_expired()


def test_token_data_not_expired_when_far_future() -> None:
    tokens = TokenData("t", "r", expires_at=time.time() + 3600, user_id="u")
    assert not tokens.is_expired()


def test_token_data_expired_within_buffer() -> None:
    tokens = TokenData("t", "r", expires_at=time.time() + 30, user_id="u")  # within 60s buffer
    assert tokens.is_expired()


def test_load_tokens_returns_none_when_no_file(manager: OAuthManager, tmp_path: Path) -> None:
    with patch("figma_cost_mcp.oauth._TOKEN_STORE_PATH", tmp_path / "nonexistent.json"):
        result = manager.load_tokens()
    assert result is None


def test_save_and_load_tokens_roundtrip(manager: OAuthManager, tmp_path: Path) -> None:
    store = tmp_path / "tokens.json"
    original = TokenData("access", "refresh", time.time() + 3600, "user-1")
    with patch("figma_cost_mcp.oauth._TOKEN_STORE_PATH", store):
        manager._save(original)
        loaded = manager.load_tokens()
    assert loaded is not None
    assert loaded.access_token == "access"
    assert loaded.user_id == "user-1"
