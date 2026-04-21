import httpx
import pytest
import respx

from figma_cost_mcp.http_client import FIGMA_API_BASE, RateLimitedClient
from figma_cost_mcp.tools import components

_TEAM_ID = "team-123"
_FILE_KEY = "file-abc"
_COMPONENT_KEY = "comp-xyz"
_STYLE_KEY = "style-uvw"

_COMPONENTS_RESPONSE = {
    "meta": {
        "components": [
            {
                "key": "comp-1",
                "file_key": _FILE_KEY,
                "node_id": "1:2",
                "name": "Button/Primary",
                "description": "Primary button",
                "thumbnail_url": "https://figma.com/t/c1.png",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-10T00:00:00Z",
            }
        ],
        "cursor": None,
    }
}

_STYLES_RESPONSE = {
    "meta": {
        "styles": [
            {
                "key": "style-1",
                "file_key": _FILE_KEY,
                "node_id": "2:3",
                "name": "Colors/Primary",
                "description": "Brand primary",
                "style_type": "FILL",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-10T00:00:00Z",
            }
        ],
        "cursor": None,
    }
}

_SINGLE_COMPONENT_RESPONSE = {
    "meta": {
        "key": _COMPONENT_KEY,
        "file_key": _FILE_KEY,
        "node_id": "3:4",
        "name": "Icon/Arrow",
        "description": "Arrow icon",
        "thumbnail_url": "https://figma.com/t/c2.png",
        "created_at": "2024-01-05T00:00:00Z",
        "updated_at": "2024-01-12T00:00:00Z",
    }
}

_SINGLE_STYLE_RESPONSE = {
    "meta": {
        "key": _STYLE_KEY,
        "file_key": _FILE_KEY,
        "node_id": "4:5",
        "name": "Typography/H1",
        "description": "Heading 1",
        "style_type": "TEXT",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-10T00:00:00Z",
    }
}


@pytest.fixture(autouse=True)
def inject_mock_client() -> None:
    components._set_client(RateLimitedClient(FIGMA_API_BASE, "test-token"))
    yield
    components._set_client(None)


@pytest.mark.asyncio
async def test_get_team_components_returns_list() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/teams/{_TEAM_ID}/components").mock(
            return_value=httpx.Response(200, json=_COMPONENTS_RESPONSE)
        )
        result = await components.get_team_components(team_id=_TEAM_ID)
    assert result["total"] == 1
    assert result["components"][0]["name"] == "Button/Primary"
    assert result["components"][0]["key"] == "comp-1"


@pytest.mark.asyncio
async def test_get_team_styles_returns_list() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/teams/{_TEAM_ID}/styles").mock(
            return_value=httpx.Response(200, json=_STYLES_RESPONSE)
        )
        result = await components.get_team_styles(team_id=_TEAM_ID)
    assert result["total"] == 1
    assert result["styles"][0]["name"] == "Colors/Primary"
    assert result["styles"][0]["style_type"] == "FILL"


@pytest.mark.asyncio
async def test_get_file_components_returns_list() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/files/{_FILE_KEY}/components").mock(
            return_value=httpx.Response(200, json=_COMPONENTS_RESPONSE)
        )
        result = await components.get_file_components(_FILE_KEY)
    assert result["file_key"] == _FILE_KEY
    assert result["total"] == 1


@pytest.mark.asyncio
async def test_get_file_styles_returns_list() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/files/{_FILE_KEY}/styles").mock(
            return_value=httpx.Response(200, json=_STYLES_RESPONSE)
        )
        result = await components.get_file_styles(_FILE_KEY)
    assert result["file_key"] == _FILE_KEY
    assert result["total"] == 1


@pytest.mark.asyncio
async def test_get_component_returns_details() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/components/{_COMPONENT_KEY}").mock(
            return_value=httpx.Response(200, json=_SINGLE_COMPONENT_RESPONSE)
        )
        result = await components.get_component(_COMPONENT_KEY)
    assert result["key"] == _COMPONENT_KEY
    assert result["name"] == "Icon/Arrow"


@pytest.mark.asyncio
async def test_get_style_returns_details() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/styles/{_STYLE_KEY}").mock(
            return_value=httpx.Response(200, json=_SINGLE_STYLE_RESPONSE)
        )
        result = await components.get_style(_STYLE_KEY)
    assert result["key"] == _STYLE_KEY
    assert result["style_type"] == "TEXT"


@pytest.mark.asyncio
async def test_get_team_components_missing_team_id_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FIGMA_TEAM_ID", raising=False)
    with pytest.raises(ValueError, match="team_id is required"):
        await components.get_team_components(team_id=None)
