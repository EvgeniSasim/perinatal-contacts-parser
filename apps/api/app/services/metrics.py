"""Метрики полноты данных для админки и отчётов QA."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import CrawlAttempt, Institution, InstitutionPerson
from app.schemas import TYPE_LABELS

TRACKED_FIELDS = ("address", "website", "chief_physician", "pathology_head", "nmic_ref")


def _pct(part: int, total: int) -> float:
    return round(part * 100 / total, 1) if total else 0.0


def build_completeness(db: Session) -> dict[str, Any]:
    rows = list(db.scalars(select(Institution).where(Institution.verification_status != "rejected")))
    total = len(rows)

    fields: dict[str, dict[str, float | int]] = {}
    for name in TRACKED_FIELDS:
        filled = sum(1 for r in rows if (getattr(r, name) or "").strip() not in {"", "—"})
        fields[name] = {"filled": filled, "pct": _pct(filled, total)}
    for name, attr in (("phones", "phones_json"), ("emails", "emails_json")):
        filled = sum(1 for r in rows if getattr(r, attr))
        fields[name] = {"filled": filled, "pct": _pct(filled, total)}

    by_type: list[dict[str, Any]] = []
    for code, label in TYPE_LABELS.items():
        subset = [r for r in rows if r.type == code]
        if not subset:
            continue
        by_type.append(
            {
                "type": code,
                "label": label,
                "total": len(subset),
                "chief_pct": _pct(sum(1 for r in subset if r.chief_physician), len(subset)),
                "email_pct": _pct(sum(1 for r in subset if r.emails_json), len(subset)),
                "phone_pct": _pct(sum(1 for r in subset if r.phones_json), len(subset)),
                "site_pct": _pct(sum(1 for r in subset if r.website), len(subset)),
            }
        )
    by_type.sort(key=lambda item: -item["total"])

    person_counts = dict(
        db.execute(select(InstitutionPerson.role, func.count()).group_by(InstitutionPerson.role)).all()
    )
    person_counts["total"] = sum(person_counts.values())
    person_counts["unverified"] = (
        db.scalar(
            select(func.count())
            .select_from(InstitutionPerson)
            .where(InstitutionPerson.verified_manually.is_(False))
        )
        or 0
    )
    person_counts["high_confidence"] = (
        db.scalar(
            select(func.count())
            .select_from(InstitutionPerson)
            .where(InstitutionPerson.confidence == "high")
        )
        or 0
    )

    attempts = dict(
        db.execute(select(CrawlAttempt.status, func.count()).group_by(CrawlAttempt.status)).all()
    )

    return {
        "total": total,
        "fields": fields,
        "by_type": by_type,
        "persons": {k: int(v) for k, v in person_counts.items()},
        "attempts": {k: int(v) for k, v in attempts.items()},
    }
