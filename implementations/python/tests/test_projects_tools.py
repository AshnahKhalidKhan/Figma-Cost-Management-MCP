import httpx
import pytest
import respx

from figma_cost_mcp.http_client import FIGMA_API_BASE, RateLimitedClient
from figma_cost_mcp.tools import projects

_TEAM_ID = "team-123"
_PROJECT_ID = "proj-456"

_PROJECTS_RESPONSE = {
    "projects": [
        {"id": "proj-1", "name": "Brand"},
        {"id": "proj-2", "name": "Product"},
    ]
}

_FILES_RESPONSE = {
    "files": [
        {
            "key": "file-abc",
            "name": "Homepage",
            "last_modified": "2024-01-15T10:00:00Z",
            "thumbnail_url": "https://figma.com/thumb/abc.png",
        },
        {
            "key": "file-def",
            "name": "Components",
            "last_modified": "2024-01-14T08:00:00Z",
            "thumbnail_url": None,
        },
    ]
}


@pytest.fixture(autouse=True)
def inject_mock_client() -> None:
    projects._set_client(RateLimitedClient(FIGMA_API_BASE, "test-token"))
    yield
    projects._set_client(None)


@pytest.mark.asyncio
async def test_get_team_projects_returns_list() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/teams/{_TEAM_ID}/projects").mock(
            return_value=httpx.Response(200, json=_PROJECTS_RESPONSE)
        )
        result = await projects.get_team_projects(team_id=_TEAM_ID)
    assert result["total"] == 2
    assert result["team_id"] == _TEAM_ID
    assert result["projects"][0]["name"] == "Brand"


@pytest.mark.asyncio
async def test_get_team_projects_ids_present() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/teams/{_TEAM_ID}/projects").mock(
            return_value=httpx.Response(200, json=_PROJECTS_RESPONSE)
        )
        result = await projects.get_team_projects(team_id=_TEAM_ID)
    ids = {p["id"] for p in result["projects"]}
    assert ids == {"proj-1", "proj-2"}


@pytest.mark.asyncio
async def test_get_project_files_returns_files() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/projects/{_PROJECT_ID}/files").mock(
            return_value=httpx.Response(200, json=_FILES_RESPONSE)
        )
        result = await projects.get_project_files(_PROJECT_ID)
    assert result["total"] == 2
    assert result["files"][0]["key"] == "file-abc"
    assert result["files"][0]["name"] == "Homepage"


@pytest.mark.asyncio
async def test_get_project_files_includes_last_modified() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/projects/{_PROJECT_ID}/files").mock(
            return_value=httpx.Response(200, json=_FILES_RESPONSE)
        )
        result = await projects.get_project_files(_PROJECT_ID)
    assert result["files"][0]["last_modified"] == "2024-01-15T10:00:00Z"


@pytest.mark.asyncio
async def test_get_team_projects_missing_team_id_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FIGMA_TEAM_ID", raising=False)
    with pytest.raises(ValueError, match="team_id is required"):
        await projects.get_team_projects(team_id=None)


@pytest.mark.asyncio
async def test_get_team_projects_uses_env_team_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIGMA_TEAM_ID", _TEAM_ID)
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/teams/{_TEAM_ID}/projects").mock(
            return_value=httpx.Response(200, json=_PROJECTS_RESPONSE)
        )
        result = await projects.get_team_projects()
    assert result["team_id"] == _TEAM_ID
