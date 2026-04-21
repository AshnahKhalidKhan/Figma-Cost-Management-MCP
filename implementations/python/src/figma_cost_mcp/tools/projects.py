import logging
from typing import Annotated

from .._mcp import mcp
from ..config import Config
from ..http_client import RateLimitedClient, make_rest_client
from ..models.projects import TeamProjectsResponse, ProjectFilesResponse
from ..oauth import get_oauth_manager

logger = logging.getLogger(__name__)

_client: RateLimitedClient | None = None


def _get_client() -> RateLimitedClient:
    global _client
    if _client is None:
        config = Config.from_env()
        if config.figma_access_token:
            _client = make_rest_client(token=config.figma_access_token)
        else:
            _client = make_rest_client(token_provider=get_oauth_manager().get_valid_token)
    return _client


def _set_client(client: RateLimitedClient | None) -> None:
    global _client
    _client = client


def _resolve_team_id(team_id: str | None) -> str:
    if team_id:
        return team_id
    env_team_id = Config.from_env().figma_team_id
    if not env_team_id:
        raise ValueError(
            "team_id is required. Set FIGMA_TEAM_ID in your environment, or pass it as a parameter. "
            "Find your team ID in the Figma URL: figma.com/files/team/{TEAM_ID}"
        )
    return env_team_id


@mcp.tool()
async def get_team_projects(
    team_id: Annotated[
        str | None,
        "Figma team ID. Defaults to FIGMA_TEAM_ID env var.",
    ] = None,
) -> dict:
    """List all projects in a Figma team.

    Returns each project's ID and name. Use project IDs with get_project_files
    to enumerate all design files within a project.

    Projects are the folders that organize files within a team. This gives you
    a full map of your team's organizational structure.
    """
    tid = _resolve_team_id(team_id)
    data = await _get_client().get(f"/v1/teams/{tid}/projects")
    response = TeamProjectsResponse.model_validate(data)
    return {
        "team_id": tid,
        "projects": [{"id": p.id, "name": p.name} for p in response.projects],
        "total": len(response.projects),
    }


@mcp.tool()
async def get_project_files(
    project_id: Annotated[str, "Figma project ID (from get_team_projects)"],
) -> dict:
    """List all files in a Figma project.

    Returns each file's key, name, last modified timestamp, and thumbnail URL.
    The file key is used in all other file-related tools.

    Use this to enumerate every design file inside a specific project,
    or to find recently modified files within a project.
    """
    data = await _get_client().get(f"/v1/projects/{project_id}/files")
    response = ProjectFilesResponse.model_validate(data)
    return {
        "project_id": project_id,
        "files": [
            {
                "key": f.key,
                "name": f.name,
                "last_modified": f.last_modified,
                "thumbnail_url": f.thumbnail_url,
            }
            for f in response.files
        ],
        "total": len(response.files),
    }
