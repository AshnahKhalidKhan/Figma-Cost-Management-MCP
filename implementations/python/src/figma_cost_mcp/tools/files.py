import logging
from typing import Annotated

from .._mcp import mcp
from ..config import Config
from ..http_client import RateLimitedClient, make_rest_client
from ..models.files import FileVersionsResponse, FileMeta
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


@mcp.tool()
async def get_file(
    file_key: Annotated[str, "Figma file key — the alphanumeric ID in the file URL after /design/ or /file/"],
    version: Annotated[str | None, "Specific version ID to retrieve (from get_file_versions)"] = None,
    depth: Annotated[int | None, "Node depth limit (1=pages only, 2=frames, etc.). Omit for full tree."] = None,
) -> dict:
    """Get Figma file metadata and document structure.

    Returns the file name, last modified time, version, role, editor type, thumbnail,
    and the full document tree up to the requested depth. Use depth=1 to get just
    page names without fetching the entire design tree.

    File key is the alphanumeric string in the Figma URL:
    figma.com/design/{FILE_KEY}/...  or  figma.com/file/{FILE_KEY}/...
    """
    params: dict = {}
    if version:
        params["version"] = version
    if depth is not None:
        params["depth"] = depth
    data = await _get_client().get(f"/v1/files/{file_key}", params=params or None)
    return {
        "name": data.get("name"),
        "last_modified": data.get("lastModified"),
        "thumbnail_url": data.get("thumbnailUrl"),
        "version": data.get("version"),
        "role": data.get("role"),
        "editor_type": data.get("editorType"),
        "link_access": data.get("linkAccess"),
        "schema_version": data.get("schemaVersion"),
        "pages": [
            {"id": page.get("id"), "name": page.get("name")}
            for page in (data.get("document", {}).get("children") or [])
        ],
    }


@mcp.tool()
async def get_file_nodes(
    file_key: Annotated[str, "Figma file key"],
    ids: Annotated[str, "Comma-separated list of node IDs to retrieve (e.g. '1:2,3:4')"],
    version: Annotated[str | None, "Specific version ID"] = None,
    depth: Annotated[int | None, "Node traversal depth limit"] = None,
) -> dict:
    """Get specific nodes from a Figma file by their node IDs.

    Returns the node data (type, name, children, properties) for each requested ID.
    Node IDs look like '1:2' or '0:1' and can be found in the Figma URL when a
    node is selected, or from get_file results.

    Useful for extracting specific frames, components, or layers without loading
    the entire file tree.
    """
    params: dict = {"ids": ids}
    if version:
        params["version"] = version
    if depth is not None:
        params["depth"] = depth
    data = await _get_client().get(f"/v1/files/{file_key}/nodes", params=params)
    return {
        "name": data.get("name"),
        "nodes": data.get("nodes", {}),
    }


@mcp.tool()
async def get_file_versions(
    file_key: Annotated[str, "Figma file key"],
) -> dict:
    """Get the version history of a Figma file.

    Returns all saved versions with their IDs, labels, descriptions, creation timestamps,
    and the user who created each version. Version IDs can be passed to get_file or
    get_file_nodes to retrieve a specific historical snapshot.

    Note: Only named versions (created via File → Save to Version History) appear
    here. Auto-saves are not included.
    """
    data = await _get_client().get(f"/v1/files/{file_key}/versions")
    response = FileVersionsResponse.model_validate(data)
    return {
        "file_key": file_key,
        "versions": [
            {
                "id": v.id,
                "created_at": v.created_at,
                "label": v.label,
                "description": v.description,
                "created_by": v.user.handle if v.user else None,
            }
            for v in response.versions
        ],
        "total": len(response.versions),
    }


@mcp.tool()
async def export_file_images(
    file_key: Annotated[str, "Figma file key"],
    ids: Annotated[str, "Comma-separated node IDs to export (e.g. '1:2,3:4')"],
    format: Annotated[str, "Export format: png, jpg, svg, or pdf"] = "png",
    scale: Annotated[float, "Export scale multiplier (0.01–4). Use 2 for 2x/Retina."] = 1.0,
    svg_include_id: Annotated[bool, "SVG only: include node IDs as element IDs"] = False,
    svg_simplify_stroke: Annotated[bool, "SVG only: simplify inside/outside strokes"] = True,
    use_absolute_bounds: Annotated[bool, "Use absolute bounding box (includes effects outside frame)"] = False,
    contents_only: Annotated[bool, "Omit background canvas color"] = True,
) -> dict:
    """Export Figma nodes as images and get their download URLs.

    Returns a map of node ID → image URL. URLs are temporary (expire after a short time).
    Supports PNG, JPG, SVG, and PDF export formats.

    Use scale=2 for @2x Retina exports. For SVG, set svg_include_id=True to
    preserve node names as CSS/JS selectors.
    """
    params: dict = {
        "ids": ids,
        "format": format,
        "scale": scale,
        "svg_include_id": str(svg_include_id).lower(),
        "svg_simplify_stroke": str(svg_simplify_stroke).lower(),
        "use_absolute_bounds": str(use_absolute_bounds).lower(),
        "contentsOnly": str(contents_only).lower(),
    }
    data = await _get_client().get(f"/v1/images/{file_key}", params=params)
    return {
        "file_key": file_key,
        "format": format,
        "images": data.get("images", {}),
        "err": data.get("err"),
    }


@mcp.tool()
async def get_file_image_fills(
    file_key: Annotated[str, "Figma file key"],
) -> dict:
    """Get download URLs for all image fills used in a Figma file.

    Figma stores images referenced in fills (background images, image layers) separately.
    This returns a map of image reference → download URL for all such images in the file.

    Use this when you need to download the actual image assets embedded in a design,
    such as photos, icons, or textures placed directly in Figma frames.
    """
    data = await _get_client().get(f"/v1/files/{file_key}/images")
    return {
        "file_key": file_key,
        "images": data.get("meta", {}).get("images", data.get("images", {})),
    }
