import logging
from typing import Annotated, Any

from .._mcp import mcp
from ..config import Config
from ..http_client import RateLimitedClient, make_scim_client

logger = logging.getLogger(__name__)

_SCIM_USER_SCHEMAS = [
    "urn:ietf:params:scim:schemas:core:2.0:User",
    "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
    "urn:figma:params:scim:schemas:extension:figma:2.0:FigmaUser",
]
_SCIM_GROUP_SCHEMAS = ["urn:ietf:params:scim:schemas:core:2.0:Group"]
_PATCH_OP_SCHEMA = ["urn:ietf:params:scim:api:messages:2.0:PatchOp"]

_client: RateLimitedClient | None = None


def _get_client() -> RateLimitedClient:
    global _client
    if _client is None:
        _client = make_scim_client(Config.from_env().figma_scim_token)
    return _client


def _set_client(client: RateLimitedClient | None) -> None:
    global _client
    _client = client


@mcp.tool()
async def list_figma_users(
    filter_email: Annotated[str | None, "Filter by user email address"] = None,
    filter_external_id: Annotated[str | None, "Filter by external/SCIM ID"] = None,
    count: Annotated[int, "Results per page (max 200)"] = 100,
    start_index: Annotated[int, "1-based pagination index"] = 1,
) -> dict:
    """List Figma organization users managed via SCIM provisioning.

    Returns users with their seat types, active status, and account details.
    Use count and start_index for pagination.
    """
    params: dict[str, Any] = {"count": count, "startIndex": start_index}
    if filter_email:
        params["filter"] = f'userName eq "{filter_email}"'
    elif filter_external_id:
        params["filter"] = f'externalId eq "{filter_external_id}"'
    return await _get_client().get("/Users", params=params)


@mcp.tool()
async def get_figma_user(
    user_id: Annotated[str, "Figma SCIM user ID"],
) -> dict:
    """Get full profile for a Figma user by their SCIM user ID.

    Returns seat type, active status, roles, display name, and metadata.
    """
    return await _get_client().get(f"/Users/{user_id}")


@mcp.tool()
async def create_figma_user(
    email: Annotated[str, "User email address (becomes the SCIM userName)"],
    active: Annotated[bool, "Whether the user account is active"] = True,
    seat_type: Annotated[str, "Seat type: Full, Dev, Collab, or View"] = "View",
    display_name: Annotated[str | None, "User display name"] = None,
) -> dict:
    """Create a new Figma user via SCIM provisioning.

    Seat types affect billing (highest to lowest cost): Full > Dev > Collab > View.
    """
    body: dict[str, Any] = {
        "schemas": _SCIM_USER_SCHEMAS,
        "userName": email,
        "active": active,
        "roles": [{"value": seat_type}],
    }
    if display_name:
        body["displayName"] = display_name
    return await _get_client().post("/Users", json=body)


@mcp.tool()
async def update_figma_user(
    user_id: Annotated[str, "Figma SCIM user ID"],
    email: Annotated[str, "User email address"],
    active: Annotated[bool, "Whether the user account is active"],
    seat_type: Annotated[str, "Seat type: Full, Dev, Collab, or View"],
    display_name: Annotated[str | None, "User display name"] = None,
) -> dict:
    """Fully replace a Figma user's SCIM attributes (PUT).

    Overwrites all attributes. Use deactivate_figma_user or change_figma_user_seat
    for targeted changes.
    """
    body: dict[str, Any] = {
        "schemas": _SCIM_USER_SCHEMAS,
        "userName": email,
        "active": active,
        "roles": [{"value": seat_type}],
    }
    if display_name:
        body["displayName"] = display_name
    return await _get_client().put(f"/Users/{user_id}", json=body)


@mcp.tool()
async def deactivate_figma_user(
    user_id: Annotated[str, "Figma SCIM user ID"],
) -> dict:
    """Deactivate a Figma user (preferred over deletion for cost management).

    Sets active=false, removing seat access without deleting the user or their history.
    Frees the seat license for billing purposes.
    """
    body = {
        "schemas": _PATCH_OP_SCHEMA,
        "Operations": [{"op": "replace", "path": "active", "value": False}],
    }
    return await _get_client().patch(f"/Users/{user_id}", json=body)


@mcp.tool()
async def change_figma_user_seat(
    user_id: Annotated[str, "Figma SCIM user ID"],
    seat_type: Annotated[str, "New seat type: Full, Dev, Collab, or View"],
) -> dict:
    """Change the seat type (license tier) for a Figma user.

    Directly affects billing. Seat costs: Full > Dev > Collab > View.
    """
    body = {
        "schemas": _PATCH_OP_SCHEMA,
        "Operations": [{"op": "replace", "path": "roles", "value": [{"value": seat_type}]}],
    }
    return await _get_client().patch(f"/Users/{user_id}", json=body)


@mcp.tool()
async def delete_figma_user(
    user_id: Annotated[str, "Figma SCIM user ID"],
) -> str:
    """Permanently delete a Figma user from SCIM provisioning.

    Removes the user and their provisioning logs. Irreversible.
    Prefer deactivate_figma_user for reversible seat removal.
    """
    await _get_client().delete(f"/Users/{user_id}")
    return f"User {user_id} permanently deleted."


@mcp.tool()
async def list_figma_groups(
    filter_name: Annotated[str | None, "Filter groups by display name"] = None,
    filter_external_id: Annotated[str | None, "Filter groups by external ID"] = None,
    count: Annotated[int, "Results per page (max 200)"] = 100,
    start_index: Annotated[int, "1-based pagination index"] = 1,
) -> dict:
    """List Figma SCIM-managed groups (workspace or billing groups).

    Group membership determines workspace access and billing group assignments.
    """
    params: dict[str, Any] = {"count": count, "startIndex": start_index}
    if filter_name:
        params["filter"] = f'displayName eq "{filter_name}"'
    elif filter_external_id:
        params["filter"] = f'externalId eq "{filter_external_id}"'
    return await _get_client().get("/Groups", params=params)


@mcp.tool()
async def get_figma_group(
    group_id: Annotated[str, "Figma SCIM group ID"],
) -> dict:
    """Get details for a Figma SCIM group including all current members."""
    return await _get_client().get(f"/Groups/{group_id}")


@mcp.tool()
async def create_figma_group(
    display_name: Annotated[str, "Group name — must exactly match a Figma workspace or billing group name"],
    external_id: Annotated[str | None, "External system ID for this group (max 255 chars)"] = None,
    member_ids: Annotated[list[str], "Figma user IDs to add as initial members"] = [],
) -> dict:
    """Create a Figma SCIM group linked to a workspace or billing group.

    The display_name must exactly match an existing Figma workspace or billing group.
    Adding members grants them access to the linked workspace/billing group.
    """
    body: dict[str, Any] = {
        "schemas": _SCIM_GROUP_SCHEMAS,
        "displayName": display_name,
    }
    if external_id:
        body["externalId"] = external_id
    if member_ids:
        body["members"] = [{"value": uid} for uid in member_ids]
    return await _get_client().post("/Groups", json=body)


@mcp.tool()
async def add_group_members(
    group_id: Annotated[str, "Figma SCIM group ID"],
    user_ids: Annotated[list[str], "Figma user IDs to add to the group"],
) -> dict:
    """Add members to a Figma SCIM group, granting workspace/billing group access."""
    body = {
        "schemas": [*_SCIM_GROUP_SCHEMAS, *_PATCH_OP_SCHEMA],
        "Operations": [
            {"op": "add", "path": "members", "value": [{"value": uid} for uid in user_ids]}
        ],
    }
    return await _get_client().patch(f"/Groups/{group_id}", json=body)


@mcp.tool()
async def remove_group_members(
    group_id: Annotated[str, "Figma SCIM group ID"],
    user_ids: Annotated[list[str], "Figma user IDs to remove from the group"],
) -> dict:
    """Remove members from a Figma SCIM group, revoking workspace/billing group access."""
    body = {
        "schemas": [*_SCIM_GROUP_SCHEMAS, *_PATCH_OP_SCHEMA],
        "Operations": [
            {"op": "remove", "path": "members", "value": [{"value": uid} for uid in user_ids]}
        ],
    }
    return await _get_client().patch(f"/Groups/{group_id}", json=body)


@mcp.tool()
async def delete_figma_group(
    group_id: Annotated[str, "Figma SCIM group ID"],
) -> str:
    """Permanently delete a Figma SCIM group.

    Removes the group and its provisioning logs. Does not delete the underlying
    Figma workspace or billing group — only the SCIM link.
    """
    await _get_client().delete(f"/Groups/{group_id}")
    return f"Group {group_id} permanently deleted."
