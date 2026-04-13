import pytest
import httpx
import respx

from figma_cost_mcp.http_client import FIGMA_API_BASE, RateLimitedClient
from figma_cost_mcp.models.activity_logs import BILLING_ACTION_TYPES, USER_MGMT_ACTION_TYPES
from figma_cost_mcp.tools import activity_logs

_ACTIVITY_RESPONSE = {
    "activity_logs": [
        {
            "id": "log-001",
            "timestamp": "2024-01-15T10:00:00Z",
            "action_type": "org_user_account_type_change",
            "actor": {"user_id": "user-123"},
            "details": {"old_seat": "View", "new_seat": "Full"},
        }
    ],
    "cursor": None,
}


@pytest.fixture(autouse=True)
def inject_mock_client() -> None:
    activity_logs._set_client(RateLimitedClient(FIGMA_API_BASE, "test-token"), "org-999")
    yield
    activity_logs._set_client(None, None)


@pytest.mark.asyncio
async def test_get_billing_logs_returns_response() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/activity_logs").mock(
            return_value=httpx.Response(200, json=_ACTIVITY_RESPONSE)
        )
        result = await activity_logs.get_billing_activity_logs()
    assert "activity_logs" in result
    assert len(result["activity_logs"]) == 1


@pytest.mark.asyncio
async def test_get_billing_logs_includes_org_id() -> None:
    with respx.mock:
        route = respx.get(f"{FIGMA_API_BASE}/v1/activity_logs").mock(
            return_value=httpx.Response(200, json=_ACTIVITY_RESPONSE)
        )
        await activity_logs.get_billing_activity_logs()
    assert "org_id=org-999" in str(route.calls[0].request.url)


@pytest.mark.asyncio
async def test_get_billing_logs_with_time_range() -> None:
    with respx.mock:
        route = respx.get(f"{FIGMA_API_BASE}/v1/activity_logs").mock(
            return_value=httpx.Response(200, json=_ACTIVITY_RESPONSE)
        )
        await activity_logs.get_billing_activity_logs(
            start_time="2024-01-01T00:00:00Z",
            end_time="2024-12-31T23:59:59Z",
        )
    url = str(route.calls[0].request.url)
    assert "start_time" in url
    assert "end_time" in url


@pytest.mark.asyncio
async def test_get_billing_logs_with_cursor() -> None:
    with respx.mock:
        route = respx.get(f"{FIGMA_API_BASE}/v1/activity_logs").mock(
            return_value=httpx.Response(200, json={**_ACTIVITY_RESPONSE, "cursor": "next-page"})
        )
        result = await activity_logs.get_billing_activity_logs(cursor="current-cursor")
    assert "cursor=current-cursor" in str(route.calls[0].request.url)


@pytest.mark.asyncio
async def test_get_user_management_logs_returns_response() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/activity_logs").mock(
            return_value=httpx.Response(200, json=_ACTIVITY_RESPONSE)
        )
        result = await activity_logs.get_user_management_activity_logs()
    assert "activity_logs" in result


@pytest.mark.asyncio
async def test_get_all_logs_uses_combined_event_types() -> None:
    with respx.mock:
        route = respx.get(f"{FIGMA_API_BASE}/v1/activity_logs").mock(
            return_value=httpx.Response(200, json=_ACTIVITY_RESPONSE)
        )
        await activity_logs.get_activity_logs()
    url = str(route.calls[0].request.url)
    # Should include at least one billing and one user management event type
    assert any(t in url for t in BILLING_ACTION_TYPES)
    assert any(t in url for t in USER_MGMT_ACTION_TYPES)


@pytest.mark.asyncio
async def test_get_logs_with_custom_event_types() -> None:
    with respx.mock:
        route = respx.get(f"{FIGMA_API_BASE}/v1/activity_logs").mock(
            return_value=httpx.Response(200, json=_ACTIVITY_RESPONSE)
        )
        await activity_logs.get_activity_logs(event_types=["seats_renew"])
    assert "seats_renew" in str(route.calls[0].request.url)


@pytest.mark.asyncio
async def test_billing_action_types_are_defined() -> None:
    assert "org_user_account_type_change" in BILLING_ACTION_TYPES
    assert "seats_renew" in BILLING_ACTION_TYPES
    assert "workspace_member_add" in BILLING_ACTION_TYPES


@pytest.mark.asyncio
async def test_user_mgmt_action_types_are_defined() -> None:
    assert "org_user_create" in USER_MGMT_ACTION_TYPES
    assert "org_user_delete" in USER_MGMT_ACTION_TYPES
    assert "idp_user_create" in USER_MGMT_ACTION_TYPES
