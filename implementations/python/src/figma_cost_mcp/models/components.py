from pydantic import BaseModel


class Component(BaseModel):
    key: str
    file_key: str | None = None
    node_id: str
    thumbnail_url: str | None = None
    name: str
    description: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    containing_frame: dict | None = None
    containing_page: dict | None = None


class ComponentSet(BaseModel):
    key: str
    file_key: str | None = None
    node_id: str
    name: str
    description: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    containing_frame: dict | None = None
    containing_page: dict | None = None


class Style(BaseModel):
    key: str
    file_key: str | None = None
    node_id: str
    name: str
    description: str | None = None
    style_type: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class PaginationCursor(BaseModel):
    before_id: str | None = None
    after_id: str | None = None
