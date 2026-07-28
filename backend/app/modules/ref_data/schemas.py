from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


# ── Bloom Domain ──────────────────────────────────────────────────────────────

class BloomDomainCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None


class BloomDomainUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    is_active: bool | None = None


class BloomDomainResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# ── Bloom Level ───────────────────────────────────────────────────────────────

class BloomLevelCreate(BaseModel):
    bloom_domain_id: UUID
    code: str = Field(min_length=1, max_length=10)
    name: str = Field(min_length=1, max_length=100)
    order_index: int = Field(ge=1, le=20)


class BloomLevelUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=10)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    order_index: int | None = Field(default=None, ge=1, le=20)
    is_active: bool | None = None


class BloomLevelResponse(BaseModel):
    id: UUID
    organization_id: UUID
    bloom_domain_id: UUID
    code: str
    name: str
    order_index: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# ── Delivery Method ───────────────────────────────────────────────────────────

class DeliveryMethodCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None


class DeliveryMethodUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    is_active: bool | None = None


class DeliveryMethodResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# ── Course Category ───────────────────────────────────────────────────────────

class CourseCategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None


class CourseCategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    is_active: bool | None = None


class CourseCategoryResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# ── Assessment Type ───────────────────────────────────────────────────────────

class AssessmentTypeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    is_sessional: bool = False


class AssessmentTypeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    is_sessional: bool | None = None
    is_active: bool | None = None


class AssessmentTypeResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    is_sessional: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# ── Complex Problem ───────────────────────────────────────────────────────────

class ComplexProblemCreate(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str | None = Field(default=None, max_length=150)
    description: str = Field(min_length=1)


class ComplexProblemUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=20)
    name: str | None = Field(default=None, max_length=150)
    description: str | None = Field(default=None, min_length=1)
    is_active: bool | None = None


class ComplexProblemResponse(BaseModel):
    id: UUID
    organization_id: UUID
    code: str
    name: str | None
    description: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# ── Complex Activity ──────────────────────────────────────────────────────────

class ComplexActivityCreate(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str | None = Field(default=None, max_length=150)
    description: str = Field(min_length=1)


class ComplexActivityUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=20)
    name: str | None = Field(default=None, max_length=150)
    description: str | None = Field(default=None, min_length=1)
    is_active: bool | None = None


class ComplexActivityResponse(BaseModel):
    id: UUID
    organization_id: UUID
    code: str
    name: str | None
    description: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# ── Knowledge Profile ─────────────────────────────────────────────────────────

class KnowledgeProfileCreate(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    description: str = Field(min_length=1)


class KnowledgeProfileUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=20)
    description: str | None = Field(default=None, min_length=1)
    is_active: bool | None = None


class KnowledgeProfileResponse(BaseModel):
    id: UUID
    organization_id: UUID
    code: str
    description: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# ── PO Type ───────────────────────────────────────────────────────────────────

class POTypeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None)


class POTypeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = Field(default=None)
    is_active: bool | None = None


class POTypeResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# ── Mapping Weight Label ──────────────────────────────────────────────────────

class MappingWeightLabelCreate(BaseModel):
    weight_value: int = Field(ge=1, le=3)
    label: str = Field(min_length=1, max_length=50)


class MappingWeightLabelUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=50)


class MappingWeightLabelResponse(BaseModel):
    id: UUID
    organization_id: UUID
    weight_value: int
    label: str
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# ── Bulk Import ───────────────────────────────────────────────────────────────
# Deliberately permissive: every row is validated in the service so a single bad
# row is reported back as an error instead of rejecting the whole spreadsheet.

class RefDataBulkImportItem(BaseModel):
    code: str = ""
    name: str | None = None
    description: str = ""


class RefDataBulkImportRequest(BaseModel):
    items: list[RefDataBulkImportItem]


class RefDataBulkImportError(BaseModel):
    row: int
    code: str
    message: str


class RefDataBulkImportResponse(BaseModel):
    created: int
    errors: list[RefDataBulkImportError]
