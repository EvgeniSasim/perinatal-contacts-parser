import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db import Base


class InstitutionType(str, enum.Enum):
    perinatal_center = "perinatal_center"
    perinatal_center_regional = "perinatal_center_regional"
    perinatal_center_city = "perinatal_center_city"
    womens_clinic = "womens_clinic"
    maternity_hospital = "maternity_hospital"
    obgyn_clinic = "obgyn_clinic"
    obgyn_chair = "obgyn_chair"
    nmic = "nmic"


class VerificationStatus(str, enum.Enum):
    pending = "pending"
    verified = "verified"
    rejected = "rejected"


class JobKind(str, enum.Enum):
    crawl = "crawl"
    enrich = "enrich"
    export = "export"
    mailing = "mailing"


class PersonRole(str, enum.Enum):
    chief = "chief"
    deputy = "deputy"
    pathology_head = "pathology_head"
    head = "head"
    other = "other"


class Confidence(str, enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"


CONFIDENCE_RANK = {"low": 1, "medium": 2, "high": 3}


class CrawlStage(str, enum.Enum):
    site_discovery = "site_discovery"
    page_finder = "page_finder"
    person_extract = "person_extract"
    email_extract = "email_extract"


class JobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    done = "done"
    failed = "failed"


class Institution(Base):
    __tablename__ = "institutions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    city: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    website: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    chief_physician: Mapped[str | None] = mapped_column(String(256), nullable=True)
    pathology_head: Mapped[str | None] = mapped_column(String(256), nullable=True)
    nmic_ref: Mapped[str | None] = mapped_column(String(256), nullable=True)
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    phones_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    emails_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    name_norm: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    phone_primary_norm: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class InstitutionPerson(Base):
    __tablename__ = "institution_persons"
    __table_args__ = (
        UniqueConstraint("institution_id", "full_name_norm", "role", name="uq_person_inst_name_role"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    full_name: Mapped[str] = mapped_column(String(256), nullable=False)
    full_name_norm: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    position_raw: Mapped[str | None] = mapped_column(String(512), nullable=True)
    department: Mapped[str | None] = mapped_column(String(256), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    email: Mapped[str | None] = mapped_column(String(256), nullable=True)
    confidence: Mapped[str] = mapped_column(String(16), nullable=False, default="low", index=True)
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    verified_manually: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CrawlAttempt(Base):
    __tablename__ = "crawl_attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    stage: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    found_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    result_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MailCampaign(Base):
    __tablename__ = "mail_campaigns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    subject: Mapped[str] = mapped_column(String(512), nullable=False)
    body_html: Mapped[str] = mapped_column(Text, nullable=False)
    filter_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    sent_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
