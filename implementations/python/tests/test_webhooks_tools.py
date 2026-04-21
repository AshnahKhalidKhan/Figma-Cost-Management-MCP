import httpx
import pytest
import respx

from figma_cost_mcp.http_client import FIGMA_API_BASE, RateLimitedClient
from figma_cost_mcp.tools import webhooks

_TEAM_ID = "team-123"
_WEBHOOK_ID = "wh-456"

_WEBHOOK = {
    "id": _WEBHOOK_ID,
    "team_id": _TEAM_ID,
    "event_type": "FILE_UPDATE",
    "endpoint": "https://example.com/hook",
    "status": "ACTIVE",
    "description": "Notify on file updates",
    "client_id": None,
}

_TEAM_WEBHOOKS_RESPONSE = {"webhooks": [_WEBHOOK]}

_REQUESTS_RESPONSE = {
    "requests": [
        {
            "id": "req-1",
            "webhook_id": _WEBHOOK_ID,
            "created_at": "2024-01-15T10:00:00Z",
            "sent_at": "2024-01-15T10:00:01Z",
            "response_status": 200,
            "error": None,
            "error_reason": None,
        }
    ]
}


@pytest.fixture(autouse=True)
def inject_mock_client() -> None:
    webhooks._set_client(RateLimitedClient(FIGMA_API_BASE, "test-token"))
    yield
    webhooks._set_client(None)


@pytest.mark.asyncio
async def test_list_team_webhooks_returns_all() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v2/teams/{_TEAM_ID}/webhooks").mock(
            return_value=httpx.Response(200, json=_TEAM_WEBHOOKS_RESPONSE)
        )
        result = await webhooks.list_team_webhooks(team_id=_TEAM_ID)
    assert result["total"] == 1
    assert result["webhooks"][0]["event_type"] == "FILE_UPDATE"


@pytest.mark.asyncio
async def test_get_webhook_returns_details() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v2/webhooks/{_WEBHOOK_ID}").mock(
            return_value=httpx.Response(200, json=_WEBHOOK)
        )
        result = await webhooks.get_webhook(_WEBHOOK_ID)
    assert result["id"] == _WEBHOOK_ID
    assert result["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_create_webhook_posts_body() -> None:
    with respx.mock:
        route = respx.post(f"{FIGMA_API_BASE}/v2/webhooks").mock(
            return_value=httpx.Response(200, json=_WEBHOOK)
        )
        result = await webhooks.create_webhook(
            event_type="FILE_UPDATE",
            endpoint="https://example.com/hook",
            passcode="secret123",
            team_id=_TEAM_ID,
            description="Notify on file updates",
        )
    assert result["event_type"] == "FILE_UPDATE"
    assert route.called


@pytest.mark.asyncio
async def test_create_webhook_invalid_event_raises() -> None:
    with pytest.raises(ValueError, match="Invalid event_type"):
        await webhooks.create_webhook(
            event_type="INVALID_EVENT",
            endpoint="https://example.com/hook",
            passcode="secret",
            team_id=_TEAM_ID,
        )


@pytest.mark.asyncio
async def test_create_webhook_case_insensitive() -> None:
    with respx.mock:
        respx.post(f"{FIGMA_API_BASE}/v2/webhooks").mock(
            return_value=httpx.Response(200, json=_WEBHOOK)
        )
        result = await webhooks.create_webhook(
            event_type="file_update",
            endpoint="https://example.com/hook",
            passcode="secret",
            team_id=_TEAM_ID,
        )
    assert result["event_type"] == "FILE_UPDATE"


@pytest.mark.asyncio
async def test_update_webhook_sends_put() -> None:
    updated = {**_WEBHOOK, "status": "PAUSED"}
    with respx.mock:
        respx.put(f"{FIGMA_API_BASE}/v2/webhooks/{_WEBHOOK_ID}").mock(
            return_value=httpx.Response(200, json=updated)
        )
        result = await webhooks.update_webhook(_WEBHOOK_ID, status="PAUSED")
    assert result["status"] == "PAUSED"


@pytest.mark.asyncio
async def test_update_webhook_no_fields_raises() -> None:
    with pytest.raises(ValueError, match="At least one field"):
        await webhooks.update_webhook(_WEBHOOK_ID)


@pytest.mark.asyncio
async def test_delete_webhook_returns_confirmation() -> None:
    with respx.mock:
        respx.delete(f"{FIGMA_API_BASE}/v2/webhooks/{_WEBHOOK_ID}").mock(
            return_value=httpx.Response(204)
        )
        result = await webhooks.delete_webhook(_WEBHOOK_ID)
    assert result["deleted"] is True
    assert result["webhook_id"] == _WEBHOOK_ID


@pytest.mark.asyncio
async def test_get_webhook_requests_returns_history() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v2/webhooks/{_WEBHOOK_ID}/requests").mock(
            return_value=httpx.Response(200, json=_REQUESTS_RESPONSE)
        )
        result = await webhooks.get_webhook_requests(_WEBHOOK_ID)
    assert result["total"] == 1
    assert result["requests"][0]["response_status"] == 200
