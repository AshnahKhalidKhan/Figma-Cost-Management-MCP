from pydantic import BaseModel

# Roles that consume a paid editor seat on Figma Pro/Organization plans.
# owner and admin are always billed at editor rate.
EDITOR_ROLES: frozenset[str] = frozenset({"owner", "admin", "editor"})
VIEWER_ROLES: frozenset[str] = frozenset({"viewer", "viewer_restricted"})


class FigmaUser(BaseModel):
    id: str
    handle: str
    img_url: str | None = None
    email: str | None = None


class TeamMember(BaseModel):
    user: FigmaUser
    role: str  # str to handle any undocumented future roles gracefully


class TeamMembersResponse(BaseModel):
    members: list[TeamMember]
