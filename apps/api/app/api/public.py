from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import CONFIDENCE_RANK, Institution, InstitutionPerson
from app.schemas import (
    TYPE_LABELS,
    InstitutionListOut,
    InstitutionOut,
    PersonListOut,
    PersonOut,
)
from app.services.query import query_institutions, to_out

router = APIRouter(tags=["public"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/meta/types")
def meta_types() -> list[dict]:
    return [{"code": k, "label": v} for k, v in TYPE_LABELS.items()]


@router.get("/meta/regions")
def meta_regions(db: Session = Depends(get_db)) -> list[str]:
    rows = db.scalars(
        select(Institution.region)
        .where(Institution.verification_status != "rejected")
        .distinct()
        .order_by(Institution.region)
    ).all()
    return list(rows)


@router.get("/meta/stats")
def meta_stats(db: Session = Depends(get_db)) -> dict:
    total = db.scalar(
        select(func.count()).select_from(Institution).where(Institution.verification_status != "rejected")
    )
    by_type = db.execute(
        select(Institution.type, func.count())
        .where(Institution.verification_status != "rejected")
        .group_by(Institution.type)
    ).all()
    return {"total": total or 0, "by_type": {t: c for t, c in by_type}}


@router.get("/institutions", response_model=InstitutionListOut)
def list_institutions(
    q: str | None = None,
    type: str | None = None,
    region: str | None = None,
    city: str | None = None,
    has_email: bool | None = None,
    has_phone: bool | None = None,
    has_chief: bool | None = None,
    nmic_ref: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str = Query("name", pattern="^(name|updated_at|region)$"),
    db: Session = Depends(get_db),
) -> InstitutionListOut:
    rows, total = query_institutions(
        db,
        q=q,
        type=type,
        region=region,
        city=city,
        has_email=has_email,
        has_phone=has_phone,
        has_chief=has_chief,
        nmic_ref=nmic_ref,
        page=page,
        page_size=page_size,
        sort=sort,
    )
    return InstitutionListOut(
        items=[to_out(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/institutions/{institution_id}", response_model=InstitutionOut)
def get_institution(institution_id: str, db: Session = Depends(get_db)) -> InstitutionOut:
    row = db.get(Institution, institution_id)
    if not row or row.verification_status == "rejected":
        raise HTTPException(status_code=404, detail="Not found")
    return to_out(row)


@router.get("/institutions/{institution_id}/persons", response_model=PersonListOut)
def get_institution_persons(
    institution_id: str,
    min_confidence: str = Query("medium", pattern="^(high|medium|low)$"),
    db: Session = Depends(get_db),
) -> PersonListOut:
    row = db.get(Institution, institution_id)
    if not row or row.verification_status == "rejected":
        raise HTTPException(status_code=404, detail="Not found")
    threshold = CONFIDENCE_RANK[min_confidence]
    allowed = [c for c, rank in CONFIDENCE_RANK.items() if rank >= threshold]
    persons = db.scalars(
        select(InstitutionPerson)
        .where(
            InstitutionPerson.institution_id == institution_id,
            InstitutionPerson.confidence.in_(allowed),
        )
        .order_by(InstitutionPerson.role, InstitutionPerson.full_name)
    ).all()
    items = [PersonOut.model_validate(p) for p in persons]
    return PersonListOut(items=items, total=len(items))
