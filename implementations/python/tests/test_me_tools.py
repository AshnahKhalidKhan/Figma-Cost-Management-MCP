import httpx
import pytest
import respx

from figma_cost_mcp.http_client import FIGMA_API_BASE, RateLimitedClient
from figma_cost_mcp.tools import me

_USER_RESPONSE = {
    "id": "user-123",
    "email": "alice@example.com",
    "handle": "alice",
    "img_url": "https://figma.com/img/alice.png",
}


@pytest.fixture(autouse=True)
def inject_mock_client() -> None:
    me._set_client(RateLimitedClient(FIGMA_API_BASE, "test-token"))
    yield
    me._set_client(None)


@pytest.mark.asyncio
async def test_get_current_user_returns_user_data() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/me").mock(
            return_value=httpx.Response(200, json=_USER_RESPONSE)
        )
        result = await me.get_current_user()
    assert result["id"] == "user-123"
    assert result["handle"] == "alice"
    assert result["email"] == "alice@example.com"


@pytest.mark.asyncio
async def test_get_current_user_calls_correct_endpoint() -> None:
    with respx.mock:
        route = respx.get(f"{FIGMA_API_BASE}/v1/me").mock(
            return_value=httpx.Response(200, json=_USER_RESPONSE)
        )
        await me.get_current_user()
    assert route.called
