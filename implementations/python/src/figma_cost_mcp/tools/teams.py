import logging
from typing import Annotated

from .._mcp import mcp
from ..config import Config
from ..http_client import RateLimitedClient, make_rest_client
from ..models.teams import EDITOR_ROLES, TeamMembersResponse
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
async def list_team_members(
    team_id: Annotated[
        str | None,
        "Figma team ID. Defaults to FIGMA_TEAM_ID env var. "
        "Find it in the Figma URL: figma.com/files/team/{TEAM_ID}",
    ] = None,
) -> dict:
    """List all members of a Figma team with their roles and billing seat status.

    On Figma Pro, owner/admin/editor roles consume paid seats; viewer roles are free.
    Use this to audit who holds paid editor seats on your team.

    Returns each member's handle, email, role, and whether they occupy a billed seat.
    """
    tid = _resolve_team_id(team_id)
    data = await _get_client().get(f"/v1/teams/{tid}/members")
    response = TeamMembersResponse.model_validate(data)
    members_out = [
        {
            "user_id": m.user.id,
            "handle": m.user.handle,
            "email": m.user.email,
            "role": m.role,
            "billed_seat": m.role in EDITOR_ROLES,
        }
        for m in response.members
    ]
    return {
        "team_id": tid,
        "members": members_out,
        "total_members": len(members_out),
        "billed_seats": sum(1 for m in members_out if m["billed_seat"]),
        "free_seats": sum(1 for m in members_out if not m["billed_seat"]),
    }


@mcp.tool()
async def get_team_billing_summary(
    team_id: Annotated[
        str | None,
        "Figma team ID. Defaults to FIGMA_TEAM_ID env var. "
        "Find it in the Figma URL: figma.com/files/team/{TEAM_ID}",
    ] = None,
) -> dict:
    """Summarize paid editor seats vs free viewer seats for a Figma team.

    On Figma Pro: owner, admin, and editor roles are billed; viewer roles are free.
    Returns role-by-role breakdown and lists of who is in each tier — useful for
    identifying viewers to downgrade or editors to review for seat reclamation.
    """
    tid = _resolve_team_id(team_id)
    data = await _get_client().get(f"/v1/teams/{tid}/members")
    response = TeamMembersResponse.model_validate(data)

    editors: list[dict] = []
    viewers: list[dict] = []
    role_counts: dict[str, int] = {}

    for m in response.members:
        role_counts[m.role] = role_counts.get(m.role, 0) + 1
        entry = {
            "user_id": m.user.id,
            "handle": m.user.handle,
            "email": m.user.email,
            "role": m.role,
        }
        if m.role in EDITOR_ROLES:
            editors.append(entry)
        else:
            viewers.append(entry)

    return {
        "team_id": tid,
        "billed_editor_seats": len(editors),
        "free_viewer_seats": len(viewers),
        "total_members": len(response.members),
        "role_breakdown": role_counts,
        "editors": editors,
        "viewers": viewers,
    }
