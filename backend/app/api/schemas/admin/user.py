from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator


class UserRolePayload(BaseModel):
    role: str = Field(pattern="^(CUSTOMER|STAFF_ADMIN)$")
    status: str = Field(default="ACTIVE", pattern="^(ACTIVE|SUSPENDED)$")
    permissionCodes: list[str] | None = None

class RolePermissionsPayload(BaseModel):
    permissionCodes: list[str] = Field(default_factory=list)

class StaffCreatePayload(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    fullName: str = Field(min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=30)
    status: str = Field(default="ACTIVE", pattern="^(ACTIVE|SUSPENDED)$")
    permissionCodes: list[str] = Field(default_factory=list)

class UserPermissionsPayload(BaseModel):
    permissionCodes: list[str] = Field(default_factory=list)
