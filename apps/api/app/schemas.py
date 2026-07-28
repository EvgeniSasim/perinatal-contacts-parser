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
    nmic_ref: str | None = None


class MailingRequest(BaseModel):
    subject: str
    body_html: str
    dry_run: bool = True
    filter: ExportRequest = Field(default_factory=ExportRequest)


class CrawlRequest(BaseModel):
    source: str = "seed_csv"
    url: str | None = None


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
