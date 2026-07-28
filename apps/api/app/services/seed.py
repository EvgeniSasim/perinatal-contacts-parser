import csv
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Institution, InstitutionPerson
from app.services.collectors.person_extractor import normalize_person_name
from app.services.normalize import normalize_email, normalize_name, normalize_phone, split_multi


def upsert_institution(db: Session, data: dict) -> Institution:
    name_norm = normalize_name(data["name"])
    phones = [p for p in (normalize_phone(x) for x in data.get("phones", [])) if p]
    # keep display phones as provided-ish
    display_phones = data.get("phones") or []
    emails = [e for e in (normalize_email(x) for x in data.get("emails", [])) if e]
    phone_primary = phones[0] if phones else None

    existing = db.scalar(
        select(Institution).where(
            Institution.name_norm == name_norm,
            Institution.city == data["city"],
        )
    )
    if existing:
        existing.type = data["type"]
        existing.region = data["region"]
        existing.address = data["address"]
        existing.website = data.get("website") or existing.website
        existing.chief_physician = data.get("chief_physician") or existing.chief_physician
        existing.pathology_head = data.get("pathology_head") or existing.pathology_head
        existing.nmic_ref = data.get("nmic_ref") or existing.nmic_ref
        existing.source_url = data["source_url"]
        existing.verification_status = data.get("verification_status") or existing.verification_status
        existing.phones_json = list(dict.fromkeys([*(existing.phones_json or []), *display_phones]))
        existing.emails_json = list(dict.fromkeys([*(existing.emails_json or []), *emails]))
        existing.phone_primary_norm = phone_primary or existing.phone_primary_norm
        return existing

    row = Institution(
        name=data["name"],
        type=data["type"],
        region=data["region"],
        city=data["city"],
        address=data["address"],
        website=data.get("website") or None,
        chief_physician=data.get("chief_physician") or None,
        pathology_head=data.get("pathology_head") or None,
        nmic_ref=data.get("nmic_ref") or None,
        source_url=data["source_url"],
        verification_status=data.get("verification_status") or "pending",
        phones_json=display_phones,
        emails_json=emails,
        name_norm=name_norm,
        phone_primary_norm=phone_primary,
    )
    db.add(row)
    return row


def load_seed_csv(db: Session, path: str | Path) -> int:
    csv_path = Path(path)
    if not csv_path.is_file():
        raise FileNotFoundError(f"Seed CSV not found: {csv_path}")
    count = 0
    with csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            data = {
                "name": raw["name"].strip(),
                "type": raw["type"].strip(),
                "region": raw["region"].strip(),
                "city": raw["city"].strip(),
                "address": raw["address"].strip(),
                "phones": split_multi(raw.get("phones")),
                "emails": split_multi(raw.get("emails")),
                "website": (raw.get("website") or "").strip() or None,
                "chief_physician": (raw.get("chief_physician") or "").strip() or None,
                "pathology_head": (raw.get("pathology_head") or "").strip() or None,
                "nmic_ref": (raw.get("nmic_ref") or "").strip() or None,
                "source_url": raw["source_url"].strip(),
                "verification_status": (raw.get("verification_status") or "pending").strip(),
            }
            upsert_institution(db, data)
            count += 1
    db.commit()
    return count


def load_persons_csv(db: Session, path: str | Path) -> int:
    """Восстановить `institution_persons` из снапшота.

    Без этого свежий деплой видит только денормализованные `chief_physician` /
    `pathology_head`, но теряет должности, отделения и ссылки на источник.
    """
    csv_path = Path(path)
    if not csv_path.is_file():
        return 0
    by_key = {
        (normalize_name(inst.name), inst.city): inst
        for inst in db.scalars(select(Institution)).all()
    }
    count = 0
    with csv_path.open(encoding="utf-8") as f:
        for raw in csv.DictReader(f):
            inst = by_key.get((normalize_name(raw["institution_name"]), raw["city"].strip()))
            if inst is None:
                continue
            full_name = raw["full_name"].strip()
            name_norm = normalize_person_name(full_name)
            role = raw["role"].strip()
            existing = db.scalar(
                select(InstitutionPerson).where(
                    InstitutionPerson.institution_id == inst.id,
                    InstitutionPerson.full_name_norm == name_norm,
                    InstitutionPerson.role == role,
                )
            )
            if existing is not None:
                continue
            db.add(
                InstitutionPerson(
                    institution_id=inst.id,
                    full_name=full_name,
                    full_name_norm=name_norm,
                    role=role,
                    position_raw=(raw.get("position_raw") or "").strip() or None,
                    department=(raw.get("department") or "").strip() or None,
                    phone=(raw.get("phone") or "").strip() or None,
                    email=(raw.get("email") or "").strip() or None,
                    confidence=(raw.get("confidence") or "low").strip(),
                    source_url=raw["source_url"].strip(),
                    verified_manually=(raw.get("verified_manually") or "").strip() == "да",
                )
            )
            db.flush()
            count += 1
    db.commit()
    return count
