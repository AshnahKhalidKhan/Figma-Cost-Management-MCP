from pydantic import BaseModel


class CommentUser(BaseModel):
    id: str | None = None
    handle: str
    img_url: str | None = None


class CommentReaction(BaseModel):
    emoji: str
    created_at: str


class Comment(BaseModel):
    id: str
    file_key: str | None = None
    parent_id: str | None = None
    user: CommentUser
    created_at: str
    resolved_at: str | None = None
    message: str
    order_id: str | int | None = None
    client_meta: dict | None = None
    reactions: list[CommentReaction] | None = None


class CommentsResponse(BaseModel):
    comments: list[Comment]
