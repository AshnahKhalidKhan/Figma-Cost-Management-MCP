import httpx
import pytest
import respx

from figma_cost_mcp.http_client import FIGMA_API_BASE, RateLimitedClient
from figma_cost_mcp.tools import dev_resources

_FILE_KEY = "file-abc"
_NODE_ID = "1:2"
_DEV_RESOURCE_ID = "dr-999"

_DEV_RESOURCE = {
    "id": _DEV_RESOURCE_ID,
    "name": "GitHub PR #42",
    "url": "https://github.com/org/repo/pull/42",
    "file_key": _FILE_KEY,
    "node_id": _NODE_ID,
    "created_at": "2024-01-15T10:00:00Z",
    "updated_at": "2024-01-15T10:00:00Z",
}

_GET_RESPONSE = {"dev_resources": [_DEV_RESOURCE], "errors": []}

_CREATE_RESPONSE = {"dev_resources_created": [_DEV_RESOURCE], "errors": []}

_UPDATE_RESPONSE = {
    "dev_resources_updated": [
        {**_DEV_RESOURCE, "name": "GitHub PR #43", "url": "https://github.com/org/repo/pull/43"}
    ],
    "errors": [],
}


@pytest.fixture(autouse=True)
def inject_mock_client() -> None:
    dev_resources._set_client(RateLimitedClient(FIGMA_API_BASE, "test-token"))
    yield
    dev_resources._set_client(None)


@pytest.mark.asyncio
async def test_get_dev_resources_returns_list() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/files/{_FILE_KEY}/dev_resources").mock(
            return_value=httpx.Response(200, json=_GET_RESPONSE)
        )
        result = await dev_resources.get_dev_resources(_FILE_KEY)
    assert result["total"] == 1
    assert result["dev_resources"][0]["name"] == "GitHub PR #42"
    assert result["dev_resources"][0]["url"] == "https://github.com/org/repo/pull/42"


@pytest.mark.asyncio
async def test_get_dev_resources_file_key_in_result() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/files/{_FILE_KEY}/dev_resources").mock(
            return_value=httpx.Response(200, json=_GET_RESPONSE)
        )
        result = await dev_resources.get_dev_resources(_FILE_KEY)
    assert result["file_key"] == _FILE_KEY


@pytest.mark.asyncio
async def test_create_dev_resource_posts_body() -> None:
    with respx.mock:
        route = respx.post(f"{FIGMA_API_BASE}/v1/dev_resources").mock(
            return_value=httpx.Response(200, json=_CREATE_RESPONSE)
        )
        result = await dev_resources.create_dev_resource(
            name="GitHub PR #42",
            url="https://github.com/org/repo/pull/42",
            file_key=_FILE_KEY,
            node_id=_NODE_ID,
        )
    assert result["created"]["id"] == _DEV_RESOURCE_ID
    assert route.called


@pytest.mark.asyncio
async def test_create_dev_resource_returns_id() -> None:
    with respx.mock:
        respx.post(f"{FIGMA_API_BASE}/v1/dev_resources").mock(
            return_value=httpx.Response(200, json=_CREATE_RESPONSE)
        )
        result = await dev_resources.create_dev_resource(
            name="GitHub PR #42",
            url="https://github.com/org/repo/pull/42",
            file_key=_FILE_KEY,
            node_id=_NODE_ID,
        )
    assert result["created"]["node_id"] == _NODE_ID


@pytest.mark.asyncio
async def test_update_dev_resource_sends_put() -> None:
    with respx.mock:
        route = respx.put(f"{FIGMA_API_BASE}/v1/dev_resources").mock(
            return_value=httpx.Response(200, json=_UPDATE_RESPONSE)
        )
        result = await dev_resources.update_dev_resource(
            _DEV_RESOURCE_ID,
            name="GitHub PR #43",
            url="https://github.com/org/repo/pull/43",
        )
    assert result["updated"]["name"] == "GitHub PR #43"
    assert route.called


@pytest.mark.asyncio
async def test_update_dev_resource_no_fields_raises() -> None:
    with pytest.raises(ValueError, match="At least one of name or url"):
        await dev_resources.update_dev_resource(_DEV_RESOURCE_ID)


@pytest.mark.asyncio
async def test_delete_dev_resource_returns_confirmation() -> None:
    with respx.mock:
        respx.delete(
            f"{FIGMA_API_BASE}/v1/files/{_FILE_KEY}/dev_resources/{_DEV_RESOURCE_ID}"
        ).mock(return_value=httpx.Response(204))
        result = await dev_resources.delete_dev_resource(_FILE_KEY, _DEV_RESOURCE_ID)
    assert result["deleted"] is True
    assert result["dev_resource_id"] == _DEV_RESOURCE_ID
