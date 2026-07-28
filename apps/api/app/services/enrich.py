"""Оркестратор обогащения: сайт → страницы → персоны и email.

Каждый шаг пишет запись в crawl_attempts, чтобы было видно, где именно данные теряются
и чтобы не долбить повторно мёртвые домены.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import CONFIDENCE_RANK, CrawlAttempt, Institution, InstitutionPerson
from app.services.collectors.page_finder import find_pages, normalize_site_url
from app.services.collectors.person_extractor import (
    ExtractedPerson,
    extract_persons,
    normalize_person_name,
    pick_field_values,
)
from app.services.collectors.site_discovery import discover_site, verify_site
from app.services.normalize import normalize_email, normalize_phone

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
EMAIL_JUNK = re.compile(r"(example|sentry|\.png|\.jpg|\.gif|webmaster@|no-?reply|domain\.)", re.I)
RETRY_AFTER_DAYS = 7


def _log(
    db: Session,
    *,
    institution_id: str | None,
    stage: str,
    status: str,
    url: str | None = None,
    http_status: int | None = None,
    detail: str | None = None,
    found_count: int = 0,
) -> None:
    db.add(
        CrawlAttempt(
            institution_id=institution_id,
            stage=stage,
            status=status,
            url=url,
            http_status=http_status,
            detail=(detail or "")[:2000] or None,
            found_count=found_count,
        )
    )


def _attempt_status(page_error: str | None) -> str:
    if page_error == "blocked_by_robots":
        return "blocked"
    if page_error in {"timeout", "ssl_error", "dns_error", "refused", "network_error"}:
        return "timeout" if page_error == "timeout" else "http_error"
    return "not_found"


def _recently_failed(db: Session, institution_id: str) -> bool:
    """Домен уже недавно оказался недоступен — повторный обход бессмысленен.

    Проверяются оба «сетевых» шага: учреждение может иметь валидный сайт в БД
    (site_discovery проходит), но сам домен не отвечать — тогда провал будет на page_finder.
    """
    since = datetime.now(timezone.utc) - timedelta(days=RETRY_AFTER_DAYS)
    stmt = (
        select(func.count())
        .select_from(CrawlAttempt)
        .where(
            CrawlAttempt.institution_id == institution_id,
            CrawlAttempt.stage.in_(("site_discovery", "page_finder")),
            CrawlAttempt.status.in_(("not_found", "timeout", "blocked", "http_error")),
            CrawlAttempt.created_at >= since,
        )
    )
    return bool(db.execute(stmt).scalar_one())


def upsert_person(db: Session, institution_id: str, person: ExtractedPerson) -> bool:
    """Записать персону. Возвращает True, если создана или обновлена."""
    name_norm = normalize_person_name(person.full_name)
    existing = db.execute(
        select(InstitutionPerson).where(
            InstitutionPerson.institution_id == institution_id,
            InstitutionPerson.full_name_norm == name_norm,
            InstitutionPerson.role == person.role,
        )
    ).scalar_one_or_none()

    if existing is None:
        db.add(
            InstitutionPerson(
                institution_id=institution_id,
                full_name=person.full_name,
                full_name_norm=name_norm,
                role=person.role,
                position_raw=person.position_raw,
                department=person.department,
                phone=normalize_phone(person.phone or "") if person.phone else None,
                email=normalize_email(person.email or "") if person.email else None,
                confidence=person.confidence,
                source_url=person.source_url,
            )
        )
        # сессия создана с autoflush=False, поэтому без явного flush одна и та же
        # персона со следующей страницы того же сайта нарушит unique-констрейнт
        db.flush()
        return True

    if existing.verified_manually:
        return False
    if CONFIDENCE_RANK[person.confidence] < CONFIDENCE_RANK[existing.confidence]:
        return False
    existing.full_name = person.full_name
    existing.position_raw = person.position_raw or existing.position_raw
    existing.department = person.department or existing.department
    existing.phone = (normalize_phone(person.phone or "") if person.phone else None) or existing.phone
    existing.email = (normalize_email(person.email or "") if person.email else None) or existing.email
    existing.confidence = person.confidence
    existing.source_url = person.source_url
    return True


def _harvest_emails(html: str) -> list[str]:
    found = []
    for raw in EMAIL_RE.findall(html):
        if EMAIL_JUNK.search(raw):
            continue
        value = normalize_email(raw)
        if value and value not in found:
            found.append(value)
    return found[:5]


def enrich_institution(db: Session, inst: Institution, *, force: bool = False) -> dict[str, Any]:
    """Обогатить одно учреждение. Возвращает сводку по шагам."""
    result: dict[str, Any] = {
        "id": inst.id,
        "name": inst.name,
        "site": None,
        "pages": 0,
        "persons": 0,
        "chief": None,
        "pathology_head": None,
        "emails_added": 0,
        "status": "ok",
    }

    if not force and _recently_failed(db, inst.id):
        result["status"] = "skipped_recent_failure"
        _log(db, institution_id=inst.id, stage="site_discovery", status="skipped", detail="недавняя неудача")
        return result

    discovered = discover_site(inst.name, inst.city, inst.website)
    if discovered is None:
        result["status"] = "site_not_found"
        _log(db, institution_id=inst.id, stage="site_discovery", status="not_found")
        return result

    site = normalize_site_url(discovered.url)
    if site is None:
        result["status"] = "bad_site_url"
        _log(
            db,
            institution_id=inst.id,
            stage="site_discovery",
            status="not_found",
            url=discovered.url,
            detail="не удалось нормализовать URL",
        )
        return result

    if discovered.strategy != "existing":
        ok, http_status, detail = verify_site(site, inst.name, inst.city)
        if not ok:
            result["status"] = "site_unverified"
            _log(
                db,
                institution_id=inst.id,
                stage="site_discovery",
                status="not_found",
                url=site,
                http_status=http_status,
                detail=detail,
            )
            return result
        inst.website = site

    result["site"] = site
    _log(
        db,
        institution_id=inst.id,
        stage="site_discovery",
        status="ok",
        url=site,
        detail=discovered.strategy,
    )

    pages, page_error = find_pages(site)
    result["pages"] = len(pages)
    if not pages:
        result["status"] = f"no_pages:{page_error}" if page_error else "no_pages"
        _log(
            db,
            institution_id=inst.id,
            stage="page_finder",
            status=_attempt_status(page_error),
            url=site,
            detail=page_error,
        )
        return result
    _log(
        db,
        institution_id=inst.id,
        stage="page_finder",
        status="ok",
        url=site,
        found_count=len(pages),
        detail=", ".join(sorted({p.kind for p in pages})),
    )

    all_persons: list[ExtractedPerson] = []
    emails: list[str] = list(inst.emails_json or [])
    emails_before = len(emails)

    for page in pages:
        persons = extract_persons(page.html, page.url, page.kind)
        for person in persons:
            upsert_person(db, inst.id, person)
        all_persons.extend(persons)
        _log(
            db,
            institution_id=inst.id,
            stage="person_extract",
            status="ok" if persons else "not_found",
            url=page.url,
            found_count=len(persons),
            detail=page.kind,
        )
        for email in _harvest_emails(page.html):
            if email not in emails:
                emails.append(email)

    result["persons"] = len(all_persons)
    if len(emails) > emails_before:
        inst.emails_json = emails[:10]
        result["emails_added"] = len(inst.emails_json) - emails_before
    _log(
        db,
        institution_id=inst.id,
        stage="email_extract",
        status="ok" if result["emails_added"] else "not_found",
        url=site,
        found_count=result["emails_added"],
    )

    fields = pick_field_values(all_persons)
    if fields["chief_physician"] and not _is_manually_verified(db, inst.id, "chief"):
        inst.chief_physician = fields["chief_physician"]
    if fields["pathology_head"] and not _is_manually_verified(db, inst.id, "pathology_head"):
        inst.pathology_head = fields["pathology_head"]
    result["chief"] = inst.chief_physician
    result["pathology_head"] = inst.pathology_head
    return result


def _is_manually_verified(db: Session, institution_id: str, role: str) -> bool:
    stmt = (
        select(func.count())
        .select_from(InstitutionPerson)
        .where(
            InstitutionPerson.institution_id == institution_id,
            InstitutionPerson.role == role,
            InstitutionPerson.verified_manually.is_(True),
        )
    )
    return bool(db.execute(stmt).scalar_one())


def run_enrichment(
    db: Session,
    *,
    limit: int = 25,
    only_missing_chief: bool = True,
    region: str | None = None,
    type_: str | None = None,
    with_site_only: bool = False,
    without_site_only: bool = False,
    force: bool = False,
    progress: Callable[[int, int, dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    stmt = select(Institution).where(Institution.verification_status != "rejected")
    if only_missing_chief:
        stmt = stmt.where(Institution.chief_physician.is_(None))
    if region:
        stmt = stmt.where(Institution.region == region)
    if type_:
        stmt = stmt.where(Institution.type == type_)
    if with_site_only:
        stmt = stmt.where(Institution.website.is_not(None), Institution.website != "")
    if without_site_only:
        stmt = stmt.where(or_(Institution.website.is_(None), Institution.website == ""))
    # сначала те, у кого сайт уже известен — там выше отдача
    stmt = stmt.order_by(Institution.website.is_(None), Institution.name).limit(limit)

    institutions = list(db.execute(stmt).scalars())
    items: list[dict[str, Any]] = []
    for index, inst in enumerate(institutions, start=1):
        try:
            item = enrich_institution(db, inst, force=force)
            items.append(item)
        except Exception as exc:  # noqa: BLE001 — одно упавшее учреждение не должно ронять job
            db.rollback()
            item = {"id": inst.id, "name": inst.name, "status": "error", "error": str(exc)[:300]}
            items.append(item)
            _log(db, institution_id=inst.id, stage="person_extract", status="http_error", detail=str(exc)[:300])
        db.commit()
        if progress is not None:
            progress(index, len(institutions), item)

    return {
        "processed": len(items),
        "chief_found": sum(1 for i in items if i.get("chief")),
        "pathology_found": sum(1 for i in items if i.get("pathology_head")),
        "sites_found": sum(1 for i in items if i.get("site")),
        "emails_added": sum(i.get("emails_added", 0) for i in items),
        "persons_total": sum(i.get("persons", 0) for i in items),
        "items": items,
    }
