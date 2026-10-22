import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

Status = Literal["active", "inactive"]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class RefreshIn(BaseModel):
    refresh_token: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(ORM):
    id: uuid.UUID
    company_id: uuid.UUID
    organization_id: uuid.UUID | None
    branch_id: uuid.UUID | None
    employee_code: str
    full_name: str
    email: str
    phone: str | None
    role: str
    status: str


class MeOut(UserOut):
    branch_ids: list[uuid.UUID] = []


class CompanyOut(ORM):
    id: uuid.UUID
    name: str
    code: str
    contact_email: str | None
    contact_phone: str | None
    address: str | None
    status: str


class CompanyPatch(BaseModel):
    name: str | None = Field(None, max_length=200)
    contact_email: str | None = None
    contact_phone: str | None = None
    address: str | None = None


class OrganizationIn(BaseModel):
    name: str = Field(max_length=200)
    code: str = Field(max_length=50)


class OrganizationPatch(BaseModel):
    name: str | None = Field(None, max_length=200)
    status: Status | None = None


class OrganizationOut(ORM):
    id: uuid.UUID
    name: str
    code: str
    status: str


class BranchIn(BaseModel):
    name: str = Field(max_length=200)
    code: str = Field(max_length=50)
    organization_id: uuid.UUID | None = None
    address: str | None = Field(None, max_length=500)
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)


class BranchPatch(BaseModel):
    name: str | None = Field(None, max_length=200)
    organization_id: uuid.UUID | None = None
    address: str | None = Field(None, max_length=500)
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    status: Status | None = None


class BranchOut(ORM):
    id: uuid.UUID
    organization_id: uuid.UUID | None
    name: str
    code: str
    address: str | None
    latitude: float | None
    longitude: float | None
    status: str


class EmployeeIn(BaseModel):
    employee_code: str = Field(max_length=50)
    full_name: str = Field(max_length=200)
    email: EmailStr
    phone: str | None = Field(None, max_length=30)
    role: Literal["admin", "agent"] = "agent"
    password: str = Field(min_length=8, max_length=200)
    organization_id: uuid.UUID | None = None
    branch_id: uuid.UUID | None = None
    branch_ids: list[uuid.UUID] = []


class EmployeePatch(BaseModel):
    full_name: str | None = Field(None, max_length=200)
    phone: str | None = Field(None, max_length=30)
    role: Literal["admin", "agent"] | None = None
    password: str | None = Field(None, min_length=8, max_length=200)
    branch_id: uuid.UUID | None = None
    branch_ids: list[uuid.UUID] | None = None
    status: Status | None = None


class Page(BaseModel):
    items: list
    total: int
    page: int
    page_size: int
