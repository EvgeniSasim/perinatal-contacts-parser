#!/usr/bin/env python3
"""CLI: выгрузка текущего состояния БД в seed-CSV.

Нужен, чтобы результаты обогащения (ФИО, email) не оставались только в локальной БД,
а попадали в репозиторий как воспроизводимый снапшот.

    python3 scripts/dump_seed.py
    python3 scripts/dump_seed.py --out data/seed/institutions.csv --persons data/seed/persons.csv
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))
os.chdir(ROOT)

from sqlalchemy import select

from app.db import SessionLocal, init_db
from app.models import Institution, InstitutionPerson

INSTITUTION_FIELDS = [
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

PERSON_FIELDS = [
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


def dump_institutions(db, path: Path) -> int:
    rows = list(db.scalars(select(Institution).order_by(Institution.name)))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=INSTITUTION_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "name": row.name,
                    "type": row.type,
                    "region": row.region,
                    "city": row.city,
                    "address": row.address,
                    "phones": ";".join(row.phones_json or []),
                    "emails": ";".join(row.emails_json or []),
                    "website": row.website or "",
                    "chief_physician": row.chief_physician or "",
                    "pathology_head": row.pathology_head or "",
                    "nmic_ref": row.nmic_ref or "",
                    "source_url": row.source_url,
                    "verification_status": row.verification_status,
                }
            )
    return len(rows)


def dump_persons(db, path: Path, min_confidence: str = "medium") -> int:
    ranks = {"low": 1, "medium": 2, "high": 3}
    threshold = ranks[min_confidence]
    names = dict(db.execute(select(Institution.id, Institution.name)).all())
    cities = dict(db.execute(select(Institution.id, Institution.city)).all())
    persons = [
        p
        for p in db.scalars(select(InstitutionPerson).order_by(InstitutionPerson.role))
        if ranks[p.confidence] >= threshold
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=PERSON_FIELDS)
        writer.writeheader()
        for person in persons:
            writer.writerow(
                {
                    "institution_name": names.get(person.institution_id, ""),
                    "city": cities.get(person.institution_id, ""),
                    "full_name": person.full_name,
                    "role": person.role,
                    "position_raw": person.position_raw or "",
                    "department": person.department or "",
                    "phone": person.phone or "",
                    "email": person.email or "",
                    "confidence": person.confidence,
                    "verified_manually": "да" if person.verified_manually else "нет",
                    "source_url": person.source_url,
                }
            )
    return len(persons)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default="data/seed/institutions.csv")
    parser.add_argument("--persons", default="data/seed/persons.csv")
    parser.add_argument("--min-confidence", default="medium", choices=["high", "medium", "low"])
    args = parser.parse_args()

    init_db()
    with SessionLocal() as db:
        institutions = dump_institutions(db, Path(args.out))
        persons = dump_persons(db, Path(args.persons), args.min_confidence)
    print(f"Учреждений: {institutions} → {args.out}")
    print(f"Персон ({args.min_confidence}+): {persons} → {args.persons}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
