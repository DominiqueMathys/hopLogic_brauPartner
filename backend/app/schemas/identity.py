from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=1, max_length=200)


class PasswordChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=12, max_length=200)


class PasswordResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=200)


class PasswordResetConfirm(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=10, max_length=200)
    new_password: str = Field(min_length=12, max_length=200)


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)


class UserWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    email: str = Field(min_length=3, max_length=200)
    role_code: str = Field(min_length=2, max_length=40)
    password: str | None = Field(default=None, max_length=200)


class StatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str


class PermissionRead(BaseModel):
    code: str
    resource: str
    action: str
    description: str


class RoleRead(BaseModel):
    code: str
    name: str
    description: str
    permissions: list[str]


class RolePermissionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    permissions: list[str]


class UserRead(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    display_name: str
    email: str
    role_code: str
    role_name: str
    status: str
    created_at: datetime
    last_login_at: datetime | None
    permissions: list[str]
    is_demo: bool


class UserList(BaseModel):
    items: list[UserRead]
    total: int
    page: int
    page_size: int


class DirectoryEntry(BaseModel):
    id: UUID
    display_name: str
    role_code: str
    role_name: str


class SessionRead(BaseModel):
    user: UserRead
    csrf_token: str


class AuditRead(BaseModel):
    id: UUID
    event_type: str
    occurred_at: datetime
    actor_id: UUID | None
    actor_label: str | None
    resource_type: str | None
    resource_id: str | None
    result: str
    detail: str | None


class AuditList(BaseModel):
    items: list[AuditRead]
    total: int
    page: int
    page_size: int
