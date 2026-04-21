import httpx
import pytest
import respx

from figma_cost_mcp.http_client import FIGMA_API_BASE, RateLimitedClient
from figma_cost_mcp.tools import analytics

_FILE_KEY = "lib-abc"

_ACTIONS_RESPONSE = {
    "rows": [
        {
            "component_key": "comp-1",
            "component_name": "Button/Primary",
            "insertions": 42,
            "detachments": 3,
        }
    ],
    "next_cursor": None,
}

_USAGES_RESPONSE = {
    "rows": [
        {
            "component_key": "comp-1",
            "component_name": "Button/Primary",
            "usages": 150,
        }
    ],
    "next_cursor": "cur-xyz",
}


@pytest.fixture(autouse=True)
def inject_mock_client() -> None:
    analytics._set_client(RateLimitedClient(FIGMA_API_BASE, "test-token"))
    yield
    analytics._set_client(None)


@pytest.mark.asyncio
async def test_get_library_analytics_actions_returns_rows() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/analytics/libraries/{_FILE_KEY}/actions").mock(
            return_value=httpx.Response(200, json=_ACTIONS_RESPONSE)
        )
        result = await analytics.get_library_analytics_actions(_FILE_KEY)
    assert result["file_key"] == _FILE_KEY
    assert len(result["actions"]) == 1
    assert result["actions"][0]["component_name"] == "Button/Primary"


@pytest.mark.asyncio
async def test_get_library_analytics_actions_with_group_by() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/analytics/libraries/{_FILE_KEY}/actions").mock(
            return_value=httpx.Response(200, json=_ACTIONS_RESPONSE)
        )
        result = await analytics.get_library_analytics_actions(_FILE_KEY, group_by="component")
    assert result["group_by"] == "component"


@pytest.mark.asyncio
async def test_get_library_analytics_actions_invalid_group_by_raises() -> None:
    with pytest.raises(ValueError, match="group_by must be one of"):
        await analytics.get_library_analytics_actions(_FILE_KEY, group_by="invalid")


@pytest.mark.asyncio
async def test_get_library_analytics_usages_returns_rows() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/analytics/libraries/{_FILE_KEY}/usages").mock(
            return_value=httpx.Response(200, json=_USAGES_RESPONSE)
        )
        result = await analytics.get_library_analytics_usages(_FILE_KEY)
    assert result["file_key"] == _FILE_KEY
    assert len(result["usages"]) == 1
    assert result["usages"][0]["usages"] == 150


@pytest.mark.asyncio
async def test_get_library_analytics_usages_returns_cursor() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/analytics/libraries/{_FILE_KEY}/usages").mock(
            return_value=httpx.Response(200, json=_USAGES_RESPONSE)
        )
        result = await analytics.get_library_analytics_usages(_FILE_KEY)
    assert result["cursor"] == "cur-xyz"


@pytest.mark.asyncio
async def test_get_library_analytics_usages_invalid_group_by_raises() -> None:
    with pytest.raises(ValueError, match="group_by must be one of"):
        await analytics.get_library_analytics_usages(_FILE_KEY, group_by="unknown")
