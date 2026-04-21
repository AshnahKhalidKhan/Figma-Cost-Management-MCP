import httpx
import pytest
import respx

from figma_cost_mcp.http_client import FIGMA_API_BASE, RateLimitedClient
from figma_cost_mcp.tools import files

_FILE_KEY = "abc123"

_FILE_RESPONSE = {
    "name": "My Design",
    "lastModified": "2024-01-15T10:00:00Z",
    "thumbnailUrl": "https://figma.com/thumb/abc.png",
    "version": "v42",
    "role": "editor",
    "editorType": "figma",
    "linkAccess": "view",
    "schemaVersion": 0,
    "document": {
        "id": "0:0",
        "name": "Document",
        "type": "DOCUMENT",
        "children": [
            {"id": "0:1", "name": "Page 1", "type": "CANVAS"},
            {"id": "0:2", "name": "Page 2", "type": "CANVAS"},
        ],
    },
}

_VERSIONS_RESPONSE = {
    "versions": [
        {
            "id": "ver-1",
            "created_at": "2024-01-10T09:00:00Z",
            "label": "v1.0 Release",
            "description": "Initial release",
            "user": {"id": "u1", "handle": "alice", "img_url": ""},
        },
        {
            "id": "ver-2",
            "created_at": "2024-01-14T15:00:00Z",
            "label": None,
            "description": None,
            "user": {"id": "u2", "handle": "bob", "img_url": ""},
        },
    ]
}

_IMAGES_RESPONSE = {
    "images": {"1:2": "https://figma.com/img/node.png"},
    "err": None,
}

_IMAGE_FILLS_RESPONSE = {
    "meta": {"images": {"hash123": "https://figma.com/fills/image.png"}}
}

_NODES_RESPONSE = {
    "name": "My Design",
    "nodes": {
        "1:2": {"document": {"id": "1:2", "name": "Frame 1", "type": "FRAME"}}
    },
}


@pytest.fixture(autouse=True)
def inject_mock_client() -> None:
    files._set_client(RateLimitedClient(FIGMA_API_BASE, "test-token"))
    yield
    files._set_client(None)


@pytest.mark.asyncio
async def test_get_file_returns_name_and_pages() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/files/{_FILE_KEY}").mock(
            return_value=httpx.Response(200, json=_FILE_RESPONSE)
        )
        result = await files.get_file(_FILE_KEY)
    assert result["name"] == "My Design"
    assert len(result["pages"]) == 2
    assert result["pages"][0]["name"] == "Page 1"


@pytest.mark.asyncio
async def test_get_file_metadata_fields() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/files/{_FILE_KEY}").mock(
            return_value=httpx.Response(200, json=_FILE_RESPONSE)
        )
        result = await files.get_file(_FILE_KEY)
    assert result["last_modified"] == "2024-01-15T10:00:00Z"
    assert result["version"] == "v42"
    assert result["role"] == "editor"
    assert result["editor_type"] == "figma"


@pytest.mark.asyncio
async def test_get_file_versions_returns_all() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/files/{_FILE_KEY}/versions").mock(
            return_value=httpx.Response(200, json=_VERSIONS_RESPONSE)
        )
        result = await files.get_file_versions(_FILE_KEY)
    assert result["total"] == 2
    assert result["versions"][0]["id"] == "ver-1"
    assert result["versions"][0]["label"] == "v1.0 Release"
    assert result["versions"][0]["created_by"] == "alice"


@pytest.mark.asyncio
async def test_get_file_versions_unlabeled_version() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/files/{_FILE_KEY}/versions").mock(
            return_value=httpx.Response(200, json=_VERSIONS_RESPONSE)
        )
        result = await files.get_file_versions(_FILE_KEY)
    assert result["versions"][1]["label"] is None


@pytest.mark.asyncio
async def test_export_file_images_returns_urls() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/images/{_FILE_KEY}").mock(
            return_value=httpx.Response(200, json=_IMAGES_RESPONSE)
        )
        result = await files.export_file_images(_FILE_KEY, ids="1:2")
    assert "1:2" in result["images"]
    assert result["format"] == "png"


@pytest.mark.asyncio
async def test_get_file_image_fills_returns_map() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/files/{_FILE_KEY}/images").mock(
            return_value=httpx.Response(200, json=_IMAGE_FILLS_RESPONSE)
        )
        result = await files.get_file_image_fills(_FILE_KEY)
    assert "hash123" in result["images"]


@pytest.mark.asyncio
async def test_get_file_nodes_returns_node_data() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/files/{_FILE_KEY}/nodes").mock(
            return_value=httpx.Response(200, json=_NODES_RESPONSE)
        )
        result = await files.get_file_nodes(_FILE_KEY, ids="1:2")
    assert "1:2" in result["nodes"]
    assert result["name"] == "My Design"
