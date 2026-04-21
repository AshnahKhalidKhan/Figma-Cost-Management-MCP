import logging
from typing import Annotated

from .._mcp import mcp
from ..config import Config
from ..http_client import RateLimitedClient, make_rest_client
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


def _fmt_dev_resource(r: dict) -> dict:
    return {
        "id": r.get("id"),
        "name": r.get("name"),
        "url": r.get("url"),
        "file_key": r.get("file_key"),
        "node_id": r.get("node_id"),
        "created_at": r.get("created_at"),
        "updated_at": r.get("updated_at"),
    }


@mcp.tool()
async def get_dev_resources(
    file_key: Annotated[str, "Figma file key"],
    node_ids: Annotated[
        str | None,
        "Comma-separated node IDs to filter by (e.g. '1:2,3:4'). Omit for all resources in the file.",
    ] = None,
) -> dict:
    """Get dev resources (linked URLs) attached to nodes in a Figma file.

    Dev resources are links (GitHub PRs, Storybook stories, Jira tickets, etc.)
    attached to specific design nodes to connect designs with their implementation.
    They appear in Figma's Dev Mode panel.

    Filter by node_ids to get resources for specific frames or components only.
    Returns each resource's name, URL, associated node ID, and timestamps.
    """
    params: dict = {}
    if node_ids:
        params["node_ids"] = node_ids
    data = await _get_client().get(f"/v1/files/{file_key}/dev_resources", params=params or None)
    resources = data.get("dev_resources", [])
    errors = data.get("errors", [])
    return {
        "file_key": file_key,
        "dev_resources": [_fmt_dev_resource(r) for r in resources],
        "total": len(resources),
        "errors": errors,
    }


@mcp.tool()
async def create_dev_resource(
    name: Annotated[str, "Display name for the dev resource link"],
    url: Annotated[str, "URL to link (GitHub, Storybook, Jira, Confluence, etc.)"],
    file_key: Annotated[str, "Figma file key the node belongs to"],
    node_id: Annotated[str, "Node ID to attach this resource to (e.g. '1:2')"],
) -> dict:
    """Attach a dev resource (external link) to a specific Figma node.

    Dev resources link design nodes to their implementation artifacts — GitHub PRs,
    Storybook stories, Jira tickets, Confluence docs, etc. They appear in Figma's
    Dev Mode panel when developers inspect a design.

    Returns the created resource's ID, which can be used to update or delete it later.
    """
    body = {
        "dev_resources": [
            {
                "name": name,
                "url": url,
                "file_key": file_key,
                "node_id": node_id,
            }
        ]
    }
    data = await _get_client().post("/v1/dev_resources", json=body)
    resources = data.get("dev_resources_created", data.get("dev_resources", []))
    errors = data.get("errors", [])
    created = resources[0] if resources else {}
    return {
        "created": _fmt_dev_resource(created) if created else None,
        "errors": errors,
    }


@mcp.tool()
async def update_dev_resource(
    dev_resource_id: Annotated[str, "Dev resource ID to update (from get_dev_resources)"],
    name: Annotated[str | None, "New display name"] = None,
    url: Annotated[str | None, "New URL"] = None,
) -> dict:
    """Update the name or URL of an existing dev resource.

    Only provided fields are updated — omit fields you don't want to change.
    At least one of name or url must be provided.
    """
    if name is None and url is None:
        raise ValueError("At least one of name or url must be provided.")
    update: dict = {"id": dev_resource_id}
    if name is not None:
        update["name"] = name
    if url is not None:
        update["url"] = url
    body = {"dev_resources": [update]}
    data = await _get_client().put("/v1/dev_resources", json=body)
    resources = data.get("dev_resources_updated", data.get("dev_resources", []))
    errors = data.get("errors", [])
    updated = resources[0] if resources else {}
    return {
        "updated": _fmt_dev_resource(updated) if updated else None,
        "errors": errors,
    }


@mcp.tool()
async def delete_dev_resource(
    file_key: Annotated[str, "Figma file key the dev resource belongs to"],
    dev_resource_id: Annotated[str, "Dev resource ID to delete (from get_dev_resources)"],
) -> dict:
    """Remove a dev resource link from a Figma node.

    Permanently unlinks the external resource (GitHub PR, Storybook story, etc.)
    from the design node. This cannot be undone. The linked URL itself is unaffected.
    """
    await _get_client().delete(f"/v1/files/{file_key}/dev_resources/{dev_resource_id}")
    return {"deleted": True, "dev_resource_id": dev_resource_id}
