import uuid
from datetime import date
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field

from app.security.rbac import PORTALS, ROLES

Status = Literal["active", "inactive"]
Role = Literal[tuple(ROLES)]  # type: ignore[valid-type]
Portal = Literal[tuple(PORTALS)]  # type: ignore[valid-type]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginIn(BaseModel):
    # Emp ID (e.g. AHFL01810) or email. "email" is accepted as an alias for older clients.
    identifier: str = Field(min_length=1, max_length=200, validation_alias=AliasChoices("identifier", "email"))
    password: str = Field(min_length=1, max_length=200)
    portal: Portal


class RefreshIn(BaseModel):
    refresh_token: str


class ChangePasswordIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=8, max_length=200)


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str
    portal: str
    must_change_password: bool = False


class UserOut(ORM):
    id: uuid.UUID
    company_id: uuid.UUID
    branch_id: uuid.UUID | None
    cluster_id: uuid.UUID | None
    region_id: uuid.UUID | None
    employee_code: str
    full_name: str
    email: str | None
    phone: str | None
    role: str
    designation: str | None
    spoke: str | None
    joining_date: date | None
    exit_date: date | None
    must_change_password: bool
    status: str


class MeOut(UserOut):
    role_label: str = ""
    portal: str = ""
    permissions: list[str] = []
    branch_ids: list[uuid.UUID] = []
    branch_name: str | None = None
    cluster_name: str | None = None
    region_name: str | None = None
    company_name: str | None = None


class CompanyOut(ORM):
    id: uuid.UUID
    name: str
    code: str
    contact_email: str | None
    contact_phone: str | None
    address: str | None
    timezone: str
    status: str


class CompanyPatch(BaseModel):
    name: str | None = Field(None, max_length=200)
    contact_email: str | None = None
    contact_phone: str | None = None
    address: str | None = None


class RegionIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=1, max_length=50)


class RegionPatch(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    code: str | None = Field(None, min_length=1, max_length=50)
    status: Status | None = None


class RegionOut(ORM):
    id: uuid.UUID
    name: str
    code: str
    status: str


class ClusterIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=1, max_length=50)
    region_id: uuid.UUID


class ClusterPatch(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    code: str | None = Field(None, min_length=1, max_length=50)
    region_id: uuid.UUID | None = None
    status: Status | None = None


class ClusterOut(ORM):
    id: uuid.UUID
    region_id: uuid.UUID
    name: str
    code: str
    status: str


class BranchIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=1, max_length=50)
    region_id: uuid.UUID | None = None
    cluster_id: uuid.UUID | None = None
    address: str | None = Field(None, max_length=500)
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)


class BranchPatch(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    code: str | None = Field(None, min_length=1, max_length=50)  # the seeded codes are placeholders
    region_id: uuid.UUID | None = None
    cluster_id: uuid.UUID | None = None
    address: str | None = Field(None, max_length=500)
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    status: Status | None = None


class BranchOut(ORM):
    id: uuid.UUID
    region_id: uuid.UUID | None
    cluster_id: uuid.UUID | None
    name: str
    code: str
    address: str | None
    latitude: float | None
    longitude: float | None
    status: str


class EmployeeIn(BaseModel):
    employee_code: str = Field(min_length=1, max_length=50)
    full_name: str = Field(min_length=1, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=30)
    role: Role = "sales_officer"
    designation: str | None = Field(None, max_length=50)
    branch_id: uuid.UUID | None = None
    cluster_id: uuid.UUID | None = None
    region_id: uuid.UUID | None = None
    branch_ids: list[uuid.UUID] = []
    spoke: str | None = Field(None, max_length=100)
    joining_date: date | None = None
    exit_date: date | None = None


class EmployeePatch(BaseModel):
    full_name: str | None = Field(None, min_length=1, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=30)
    role: Role | None = None
    designation: str | None = Field(None, max_length=50)
    branch_id: uuid.UUID | None = None
    cluster_id: uuid.UUID | None = None
    region_id: uuid.UUID | None = None
    branch_ids: list[uuid.UUID] | None = None
    spoke: str | None = Field(None, max_length=100)
    joining_date: date | None = None
    exit_date: date | None = None
    status: Status | None = None


class Page(BaseModel):
    items: list
    total: int
    page: int
    page_size: int
