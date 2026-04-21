import json
import time
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
import respx

from figma_cost_mcp.oauth import OAuthManager, TokenData, _REFRESH_URL, _TOKEN_URL

_CLIENT_ID = "client-id"
_CLIENT_SECRET = "client-secret"
_REDIRECT_URI = "https://localhost"

_TOKEN_RESPONSE = {
    "access_token": "access-abc",
    "refresh_token": "refresh-xyz",
    "expires_in": 7776000,  # 90 days
    "token_type": "bearer",
    "user_id_string": "user-999",
}


@pytest.fixture
def manager() -> OAuthManager:
    return OAuthManager(_CLIENT_ID, _CLIENT_SECRET, _REDIRECT_URI)


def test_get_authorization_url_contains_client_id(manager: OAuthManager) -> None:
    url, _ = manager.get_authorization_url()
    assert _CLIENT_ID in url


def test_get_authorization_url_contains_scopes(manager: OAuthManager) -> None:
    url, _ = manager.get_authorization_url()
    assert "current_user:read" in url
    assert "file_metadata:read" in url


def test_get_authorization_url_returns_state(manager: OAuthManager) -> None:
    _, state = manager.get_authorization_url()
    assert len(state) > 0


def test_get_authorization_url_sets_pending_state(manager: OAuthManager) -> None:
    _, state = manager.get_authorization_url()
    assert manager._pending_state == state


@pytest.mark.asyncio
async def test_exchange_code_state_mismatch_raises(manager: OAuthManager) -> None:
    manager.get_authorization_url()
    with pytest.raises(ValueError, match="State mismatch"):
        await manager.exchange_code("code", "wrong-state")


@pytest.mark.asyncio
async def test_exchange_code_success(manager: OAuthManager, tmp_path: Path) -> None:
    _, state = manager.get_authorization_url()
    with respx.mock:
        respx.post(_TOKEN_URL).mock(return_value=httpx.Response(200, json=_TOKEN_RESPONSE))
        with patch.object(manager, "_save"):
            tokens = await manager.exchange_code("auth-code", state)
    assert tokens.access_token == "access-abc"
    assert tokens.refresh_token == "refresh-xyz"
    assert tokens.user_id == "user-999"
    assert tokens.expires_at > time.time()


@pytest.mark.asyncio
async def test_exchange_code_clears_pending_state(manager: OAuthManager) -> None:
    _, state = manager.get_authorization_url()
    with respx.mock:
        respx.post(_TOKEN_URL).mock(return_value=httpx.Response(200, json=_TOKEN_RESPONSE))
        with patch.object(manager, "_save"):
            await manager.exchange_code("code", state)
    assert manager._pending_state is None


@pytest.mark.asyncio
async def test_refresh_updates_access_token(manager: OAuthManager) -> None:
    manager._tokens = TokenData(
        access_token="old-token",
        refresh_token="refresh-xyz",
        expires_at=time.time() - 100,
        user_id="user-999",
    )
    refresh_response = {**_TOKEN_RESPONSE, "access_token": "new-token"}
    with respx.mock:
        respx.post(_REFRESH_URL).mock(return_value=httpx.Response(200, json=refresh_response))
        with patch.object(manager, "_save"):
            tokens = await manager.refresh()
    assert tokens.access_token == "new-token"
    assert tokens.refresh_token == "refresh-xyz"  # unchanged


@pytest.mark.asyncio
async def test_refresh_without_tokens_raises(manager: OAuthManager) -> None:
    with pytest.raises(RuntimeError, match="No tokens to refresh"):
        await manager.refresh()


@pytest.mark.asyncio
async def test_get_valid_token_returns_access_token(manager: OAuthManager) -> None:
    manager._tokens = TokenData(
        access_token="valid-token",
        refresh_token="refresh-xyz",
        expires_at=time.time() + 86400,
        user_id="user-999",
    )
    token = await manager.get_valid_token()
    assert token == "valid-token"


@pytest.mark.asyncio
async def test_get_valid_token_refreshes_expired_token(manager: OAuthManager) -> None:
    manager._tokens = TokenData(
        access_token="old-token",
        refresh_token="refresh-xyz",
        expires_at=time.time() - 100,
        user_id="user-999",
    )
    refresh_response = {**_TOKEN_RESPONSE, "access_token": "refreshed-token"}
    with respx.mock:
        respx.post(_REFRESH_URL).mock(return_value=httpx.Response(200, json=refresh_response))
        with patch.object(manager, "_save"):
            token = await manager.get_valid_token()
    assert token == "refreshed-token"


def test_token_data_is_expired_when_within_60s() -> None:
    token = TokenData("t", "r", time.time() + 30, "u")
    assert token.is_expired() is True


def test_token_data_not_expired_when_beyond_60s() -> None:
    token = TokenData("t", "r", time.time() + 120, "u")
    assert token.is_expired() is False


def test_save_and_load_tokens(manager: OAuthManager, tmp_path: Path) -> None:
    tokens = TokenData("tok", "ref", time.time() + 3600, "user-1")
    store = tmp_path / "tokens.json"
    store.write_text(json.dumps({"access_token": "tok", "refresh_token": "ref",
                                 "expires_at": tokens.expires_at, "user_id": "user-1"}))
    with patch("figma_cost_mcp.oauth._TOKEN_STORE_PATH", store):
        loaded = manager.load_tokens()
    assert loaded is not None
    assert loaded.access_token == "tok"
