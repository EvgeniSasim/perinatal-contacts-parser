from collections.abc import Sequence

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.orm import Session

from app.models import Institution
from app.schemas import InstitutionOut


def to_out(row: Institution) -> InstitutionOut:
    return InstitutionOut(
        id=row.id,
        name=row.name,
        type=row.type,
        region=row.region,
        city=row.city,
        address=row.address,
        phones=list(row.phones_json or []),
        emails=list(row.emails_json or []),
        website=row.website,
        chief_physician=row.chief_physician,
        pathology_head=row.pathology_head,
        nmic_ref=row.nmic_ref,
        source_url=row.source_url,
        verification_status=row.verification_status,
        updated_at=row.updated_at,
    )


def build_institutions_query(
    *,
    q: str | None = None,
    type: str | None = None,
    region: str | None = None,
    city: str | None = None,
    has_email: bool | None = None,
    has_phone: bool | None = None,
    nmic_ref: str | None = None,
    include_rejected: bool = False,
) -> Select[tuple[Institution]]:
    stmt = select(Institution)
    filters = []
    if not include_rejected:
        filters.append(Institution.verification_status != "rejected")
    if type:
        filters.append(Institution.type == type)
    if region:
        filters.append(Institution.region == region)
    if city:
        filters.append(Institution.city == city)
    if nmic_ref:
        filters.append(Institution.nmic_ref.ilike(f"%{nmic_ref}%"))
    if q:
        like = f"%{q}%"
        filters.append(
            or_(
                Institution.name.ilike(like),
                Institution.address.ilike(like),
                Institution.city.ilike(like),
                Institution.region.ilike(like),
                Institution.chief_physician.ilike(like),
            )
        )
    if has_email is True:
        filters.append(func.json_array_length(Institution.emails_json) > 0)
    if has_phone is True:
        filters.append(func.json_array_length(Institution.phones_json) > 0)
    # SQLite fallback: json_array_length may not exist — handled in query_institutions
    if filters:
        stmt = stmt.where(and_(*filters))
    return stmt


def _sqlite_safe_filter(rows: Sequence[Institution], has_email: bool | None, has_phone: bool | None) -> list[Institution]:
    result = list(rows)
    if has_email is True:
        result = [r for r in result if r.emails_json]
    if has_phone is True:
        result = [r for r in result if r.phones_json]
    return result


def query_institutions(
    db: Session,
    *,
    q: str | None = None,
    type: str | None = None,
    region: str | None = None,
    city: str | None = None,
    has_email: bool | None = None,
    has_phone: bool | None = None,
    nmic_ref: str | None = None,
    page: int = 1,
    page_size: int = 20,
    sort: str = "name",
    include_rejected: bool = False,
) -> tuple[list[Institution], int]:
    # Avoid dialect-specific JSON length in SQL for portability (sqlite tests)
    stmt = build_institutions_query(
        q=q,
        type=type,
        region=region,
        city=city,
        has_email=None,
        has_phone=None,
        nmic_ref=nmic_ref,
        include_rejected=include_rejected,
    )
    sort_map = {
        "name": Institution.name,
        "region": Institution.region,
        "updated_at": Institution.updated_at,
    }
    stmt = stmt.order_by(sort_map.get(sort, Institution.name))
    rows = list(db.scalars(stmt).all())
    rows = _sqlite_safe_filter(rows, has_email, has_phone)
    total = len(rows)
    start = max(page - 1, 0) * page_size
    return rows[start : start + page_size], total
