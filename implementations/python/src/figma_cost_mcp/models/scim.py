from typing import Any

from pydantic import BaseModel, Field


class ScimUserRole(BaseModel):
    value: str  # "Full" | "Dev" | "Collab" | "View"
    primary: bool = False


class ScimUserName(BaseModel):
    formatted: str | None = None
    given_name: str | None = Field(None, alias="givenName")
    family_name: str | None = Field(None, alias="familyName")

    model_config = {"populate_by_name": True}


class ScimUser(BaseModel):
    id: str | None = None
    user_name: str = Field(alias="userName")
    active: bool = True
    display_name: str | None = Field(None, alias="displayName")
    name: ScimUserName | None = None
    roles: list[ScimUserRole] = []
    title: str | None = None

    model_config = {"populate_by_name": True}


class ScimGroupMember(BaseModel):
    value: str
    display: str | None = None


class ScimGroup(BaseModel):
    id: str | None = None
    display_name: str = Field(alias="displayName")
    external_id: str | None = Field(None, alias="externalId")
    members: list[ScimGroupMember] = []

    model_config = {"populate_by_name": True}


class ScimListResponse(BaseModel):
    total_results: int = Field(alias="totalResults")
    items_per_page: int = Field(alias="itemsPerPage")
    start_index: int = Field(alias="startIndex")
    resources: list[dict[str, Any]] = Field(alias="Resources")

    model_config = {"populate_by_name": True}
