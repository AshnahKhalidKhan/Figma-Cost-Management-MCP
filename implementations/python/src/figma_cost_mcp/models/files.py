from pydantic import BaseModel, Field


class FileUser(BaseModel):
    id: str
    handle: str
    img_url: str | None = None
    email: str | None = None


class FileVersion(BaseModel):
    id: str
    created_at: str
    label: str | None = None
    description: str | None = None
    user: FileUser | None = None


class FileVersionsResponse(BaseModel):
    versions: list[FileVersion]


class FileMeta(BaseModel):
    name: str
    last_modified: str
    thumbnail_url: str | None = None
    version: str | None = None
    role: str | None = None
    editor_type: str | None = None
    link_access: str | None = None
