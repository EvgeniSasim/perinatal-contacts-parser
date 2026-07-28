#!/usr/bin/env python3
"""CLI: обогащение учреждений ФИО руководства и email с их официальных сайтов.

Примеры:
    python3 scripts/enrich.py --limit 50
    python3 scripts/enrich.py --limit 200 --with-site-only
    python3 scripts/enrich.py --region "Москва" --force
    python3 scripts/enrich.py --report
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))
os.chdir(ROOT)

from app.db import SessionLocal, init_db
from app.services.enrich import run_enrichment
from app.services.metrics import build_completeness


def print_report(db) -> None:
    data = build_completeness(db)
    print(f"Всего записей: {data['total']}")
    print("\nЗаполненность полей:")
    for field, value in data["fields"].items():
        print(f"  {field:20}{value['filled']:5}  {value['pct']:5}%")
    print("\nПо типам:")
    for item in data["by_type"]:
        print(
            f"  {item['label'][:38]:38}{item['total']:5}"
            f"  главврач {item['chief_pct']:5}%  email {item['email_pct']:5}%  сайт {item['site_pct']:5}%"
        )
    print(f"\nПерсоны: {json.dumps(data['persons'], ensure_ascii=False)}")
    print(f"Попытки обхода: {json.dumps(data['attempts'], ensure_ascii=False)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--region")
    parser.add_argument("--type", dest="type_")
    parser.add_argument("--with-site-only", action="store_true", help="только те, у кого уже есть сайт")
    parser.add_argument("--without-site-only", action="store_true", help="только те, у кого сайта нет")
    parser.add_argument("--all", action="store_true", help="включая те, у кого главврач уже известен")
    parser.add_argument("--force", action="store_true", help="игнорировать недавние неудачи")
    parser.add_argument("--report", action="store_true", help="только отчёт, без обогащения")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    init_db()
    with SessionLocal() as db:
        if args.report:
            print_report(db)
            return 0

        def progress(index: int, total: int, item: dict) -> None:
            chief = item.get("chief") or ""
            print(
                f"[{index:4}/{total}] {item['status'][:24]:24} {item['name'][:46]:46} {chief}",
                flush=True,
            )

        summary = run_enrichment(
            db,
            limit=args.limit,
            only_missing_chief=not args.all,
            region=args.region,
            type_=args.type_,
            with_site_only=args.with_site_only,
            without_site_only=args.without_site_only,
            force=args.force,
            progress=progress if args.verbose else None,
        )
        print(
            f"Обработано {summary['processed']}: сайтов {summary['sites_found']}, "
            f"главврачей {summary['chief_found']}, отделений патологии {summary['pathology_found']}, "
            f"персон {summary['persons_total']}, email +{summary['emails_added']}"
        )
        print()
        print_report(db)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
