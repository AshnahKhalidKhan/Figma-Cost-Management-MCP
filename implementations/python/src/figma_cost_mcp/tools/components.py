import logging
from typing import Annotated

from .._mcp import mcp
from ..config import Config
from ..http_client import RateLimitedClient, make_rest_client
from ..models.components import Component, ComponentSet, Style
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
            "team_id is required. Set FIGMA_TEAM_ID in your environment, or pass it as a parameter."
        )
    return env_team_id


def _parse_component(raw: dict) -> dict:
    c = Component.model_validate(raw)
    return {
        "key": c.key,
        "file_key": c.file_key,
        "node_id": c.node_id,
        "name": c.name,
        "description": c.description,
        "thumbnail_url": c.thumbnail_url,
        "created_at": c.created_at,
        "updated_at": c.updated_at,
    }


def _parse_style(raw: dict) -> dict:
    s = Style.model_validate(raw)
    return {
        "key": s.key,
        "file_key": s.file_key,
        "node_id": s.node_id,
        "name": s.name,
        "description": s.description,
        "style_type": s.style_type,
        "created_at": s.created_at,
        "updated_at": s.updated_at,
    }


@mcp.tool()
async def get_team_components(
    team_id: Annotated[str | None, "Figma team ID. Defaults to FIGMA_TEAM_ID env var."] = None,
    page_size: Annotated[int | None, "Number of components per page (max 100)"] = None,
    cursor: Annotated[str | None, "Pagination cursor from a previous response"] = None,
) -> dict:
    """List all published components in a Figma team's component library.

    Returns components published to the team library — these are reusable design
    elements that designers can insert into any file. Includes component key,
    name, description, file origin, and thumbnail.

    Use the cursor from the response to paginate through large libraries.
    Available on Organization and Enterprise plans.
    """
    tid = _resolve_team_id(team_id)
    params: dict = {}
    if page_size is not None:
        params["page_size"] = page_size
    if cursor:
        params["cursor"] = cursor
    data = await _get_client().get(f"/v1/teams/{tid}/components", params=params or None)
    meta = data.get("meta", data)
    components = meta.get("components", [])
    return {
        "team_id": tid,
        "components": [_parse_component(c) for c in components],
        "total": len(components),
        "cursor": meta.get("cursor"),
    }


@mcp.tool()
async def get_team_component_sets(
    team_id: Annotated[str | None, "Figma team ID. Defaults to FIGMA_TEAM_ID env var."] = None,
    page_size: Annotated[int | None, "Number of component sets per page (max 100)"] = None,
    cursor: Annotated[str | None, "Pagination cursor from a previous response"] = None,
) -> dict:
    """List all published component sets in a Figma team's library.

    Component sets are groups of components that share a property (e.g., a Button
    component set with variants: Primary, Secondary, Disabled). Returns the set key,
    name, description, and file origin.

    Available on Organization and Enterprise plans.
    """
    tid = _resolve_team_id(team_id)
    params: dict = {}
    if page_size is not None:
        params["page_size"] = page_size
    if cursor:
        params["cursor"] = cursor
    data = await _get_client().get(f"/v1/teams/{tid}/component_sets", params=params or None)
    meta = data.get("meta", data)
    component_sets = meta.get("component_sets", [])
    return {
        "team_id": tid,
        "component_sets": [
            {
                "key": cs.get("key"),
                "file_key": cs.get("file_key"),
                "node_id": cs.get("node_id"),
                "name": cs.get("name"),
                "description": cs.get("description"),
                "created_at": cs.get("created_at"),
                "updated_at": cs.get("updated_at"),
            }
            for cs in component_sets
        ],
        "total": len(component_sets),
        "cursor": meta.get("cursor"),
    }


@mcp.tool()
async def get_team_styles(
    team_id: Annotated[str | None, "Figma team ID. Defaults to FIGMA_TEAM_ID env var."] = None,
    page_size: Annotated[int | None, "Number of styles per page (max 100)"] = None,
    cursor: Annotated[str | None, "Pagination cursor from a previous response"] = None,
) -> dict:
    """List all published styles in a Figma team's library.

    Styles include colors, text styles, effects, and grids published to the team library.
    Returns style key, name, type (FILL, TEXT, EFFECT, GRID), description, and origin file.

    Use this to audit your design system — find all published color tokens, typography
    scales, and effect presets across the team.
    Available on Organization and Enterprise plans.
    """
    tid = _resolve_team_id(team_id)
    params: dict = {}
    if page_size is not None:
        params["page_size"] = page_size
    if cursor:
        params["cursor"] = cursor
    data = await _get_client().get(f"/v1/teams/{tid}/styles", params=params or None)
    meta = data.get("meta", data)
    styles = meta.get("styles", [])
    return {
        "team_id": tid,
        "styles": [_parse_style(s) for s in styles],
        "total": len(styles),
        "cursor": meta.get("cursor"),
    }


@mcp.tool()
async def get_file_components(
    file_key: Annotated[str, "Figma file key"],
) -> dict:
    """List all components published from a specific Figma file.

    Returns components published to the team library from this particular file,
    including their keys, node IDs, names, and descriptions. Use the component
    key with get_component to fetch full details including the thumbnail.
    """
    data = await _get_client().get(f"/v1/files/{file_key}/components")
    meta = data.get("meta", data)
    components = meta.get("components", [])
    return {
        "file_key": file_key,
        "components": [_parse_component(c) for c in components],
        "total": len(components),
    }


@mcp.tool()
async def get_file_styles(
    file_key: Annotated[str, "Figma file key"],
) -> dict:
    """List all styles published from a specific Figma file.

    Returns styles published to the team library from this file, including
    their keys, node IDs, types, names, and descriptions.
    Style types: FILL, TEXT, EFFECT, GRID.
    """
    data = await _get_client().get(f"/v1/files/{file_key}/styles")
    meta = data.get("meta", data)
    styles = meta.get("styles", [])
    return {
        "file_key": file_key,
        "styles": [_parse_style(s) for s in styles],
        "total": len(styles),
    }


@mcp.tool()
async def get_component(
    component_key: Annotated[str, "Component key (from get_team_components or get_file_components)"],
) -> dict:
    """Get full details for a single Figma component by its key.

    Returns the component's key, name, description, file origin, node ID,
    thumbnail URL, creation/update timestamps, and containing frame/page info.

    Component keys are stable identifiers that persist across file moves and renames.
    """
    data = await _get_client().get(f"/v1/components/{component_key}")
    meta = data.get("meta", data)
    return _parse_component(meta)


@mcp.tool()
async def get_style(
    style_key: Annotated[str, "Style key (from get_team_styles or get_file_styles)"],
) -> dict:
    """Get full details for a single Figma style by its key.

    Returns the style's key, name, type (FILL, TEXT, EFFECT, GRID), description,
    file origin, node ID, and timestamps.

    Style keys are stable identifiers used in the Figma API for referencing
    design tokens like colors, typography, and effects.
    """
    data = await _get_client().get(f"/v1/styles/{style_key}")
    meta = data.get("meta", data)
    return _parse_style(meta)
