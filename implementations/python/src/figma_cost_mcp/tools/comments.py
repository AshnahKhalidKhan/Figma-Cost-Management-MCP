import logging
from typing import Annotated

from .._mcp import mcp
from ..config import Config
from ..http_client import RateLimitedClient, make_rest_client
from ..models.comments import CommentsResponse
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


def _fmt_comment(c: dict) -> dict:
    user = c.get("user") or {}
    return {
        "id": c.get("id"),
        "parent_id": c.get("parent_id"),
        "message": c.get("message"),
        "created_at": c.get("created_at"),
        "resolved_at": c.get("resolved_at"),
        "user": {
            "id": user.get("id"),
            "handle": user.get("handle"),
        },
        "reactions": [
            {"emoji": r.get("emoji"), "created_at": r.get("created_at")}
            for r in (c.get("reactions") or [])
        ],
        "client_meta": c.get("client_meta"),
    }


@mcp.tool()
async def get_file_comments(
    file_key: Annotated[str, "Figma file key"],
) -> dict:
    """Get all comments on a Figma file.

    Returns every top-level comment and reply thread, including the author's handle,
    message text, creation timestamp, resolved status, reactions, and position
    metadata (client_meta) linking each comment to a specific node or canvas position.

    Use parent_id to reconstruct reply threads — replies reference their parent comment's ID.
    """
    data = await _get_client().get(f"/v1/files/{file_key}/comments")
    comments = data.get("comments", [])
    return {
        "file_key": file_key,
        "comments": [_fmt_comment(c) for c in comments],
        "total": len(comments),
    }


@mcp.tool()
async def post_file_comment(
    file_key: Annotated[str, "Figma file key"],
    message: Annotated[str, "Comment text. Supports @mentions using handle syntax."],
    comment_id: Annotated[str | None, "Parent comment ID to reply to a specific thread"] = None,
) -> dict:
    """Post a comment or reply on a Figma file.

    To post a top-level comment, omit comment_id.
    To reply to an existing comment, pass its ID as comment_id.

    Comments support @mentions: use '@handle' to notify a specific team member.
    Returns the new comment's ID, message, and creation timestamp.
    """
    body: dict = {"message": message}
    if comment_id:
        body["comment_id"] = comment_id
    data = await _get_client().post(f"/v1/files/{file_key}/comments", json=body)
    return _fmt_comment(data)


@mcp.tool()
async def delete_file_comment(
    file_key: Annotated[str, "Figma file key"],
    comment_id: Annotated[str, "Comment ID to delete (from get_file_comments)"],
) -> dict:
    """Delete a comment from a Figma file.

    You can only delete comments you authored, or any comment if you are an owner/admin.
    Deleting a parent comment does not delete its replies.
    This action cannot be undone.
    """
    await _get_client().delete(f"/v1/files/{file_key}/comments/{comment_id}")
    return {"deleted": True, "comment_id": comment_id}


@mcp.tool()
async def react_to_comment(
    file_key: Annotated[str, "Figma file key"],
    comment_id: Annotated[str, "Comment ID to react to"],
    emoji: Annotated[str, "Emoji to react with (e.g. ':heart:', ':thumbsup:')"],
    action: Annotated[str, "Either 'add' or 'remove'"] = "add",
) -> dict:
    """Add or remove an emoji reaction on a Figma comment.

    Use action='add' to add a reaction, action='remove' to remove your existing reaction.
    Emoji must be a valid Figma-supported emoji code (e.g. ':heart:', ':thumbsup:').
    """
    action_lower = action.lower()
    if action_lower not in {"add", "remove"}:
        raise ValueError("action must be 'add' or 'remove'")
    if action_lower == "add":
        data = await _get_client().post(
            f"/v1/files/{file_key}/comments/{comment_id}/reactions",
            json={"emoji": emoji},
        )
        return {"reacted": True, "emoji": emoji, "comment_id": comment_id}
    else:
        await _get_client().delete(
            f"/v1/files/{file_key}/comments/{comment_id}/reactions?emoji={emoji}"
        )
        return {"removed": True, "emoji": emoji, "comment_id": comment_id}
