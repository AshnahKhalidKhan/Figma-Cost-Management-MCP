import pytest
import httpx
import respx

from figma_cost_mcp.http_client import FIGMA_API_BASE, RateLimitedClient
from figma_cost_mcp.tools import payments

_PAYMENT_RESPONSE = {
    "user_id": "12345",
    "resource_id": "67890",
    "resource_type": "PLUGIN",
    "payment_status": {"status": "PAID"},
    "date_of_purchase": "2024-01-15T10:30:00Z",
}


@pytest.fixture(autouse=True)
def inject_mock_client() -> None:
    payments._set_client(RateLimitedClient(FIGMA_API_BASE, "test-token"))
    yield
    payments._set_client(None)


@pytest.mark.asyncio
async def test_validate_by_token_returns_payment_info() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/payments").mock(
            return_value=httpx.Response(200, json=_PAYMENT_RESPONSE)
        )
        result = await payments.validate_payment_by_token("short-lived-token")
    assert result["payment_status"]["status"] == "PAID"
    assert result["resource_type"] == "PLUGIN"


@pytest.mark.asyncio
async def test_validate_by_token_sends_correct_param() -> None:
    with respx.mock:
        route = respx.get(f"{FIGMA_API_BASE}/v1/payments").mock(
            return_value=httpx.Response(200, json=_PAYMENT_RESPONSE)
        )
        await payments.validate_payment_by_token("my-token")
    assert "plugin_payment_token=my-token" in str(route.calls[0].request.url)


@pytest.mark.asyncio
async def test_validate_by_user_plugin() -> None:
    with respx.mock:
        route = respx.get(f"{FIGMA_API_BASE}/v1/payments").mock(
            return_value=httpx.Response(200, json=_PAYMENT_RESPONSE)
        )
        result = await payments.validate_payment_by_user(12345, "PLUGIN", 67890)
    assert result["user_id"] == "12345"
    url = str(route.calls[0].request.url)
    assert "user_id=12345" in url
    assert "plugin_id=67890" in url


@pytest.mark.asyncio
async def test_validate_by_user_widget() -> None:
    response = {**_PAYMENT_RESPONSE, "resource_type": "WIDGET"}
    with respx.mock:
        route = respx.get(f"{FIGMA_API_BASE}/v1/payments").mock(
            return_value=httpx.Response(200, json=response)
        )
        await payments.validate_payment_by_user(1, "WIDGET", 2)
    assert "widget_id=2" in str(route.calls[0].request.url)


@pytest.mark.asyncio
async def test_validate_by_user_community_file() -> None:
    response = {**_PAYMENT_RESPONSE, "resource_type": "COMMUNITY_FILE"}
    with respx.mock:
        route = respx.get(f"{FIGMA_API_BASE}/v1/payments").mock(
            return_value=httpx.Response(200, json=response)
        )
        await payments.validate_payment_by_user(1, "COMMUNITY_FILE", 3)
    assert "community_file_id=3" in str(route.calls[0].request.url)


@pytest.mark.asyncio
async def test_validate_by_user_invalid_resource_type_raises() -> None:
    with pytest.raises(ValueError, match="Invalid resource_type"):
        await payments.validate_payment_by_user(1, "INVALID", 2)


@pytest.mark.asyncio
async def test_validate_by_token_unpaid_status() -> None:
    unpaid = {**_PAYMENT_RESPONSE, "payment_status": {"status": "UNPAID"}, "date_of_purchase": None}
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/payments").mock(
            return_value=httpx.Response(200, json=unpaid)
        )
        result = await payments.validate_payment_by_token("token")
    assert result["payment_status"]["status"] == "UNPAID"
    assert result["date_of_purchase"] is None


@pytest.mark.asyncio
async def test_validate_by_token_trial_status() -> None:
    trial = {**_PAYMENT_RESPONSE, "payment_status": {"status": "TRIAL"}}
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/payments").mock(
            return_value=httpx.Response(200, json=trial)
        )
        result = await payments.validate_payment_by_token("token")
    assert result["payment_status"]["status"] == "TRIAL"
