import httpx
import pytest
import respx

from figma_cost_mcp.http_client import FIGMA_API_BASE, RateLimitedClient
from figma_cost_mcp.tools import comments

_FILE_KEY = "file-abc"
_COMMENT_ID = "cmt-123"

_COMMENT = {
    "id": _COMMENT_ID,
    "file_key": _FILE_KEY,
    "parent_id": None,
    "message": "Looks great!",
    "created_at": "2024-01-15T10:00:00Z",
    "resolved_at": None,
    "user": {"id": "u1", "handle": "alice", "img_url": ""},
    "reactions": [{"emoji": ":heart:", "created_at": "2024-01-15T11:00:00Z"}],
    "client_meta": None,
}

_REPLY = {
    "id": "cmt-456",
    "file_key": _FILE_KEY,
    "parent_id": _COMMENT_ID,
    "message": "Thanks!",
    "created_at": "2024-01-15T10:30:00Z",
    "resolved_at": None,
    "user": {"id": "u2", "handle": "bob", "img_url": ""},
    "reactions": [],
    "client_meta": None,
}

_COMMENTS_RESPONSE = {"comments": [_COMMENT, _REPLY]}


@pytest.fixture(autouse=True)
def inject_mock_client() -> None:
    comments._set_client(RateLimitedClient(FIGMA_API_BASE, "test-token"))
    yield
    comments._set_client(None)


@pytest.mark.asyncio
async def test_get_file_comments_returns_all() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/files/{_FILE_KEY}/comments").mock(
            return_value=httpx.Response(200, json=_COMMENTS_RESPONSE)
        )
        result = await comments.get_file_comments(_FILE_KEY)
    assert result["total"] == 2
    assert result["comments"][0]["message"] == "Looks great!"


@pytest.mark.asyncio
async def test_get_file_comments_includes_reactions() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/files/{_FILE_KEY}/comments").mock(
            return_value=httpx.Response(200, json=_COMMENTS_RESPONSE)
        )
        result = await comments.get_file_comments(_FILE_KEY)
    assert result["comments"][0]["reactions"][0]["emoji"] == ":heart:"


@pytest.mark.asyncio
async def test_get_file_comments_reply_has_parent_id() -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/files/{_FILE_KEY}/comments").mock(
            return_value=httpx.Response(200, json=_COMMENTS_RESPONSE)
        )
        result = await comments.get_file_comments(_FILE_KEY)
    assert result["comments"][1]["parent_id"] == _COMMENT_ID


@pytest.mark.asyncio
async def test_post_file_comment_sends_message() -> None:
    with respx.mock:
        route = respx.post(f"{FIGMA_API_BASE}/v1/files/{_FILE_KEY}/comments").mock(
            return_value=httpx.Response(200, json=_COMMENT)
        )
        result = await comments.post_file_comment(_FILE_KEY, "Looks great!")
    assert result["message"] == "Looks great!"
    assert route.called


@pytest.mark.asyncio
async def test_post_file_comment_reply_includes_parent() -> None:
    with respx.mock:
        respx.post(f"{FIGMA_API_BASE}/v1/files/{_FILE_KEY}/comments").mock(
            return_value=httpx.Response(200, json=_REPLY)
        )
        result = await comments.post_file_comment(_FILE_KEY, "Thanks!", comment_id=_COMMENT_ID)
    assert result["parent_id"] == _COMMENT_ID


@pytest.mark.asyncio
async def test_delete_file_comment_returns_confirmation() -> None:
    with respx.mock:
        respx.delete(f"{FIGMA_API_BASE}/v1/files/{_FILE_KEY}/comments/{_COMMENT_ID}").mock(
            return_value=httpx.Response(204)
        )
        result = await comments.delete_file_comment(_FILE_KEY, _COMMENT_ID)
    assert result["deleted"] is True
    assert result["comment_id"] == _COMMENT_ID


@pytest.mark.asyncio
async def test_react_to_comment_add_posts() -> None:
    with respx.mock:
        route = respx.post(
            f"{FIGMA_API_BASE}/v1/files/{_FILE_KEY}/comments/{_COMMENT_ID}/reactions"
        ).mock(return_value=httpx.Response(200, json={}))
        result = await comments.react_to_comment(_FILE_KEY, _COMMENT_ID, ":heart:", action="add")
    assert result["reacted"] is True
    assert route.called


@pytest.mark.asyncio
async def test_react_to_comment_invalid_action_raises() -> None:
    with pytest.raises(ValueError, match="action must be"):
        await comments.react_to_comment(_FILE_KEY, _COMMENT_ID, ":heart:", action="toggle")
