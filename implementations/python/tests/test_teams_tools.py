import pytest
import httpx
import respx

from figma_cost_mcp.http_client import FIGMA_API_BASE, RateLimitedClient
from figma_cost_mcp.tools import teams

_TEAM_ID = "team-123"

_MEMBERS_RESPONSE = {
    "members": [
        {"user": {"id": "u1", "handle": "alice", "email": "alice@co.com", "img_url": ""}, "role": "owner"},
        {"user": {"id": "u2", "handle": "bob", "email": "bob@co.com", "img_url": ""}, "role": "editor"},
        {"user": {"id": "u3", "handle": "carol", "email": "carol@co.com", "img_url": ""}, "role": "viewer"},
        {"user": {"id": "u4", "handle": "dave", "email": "dave@co.com", "img_url": ""}, "role": "viewer_restricted"},
    ]
}


@pytest.fixture(autouse=True)
def inject_mock_client() -> None:
    teams._set_client(RateLimitedClient(FIGMA_API_BASE, "test-token"))
    yield
    teams._set_client(None)


@pytest.mark.asyncio
async def test_list_team_members_returns_all_members() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/teams/{_TEAM_ID}/members").mock(
            return_value=httpx.Response(200, json=_MEMBERS_RESPONSE)
        )
        result = await teams.list_team_members(team_id=_TEAM_ID)
    assert result["total_members"] == 4
    assert result["team_id"] == _TEAM_ID


@pytest.mark.asyncio
async def test_list_team_members_billed_seat_flags() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/teams/{_TEAM_ID}/members").mock(
            return_value=httpx.Response(200, json=_MEMBERS_RESPONSE)
        )
        result = await teams.list_team_members(team_id=_TEAM_ID)
    members_by_handle = {m["handle"]: m for m in result["members"]}
    assert members_by_handle["alice"]["billed_seat"] is True   # owner
    assert members_by_handle["bob"]["billed_seat"] is True     # editor
    assert members_by_handle["carol"]["billed_seat"] is False  # viewer
    assert members_by_handle["dave"]["billed_seat"] is False   # viewer_restricted


@pytest.mark.asyncio
async def test_list_team_members_seat_counts() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/teams/{_TEAM_ID}/members").mock(
            return_value=httpx.Response(200, json=_MEMBERS_RESPONSE)
        )
        result = await teams.list_team_members(team_id=_TEAM_ID)
    assert result["billed_seats"] == 2
    assert result["free_seats"] == 2


@pytest.mark.asyncio
async def test_get_team_billing_summary_splits_tiers() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/teams/{_TEAM_ID}/members").mock(
            return_value=httpx.Response(200, json=_MEMBERS_RESPONSE)
        )
        result = await teams.get_team_billing_summary(team_id=_TEAM_ID)
    assert result["billed_editor_seats"] == 2
    assert result["free_viewer_seats"] == 2
    assert result["total_members"] == 4


@pytest.mark.asyncio
async def test_get_team_billing_summary_role_breakdown() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/teams/{_TEAM_ID}/members").mock(
            return_value=httpx.Response(200, json=_MEMBERS_RESPONSE)
        )
        result = await teams.get_team_billing_summary(team_id=_TEAM_ID)
    assert result["role_breakdown"]["owner"] == 1
    assert result["role_breakdown"]["editor"] == 1
    assert result["role_breakdown"]["viewer"] == 1
    assert result["role_breakdown"]["viewer_restricted"] == 1


@pytest.mark.asyncio
async def test_get_team_billing_summary_editor_list() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/teams/{_TEAM_ID}/members").mock(
            return_value=httpx.Response(200, json=_MEMBERS_RESPONSE)
        )
        result = await teams.get_team_billing_summary(team_id=_TEAM_ID)
    editor_handles = {e["handle"] for e in result["editors"]}
    assert editor_handles == {"alice", "bob"}
    viewer_handles = {v["handle"] for v in result["viewers"]}
    assert viewer_handles == {"carol", "dave"}


@pytest.mark.asyncio
async def test_list_team_members_missing_team_id_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIGMA_ACCESS_TOKEN", "tok")
    monkeypatch.setenv("FIGMA_SCIM_TOKEN", "scim")
    monkeypatch.setenv("FIGMA_ORG_ID", "org-1")
    monkeypatch.delenv("FIGMA_TEAM_ID", raising=False)
    with pytest.raises(ValueError, match="team_id is required"):
        await teams.list_team_members(team_id=None)


@pytest.mark.asyncio
async def test_list_team_members_uses_env_team_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIGMA_TEAM_ID", _TEAM_ID)
    monkeypatch.setenv("FIGMA_ACCESS_TOKEN", "tok")
    monkeypatch.setenv("FIGMA_SCIM_TOKEN", "scim")
    monkeypatch.setenv("FIGMA_ORG_ID", "org-1")
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/teams/{_TEAM_ID}/members").mock(
            return_value=httpx.Response(200, json=_MEMBERS_RESPONSE)
        )
        result = await teams.list_team_members()
    assert result["team_id"] == _TEAM_ID
