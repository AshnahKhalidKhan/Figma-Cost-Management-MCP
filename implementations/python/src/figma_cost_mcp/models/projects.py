from pydantic import BaseModel


class Project(BaseModel):
    id: str
    name: str


class TeamProjectsResponse(BaseModel):
    projects: list[Project]


class ProjectFile(BaseModel):
    key: str
    name: str
    last_modified: str
    thumbnail_url: str | None = None
    branches: list[dict] | None = None


class ProjectFilesResponse(BaseModel):
    files: list[ProjectFile]
