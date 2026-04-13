import pytest
import httpx
import respx

from figma_cost_mcp.http_client import FIGMA_SCIM_BASE, RateLimitedClient
from figma_cost_mcp.tools import scim

_USER = {
    "id": "user-123",
    "userName": "alice@example.com",
    "active": True,
    "displayName": "Alice",
    "roles": [{"value": "Full"}],
}
_GROUP = {
    "id": "group-456",
    "displayName": "Design Team",
    "members": [],
}


@pytest.fixture(autouse=True)
def inject_mock_client() -> None:
    scim._set_client(RateLimitedClient(FIGMA_SCIM_BASE, "test-scim-token"))
    yield
    scim._set_client(None)


@pytest.mark.asyncio
async def test_list_users_returns_response() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_SCIM_BASE}/Users").mock(
            return_value=httpx.Response(200, json={"totalResults": 1, "Resources": [_USER]})
        )
        result = await scim.list_figma_users()
    assert result["totalResults"] == 1


@pytest.mark.asyncio
async def test_list_users_filter_by_email() -> None:
    with respx.mock:
        route = respx.get(f"{FIGMA_SCIM_BASE}/Users").mock(
            return_value=httpx.Response(200, json={"totalResults": 1, "Resources": [_USER]})
        )
        await scim.list_figma_users(filter_email="alice@example.com")
    assert "userName" in str(route.calls[0].request.url)


@pytest.mark.asyncio
async def test_get_user() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_SCIM_BASE}/Users/user-123").mock(
            return_value=httpx.Response(200, json=_USER)
        )
        result = await scim.get_figma_user("user-123")
    assert result["id"] == "user-123"


@pytest.mark.asyncio
async def test_create_user_sends_schemas() -> None:
    with respx.mock:
        route = respx.post(f"{FIGMA_SCIM_BASE}/Users").mock(
            return_value=httpx.Response(201, json=_USER)
        )
        result = await scim.create_figma_user("alice@example.com", seat_type="Full")
    assert result["userName"] == "alice@example.com"
    import json
    body = json.loads(route.calls[0].request.content)
    assert "urn:ietf:params:scim:schemas:core:2.0:User" in body["schemas"]
    assert body["roles"][0]["value"] == "Full"


@pytest.mark.asyncio
async def test_create_user_with_display_name() -> None:
    with respx.mock:
        route = respx.post(f"{FIGMA_SCIM_BASE}/Users").mock(
            return_value=httpx.Response(201, json=_USER)
        )
        await scim.create_figma_user("alice@example.com", display_name="Alice Smith")
    import json
    body = json.loads(route.calls[0].request.content)
    assert body["displayName"] == "Alice Smith"


@pytest.mark.asyncio
async def test_deactivate_user() -> None:
    with respx.mock:
        route = respx.patch(f"{FIGMA_SCIM_BASE}/Users/user-123").mock(
            return_value=httpx.Response(200, json={**_USER, "active": False})
        )
        result = await scim.deactivate_figma_user("user-123")
    assert result["active"] is False
    import json
    body = json.loads(route.calls[0].request.content)
    assert body["Operations"][0] == {"op": "replace", "path": "active", "value": False}


@pytest.mark.asyncio
async def test_change_seat_type() -> None:
    with respx.mock:
        route = respx.patch(f"{FIGMA_SCIM_BASE}/Users/user-123").mock(
            return_value=httpx.Response(200, json={**_USER, "roles": [{"value": "View"}]})
        )
        result = await scim.change_figma_user_seat("user-123", "View")
    assert result["roles"][0]["value"] == "View"
    import json
    body = json.loads(route.calls[0].request.content)
    assert body["Operations"][0]["path"] == "roles"


@pytest.mark.asyncio
async def test_delete_user_returns_confirmation() -> None:
    with respx.mock:
        respx.delete(f"{FIGMA_SCIM_BASE}/Users/user-123").mock(
            return_value=httpx.Response(204)
        )
        result = await scim.delete_figma_user("user-123")
    assert "user-123" in result


@pytest.mark.asyncio
async def test_list_groups() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_SCIM_BASE}/Groups").mock(
            return_value=httpx.Response(200, json={"totalResults": 1, "Resources": [_GROUP]})
        )
        result = await scim.list_figma_groups()
    assert result["totalResults"] == 1


@pytest.mark.asyncio
async def test_get_group() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_SCIM_BASE}/Groups/group-456").mock(
            return_value=httpx.Response(200, json=_GROUP)
        )
        result = await scim.get_figma_group("group-456")
    assert result["displayName"] == "Design Team"


@pytest.mark.asyncio
async def test_create_group_with_members() -> None:
    with respx.mock:
        route = respx.post(f"{FIGMA_SCIM_BASE}/Groups").mock(
            return_value=httpx.Response(201, json=_GROUP)
        )
        await scim.create_figma_group("Design Team", member_ids=["user-123"])
    import json
    body = json.loads(route.calls[0].request.content)
    assert body["displayName"] == "Design Team"
    assert body["members"] == [{"value": "user-123"}]


@pytest.mark.asyncio
async def test_add_group_members() -> None:
    with respx.mock:
        route = respx.patch(f"{FIGMA_SCIM_BASE}/Groups/group-456").mock(
            return_value=httpx.Response(200, json={**_GROUP, "members": [{"value": "user-123"}]})
        )
        result = await scim.add_group_members("group-456", ["user-123"])
    assert len(result["members"]) == 1
    import json
    body = json.loads(route.calls[0].request.content)
    assert body["Operations"][0]["op"] == "add"


@pytest.mark.asyncio
async def test_remove_group_members() -> None:
    with respx.mock:
        route = respx.patch(f"{FIGMA_SCIM_BASE}/Groups/group-456").mock(
            return_value=httpx.Response(200, json=_GROUP)
        )
        await scim.remove_group_members("group-456", ["user-123"])
    import json
    body = json.loads(route.calls[0].request.content)
    assert body["Operations"][0]["op"] == "remove"


@pytest.mark.asyncio
async def test_delete_group_returns_confirmation() -> None:
    with respx.mock:
        respx.delete(f"{FIGMA_SCIM_BASE}/Groups/group-456").mock(
            return_value=httpx.Response(204)
        )
        result = await scim.delete_figma_group("group-456")
    assert "group-456" in result
