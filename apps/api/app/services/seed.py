import csv
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Institution
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
