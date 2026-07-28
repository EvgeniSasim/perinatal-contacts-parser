import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
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
    export = "export"
    mailing = "mailing"


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
