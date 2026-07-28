from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_admin_api_key
from app.models import Institution, InstitutionPerson, Job, MailCampaign
from app.schemas import (
    CompletenessOut,
    CrawlRequest,
    EnrichRequest,
    ExportRequest,
    InstitutionCreate,
    InstitutionOut,
    InstitutionUpdate,
    JobOut,
    MailCampaignOut,
    MailingRequest,
    PersonListOut,
    PersonOut,
    PersonUpdate,
)
from app.services.collectors.html_generic import fetch_and_parse
from app.services.collectors.person_extractor import normalize_person_name
from app.services.crawl_runner import run_crawl
from app.services.enrich import run_enrichment
from app.services.export import run_export_job
from app.services.mailing import preview_mailing, run_mailing
from app.services.metrics import build_completeness
from app.services.normalize import normalize_email, normalize_name, normalize_phone
from app.services.query import to_out
from app.services.seed import upsert_institution

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin_api_key)])


@router.post("/institutions", response_model=InstitutionOut, status_code=201)
def create_institution(body: InstitutionCreate, db: Session = Depends(get_db)) -> InstitutionOut:
    row = upsert_institution(
        db,
        {
            "name": body.name,
            "type": body.type,
            "region": body.region,
            "city": body.city,
            "address": body.address,
            "phones": body.phones,
            "emails": body.emails,
            "website": body.website,
            "chief_physician": body.chief_physician,
            "pathology_head": body.pathology_head,
            "nmic_ref": body.nmic_ref,
            "source_url": body.source_url,
            "verification_status": body.verification_status,
        },
    )
    db.commit()
    db.refresh(row)
    return to_out(row)


@router.patch("/institutions/{institution_id}", response_model=InstitutionOut)
def update_institution(
    institution_id: str, body: InstitutionUpdate, db: Session = Depends(get_db)
) -> InstitutionOut:
    row = db.get(Institution, institution_id)
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    data = body.model_dump(exclude_unset=True)
    if "phones" in data and data["phones"] is not None:
        row.phones_json = data.pop("phones")
        norms = [normalize_phone(p) for p in row.phones_json]
        row.phone_primary_norm = next((p for p in norms if p), None)
    if "emails" in data and data["emails"] is not None:
        row.emails_json = [e for e in (normalize_email(x) for x in data.pop("emails")) if e]
    if "name" in data and data["name"]:
        row.name = data["name"]
        row.name_norm = normalize_name(data["name"])
        data.pop("name")
    for key, value in data.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return to_out(row)


@router.delete("/institutions/{institution_id}", status_code=204)
def delete_institution(institution_id: str, db: Session = Depends(get_db)) -> None:
    row = db.get(Institution, institution_id)
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    row.verification_status = "rejected"
    db.commit()


@router.post("/jobs/crawl", response_model=JobOut, status_code=202)
def crawl(body: CrawlRequest, db: Session = Depends(get_db)) -> JobOut:
    job = Job(kind="crawl", status="queued", payload_json=body.model_dump())
    db.add(job)
    db.commit()
    db.refresh(job)
    job.status = "running"
    db.commit()
    try:
        if body.source == "html" and body.url:
            parsed = fetch_and_parse(body.url)
            job.result_json = {"parsed": parsed}
        else:
            job.result_json = run_crawl(db, body.source, cities=body.cities)
        job.status = "done"
    except Exception as exc:  # noqa: BLE001
        job.status = "failed"
        job.error = str(exc)
    db.commit()
    db.refresh(job)
    return JobOut.model_validate(job)


@router.post("/jobs/enrich", response_model=JobOut, status_code=202)
def enrich(body: EnrichRequest, db: Session = Depends(get_db)) -> JobOut:
    job = Job(kind="enrich", status="queued", payload_json=body.model_dump())
    db.add(job)
    db.commit()
    db.refresh(job)
    job.status = "running"
    db.commit()
    try:
        job.result_json = run_enrichment(
            db,
            limit=body.limit,
            only_missing_chief=body.only_missing_chief,
            region=body.region,
            type_=body.type,
            with_site_only=body.with_site_only,
            without_site_only=body.without_site_only,
            force=body.force,
        )
        job.status = "done"
    except Exception as exc:  # noqa: BLE001
        job.status = "failed"
        job.error = str(exc)
    db.commit()
    db.refresh(job)
    return JobOut.model_validate(job)


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: str, db: Session = Depends(get_db)) -> JobOut:
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Not found")
    return JobOut.model_validate(job)


@router.get("/persons", response_model=PersonListOut)
def list_persons(
    institution_id: str | None = None,
    role: str | None = None,
    confidence: str | None = None,
    unverified_only: bool = False,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> PersonListOut:
    stmt = select(InstitutionPerson)
    if institution_id:
        stmt = stmt.where(InstitutionPerson.institution_id == institution_id)
    if role:
        stmt = stmt.where(InstitutionPerson.role == role)
    if confidence:
        stmt = stmt.where(InstitutionPerson.confidence == confidence)
    if unverified_only:
        stmt = stmt.where(InstitutionPerson.verified_manually.is_(False))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(InstitutionPerson.updated_at.desc()).limit(min(limit, 500))).all()
    return PersonListOut(items=[PersonOut.model_validate(r) for r in rows], total=total)


@router.patch("/persons/{person_id}", response_model=PersonOut)
def update_person(person_id: str, body: PersonUpdate, db: Session = Depends(get_db)) -> PersonOut:
    person = db.get(InstitutionPerson, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Not found")
    data = body.model_dump(exclude_unset=True)
    if data.get("full_name"):
        person.full_name_norm = normalize_person_name(data["full_name"])
    for key, value in data.items():
        setattr(person, key, value)
    # ручная правка сразу поднимает достоверность и защищает от перезаписи парсером
    if body.verified_manually:
        person.confidence = "high"
    db.commit()
    db.refresh(person)
    _sync_institution_fields(db, person.institution_id)
    return PersonOut.model_validate(person)


@router.delete("/persons/{person_id}", status_code=204)
def delete_person(person_id: str, db: Session = Depends(get_db)) -> None:
    person = db.get(InstitutionPerson, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Not found")
    institution_id = person.institution_id
    db.delete(person)
    db.commit()
    _sync_institution_fields(db, institution_id)


def _sync_institution_fields(db: Session, institution_id: str) -> None:
    """Пересчитать chief_physician / pathology_head после правок персон."""
    inst = db.get(Institution, institution_id)
    if not inst:
        return
    persons = db.scalars(
        select(InstitutionPerson).where(InstitutionPerson.institution_id == institution_id)
    ).all()
    for field, role in (("chief_physician", "chief"), ("pathology_head", "pathology_head")):
        candidates = sorted(
            (p for p in persons if p.role == role and p.confidence in {"high", "medium"}),
            key=lambda p: (0 if p.verified_manually else 1, 0 if p.confidence == "high" else 1),
        )
        setattr(inst, field, candidates[0].full_name if candidates else None)
    db.commit()


@router.get("/metrics/completeness", response_model=CompletenessOut)
def completeness(db: Session = Depends(get_db)) -> CompletenessOut:
    return CompletenessOut(**build_completeness(db))


@router.post("/export", response_model=JobOut, status_code=202)
def export_excel(body: ExportRequest, db: Session = Depends(get_db)) -> JobOut:
    job = Job(kind="export", status="queued", payload_json=body.model_dump())
    db.add(job)
    db.commit()
    db.refresh(job)
    run_export_job(db, job)
    db.refresh(job)
    return JobOut.model_validate(job)


@router.get("/export/{job_id}", response_model=JobOut)
def export_status(job_id: str, db: Session = Depends(get_db)) -> JobOut:
    job = db.get(Job, job_id)
    if not job or job.kind != "export":
        raise HTTPException(status_code=404, detail="Not found")
    return JobOut.model_validate(job)


@router.get("/export/{job_id}/file")
def export_file(job_id: str, db: Session = Depends(get_db)) -> FileResponse:
    job = db.get(Job, job_id)
    if not job or job.kind != "export" or job.status != "done":
        raise HTTPException(status_code=404, detail="Not found")
    path = Path((job.result_json or {}).get("path", ""))
    if not path.is_file():
        raise HTTPException(status_code=404, detail="File missing")
    return FileResponse(
        path,
        filename=path.name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.post("/mailings", response_model=MailCampaignOut, status_code=202)
def create_mailing(body: MailingRequest, db: Session = Depends(get_db)) -> MailCampaignOut:
    campaign = MailCampaign(
        subject=body.subject,
        body_html=body.body_html,
        dry_run=body.dry_run,
        filter_json=body.filter.model_dump(),
        status="queued",
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    run_mailing(db, campaign)
    db.refresh(campaign)
    return MailCampaignOut.model_validate(campaign)


@router.post("/mailings/preview")
def preview(body: MailingRequest, db: Session = Depends(get_db)) -> dict:
    return preview_mailing(db, body.subject, body.body_html, body.filter.model_dump())


@router.get("/mailings/{campaign_id}", response_model=MailCampaignOut)
def get_mailing(campaign_id: str, db: Session = Depends(get_db)) -> MailCampaignOut:
    campaign = db.get(MailCampaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Not found")
    return MailCampaignOut.model_validate(campaign)
