from datetime import datetime, timezone
from pathlib import Path

from openpyxl import Workbook
from openpyxl.workbook.workbook import Workbook as WorkbookType
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Institution, InstitutionPerson, Job
from app.services.query import query_institutions, to_out

PERSON_HEADERS = [
    "institution_id",
    "institution_name",
    "city",
    "full_name",
    "role",
    "position_raw",
    "department",
    "phone",
    "email",
    "confidence",
    "verified_manually",
    "source_url",
]


def _append_persons_sheet(db: Session, wb: WorkbookType, institution_ids: list[str]) -> None:
    """Второй лист с персонами — то, ради чего затевалось обогащение v0.2."""
    sheet = wb.create_sheet("persons")
    sheet.append(PERSON_HEADERS)
    if not institution_ids:
        return
    names = dict(
        db.execute(
            select(Institution.id, Institution.name).where(Institution.id.in_(institution_ids))
        ).all()
    )
    cities = dict(
        db.execute(
            select(Institution.id, Institution.city).where(Institution.id.in_(institution_ids))
        ).all()
    )
    persons = db.scalars(
        select(InstitutionPerson)
        .where(InstitutionPerson.institution_id.in_(institution_ids))
        .order_by(InstitutionPerson.institution_id, InstitutionPerson.role)
    ).all()
    for person in persons:
        sheet.append(
            [
                person.institution_id,
                names.get(person.institution_id, ""),
                cities.get(person.institution_id, ""),
                person.full_name,
                person.role,
                person.position_raw or "",
                person.department or "",
                person.phone or "",
                person.email or "",
                person.confidence,
                "да" if person.verified_manually else "нет",
                person.source_url,
            ]
        )


def run_export_job(db: Session, job: Job) -> Job:
    job.status = "running"
    db.commit()
    try:
        payload = job.payload_json or {}
        rows, total = query_institutions(
            db,
            q=payload.get("q"),
            type=payload.get("type"),
            region=payload.get("region"),
            city=payload.get("city"),
            has_email=payload.get("has_email"),
            has_phone=payload.get("has_phone"),
            has_chief=payload.get("has_chief"),
            nmic_ref=payload.get("nmic_ref"),
            page=1,
            page_size=100000,
        )
        storage = Path(get_settings().storage_dir) / "exports"
        storage.mkdir(parents=True, exist_ok=True)
        out_path = storage / f"export-{job.id}.xlsx"
        wb = Workbook()
        ws = wb.active
        ws.title = "institutions"
        headers = [
            "id",
            "name",
            "type",
            "region",
            "city",
            "address",
            "phones",
            "emails",
            "website",
            "chief_physician",
            "pathology_head",
            "nmic_ref",
            "source_url",
            "verification_status",
        ]
        ws.append(headers)
        for row in rows:
            item = to_out(row)
            ws.append(
                [
                    item.id,
                    item.name,
                    item.type,
                    item.region,
                    item.city,
                    item.address,
                    "; ".join(item.phones),
                    "; ".join(item.emails),
                    item.website or "",
                    item.chief_physician or "",
                    item.pathology_head or "",
                    item.nmic_ref or "",
                    item.source_url,
                    item.verification_status,
                ]
            )
        _append_persons_sheet(db, wb, [r.id for r in rows])
        wb.save(out_path)
        job.status = "done"
        job.result_json = {"path": str(out_path), "total": total, "download": f"/api/v1/admin/export/{job.id}/file"}
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as exc:  # noqa: BLE001
        job.status = "failed"
        job.error = str(exc)
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
    return job
