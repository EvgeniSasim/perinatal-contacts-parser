from datetime import datetime

from pydantic import BaseModel, Field


class InstitutionOut(BaseModel):
    id: str
    name: str
    type: str
    region: str
    city: str
    address: str
    phones: list[str] = Field(default_factory=list)
    emails: list[str] = Field(default_factory=list)
    website: str | None = None
    chief_physician: str | None = None
    pathology_head: str | None = None
    nmic_ref: str | None = None
    source_url: str
    verification_status: str
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class InstitutionListOut(BaseModel):
    items: list[InstitutionOut]
    total: int
    page: int
    page_size: int


class InstitutionCreate(BaseModel):
    name: str
    type: str
    region: str
    city: str
    address: str
    phones: list[str] = Field(default_factory=list)
    emails: list[str] = Field(default_factory=list)
    website: str | None = None
    chief_physician: str | None = None
    pathology_head: str | None = None
    nmic_ref: str | None = None
    source_url: str
    verification_status: str = "pending"


class InstitutionUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    region: str | None = None
    city: str | None = None
    address: str | None = None
    phones: list[str] | None = None
    emails: list[str] | None = None
    website: str | None = None
    chief_physician: str | None = None
    pathology_head: str | None = None
    nmic_ref: str | None = None
    source_url: str | None = None
    verification_status: str | None = None


class ExportRequest(BaseModel):
    q: str | None = None
    type: str | None = None
    region: str | None = None
    city: str | None = None
    has_email: bool | None = None
    has_phone: bool | None = None
    has_chief: bool | None = None
    nmic_ref: str | None = None


class MailingRequest(BaseModel):
    subject: str
    body_html: str
    dry_run: bool = True
    filter: ExportRequest = Field(default_factory=ExportRequest)


class CrawlRequest(BaseModel):
    source: str = "all_free"
    url: str | None = None
    cities: list[str] | None = None


class EnrichRequest(BaseModel):
    limit: int = Field(default=25, ge=1, le=500)
    only_missing_chief: bool = True
    region: str | None = None
    type: str | None = None
    with_site_only: bool = False
    without_site_only: bool = False
    force: bool = False


class PersonOut(BaseModel):
    id: str
    institution_id: str
    full_name: str
    role: str
    position_raw: str | None = None
    department: str | None = None
    phone: str | None = None
    email: str | None = None
    confidence: str
    source_url: str
    verified_manually: bool

    model_config = {"from_attributes": True}


class PersonListOut(BaseModel):
    items: list[PersonOut]
    total: int


class PersonUpdate(BaseModel):
    full_name: str | None = None
    role: str | None = None
    position_raw: str | None = None
    department: str | None = None
    phone: str | None = None
    email: str | None = None
    confidence: str | None = None
    verified_manually: bool | None = None


class CompletenessOut(BaseModel):
    total: int
    fields: dict[str, dict[str, float | int]]
    by_type: list[dict]
    persons: dict[str, int]
    attempts: dict[str, int]


class JobOut(BaseModel):
    id: str
    kind: str
    status: str
    payload_json: dict
    result_json: dict
    error: str | None = None

    model_config = {"from_attributes": True}


class MailCampaignOut(BaseModel):
    id: str
    subject: str
    dry_run: bool
    status: str
    sent_count: int
    skipped_count: int
    filter_json: dict

    model_config = {"from_attributes": True}


TYPE_LABELS = {
    "perinatal_center": "Перинатальный центр",
    "perinatal_center_regional": "Областной перинатальный центр",
    "perinatal_center_city": "Городской клинический перинатальный центр",
    "womens_clinic": "Женская консультация",
    "maternity_hospital": "Родильный дом",
    "obgyn_clinic": "Клиника акушерства и гинекологии",
    "obgyn_chair": "Кафедра акушерства и гинекологии",
    "nmic": "НМИЦ акушерства и гинекологии",
}
