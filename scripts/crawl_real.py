#!/usr/bin/env python3
"""CLI: crawl real public sources into DB / refresh seed CSV from OSM."""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))
os.chdir(ROOT)

from app.config import get_settings
from app.db import SessionLocal, init_db
from app.services.crawl_runner import run_crawl
from app.services.collectors.osm_nominatim import collect_nominatim
from app.services.collectors.site_registry import collect_site_registry


def export_csv(rows: list[dict], path: Path) -> None:
    fields = [
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
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(
                {
                    **{k: r.get(k) or "" for k in fields if k not in {"phones", "emails"}},
                    "phones": ";".join(r.get("phones") or []),
                    "emails": ";".join(r.get("emails") or []),
                }
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Crawl perinatal contacts sources")
    parser.add_argument(
        "--source",
        default="all_free",
        choices=[
            "seed_csv",
            "osm",
            "sites",
            "catalogs",
            "orgpage",
            "medadvisor",
            "kp",
            "zdrav",
            "russiamedtravel",
            "vademec",
            "murman_pdf",
            "2gis",
            "yandex",
            "all_free",
            "all",
            "refresh_seed",
        ],
    )
    parser.add_argument("--cities", nargs="*", default=None)
    args = parser.parse_args()
    get_settings.cache_clear()
    init_db()

    if args.source == "refresh_seed":
        rows = collect_site_registry(get_settings().sites_registry_path)
        rows.extend(collect_nominatim(include_cities=True, cities=args.cities))
        # dedupe by name+city
        seen: set[str] = set()
        uniq = []
        for r in rows:
            key = f"{(r['name'] or '').lower()}|{(r['city'] or '').lower()}"
            if key in seen:
                continue
            seen.add(key)
            uniq.append(r)
        out = Path(get_settings().seed_csv_path)
        export_csv(uniq, out)
        print(f"refresh_seed: {len(uniq)} rows -> {out}")
        return

    db = SessionLocal()
    try:
        result = run_crawl(db, args.source, cities=args.cities)
        print(result)
    finally:
        db.close()


if __name__ == "__main__":
    main()
