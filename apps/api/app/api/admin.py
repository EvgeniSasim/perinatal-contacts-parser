from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_admin_api_key
from app.models import Institution, Job, MailCampaign
from app.schemas import (
    CrawlRequest,
    ExportRequest,
    InstitutionCreate,
    InstitutionOut,
    InstitutionUpdate,
    JobOut,
    MailCampaignOut,
    MailingRequest,
)
from app.services.collectors.html_generic import fetch_and_parse
from app.services.crawl_runner import run_crawl
from app.services.export import run_export_job
from app.services.mailing import run_mailing
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


@router.get("/mailings/{campaign_id}", response_model=MailCampaignOut)
def get_mailing(campaign_id: str, db: Session = Depends(get_db)) -> MailCampaignOut:
    campaign = db.get(MailCampaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Not found")
    return MailCampaignOut.model_validate(campaign)
