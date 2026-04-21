import httpx
import pytest
import respx

from figma_cost_mcp.http_client import FIGMA_API_BASE, RateLimitedClient
from figma_cost_mcp.tools import variables

_FILE_KEY = "file-abc"

_LOCAL_VARS_RESPONSE = {
    "meta": {
        "variableCollections": {
            "VariableCollectionId:1:1": {
                "id": "VariableCollectionId:1:1",
                "name": "Brand Tokens",
                "modes": [{"modeId": "1:0", "name": "Light"}, {"modeId": "1:1", "name": "Dark"}],
            }
        },
        "variables": {
            "VariableID:1:2": {
                "id": "VariableID:1:2",
                "name": "color/primary",
                "resolvedType": "COLOR",
                "variableCollectionId": "VariableCollectionId:1:1",
                "valuesByMode": {
                    "1:0": {"r": 0.0, "g": 0.47, "b": 1.0, "a": 1.0},
                    "1:1": {"r": 0.0, "g": 0.35, "b": 0.8, "a": 1.0},
                },
            }
        },
    }
}

_PUBLISHED_VARS_RESPONSE = {
    "meta": {
        "variableCollections": {
            "VariableCollectionId:2:1": {
                "id": "VariableCollectionId:2:1",
                "name": "Shared Tokens",
                "modes": [{"modeId": "2:0", "name": "Default"}],
            }
        },
        "variables": {
            "VariableID:2:3": {
                "id": "VariableID:2:3",
                "name": "spacing/md",
                "resolvedType": "FLOAT",
                "variableCollectionId": "VariableCollectionId:2:1",
                "valuesByMode": {"2:0": 16},
            }
        },
    }
}


@pytest.fixture(autouse=True)
def inject_mock_client() -> None:
    variables._set_client(RateLimitedClient(FIGMA_API_BASE, "test-token"))
    yield
    variables._set_client(None)


@pytest.mark.asyncio
async def test_get_local_variables_returns_collections_and_vars() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/files/{_FILE_KEY}/variables/local").mock(
            return_value=httpx.Response(200, json=_LOCAL_VARS_RESPONSE)
        )
        result = await variables.get_local_variables(_FILE_KEY)
    assert result["file_key"] == _FILE_KEY
    assert "VariableCollectionId:1:1" in result["variable_collections"]
    assert "VariableID:1:2" in result["variables"]


@pytest.mark.asyncio
async def test_get_local_variables_has_modes() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/files/{_FILE_KEY}/variables/local").mock(
            return_value=httpx.Response(200, json=_LOCAL_VARS_RESPONSE)
        )
        result = await variables.get_local_variables(_FILE_KEY)
    collection = result["variable_collections"]["VariableCollectionId:1:1"]
    mode_names = [m["name"] for m in collection["modes"]]
    assert "Light" in mode_names
    assert "Dark" in mode_names


@pytest.mark.asyncio
async def test_get_published_variables_returns_data() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/files/{_FILE_KEY}/variables/published").mock(
            return_value=httpx.Response(200, json=_PUBLISHED_VARS_RESPONSE)
        )
        result = await variables.get_published_variables(_FILE_KEY)
    assert result["file_key"] == _FILE_KEY
    assert "VariableCollectionId:2:1" in result["variable_collections"]
    assert "VariableID:2:3" in result["variables"]
