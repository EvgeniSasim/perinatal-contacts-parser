from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.services.collectors.dgis import collect_2gis
from app.services.collectors.osm_nominatim import collect_nominatim
from app.services.collectors.site_registry import collect_site_registry
from app.services.collectors.yandex_maps import collect_yandex
from app.services.seed import load_seed_csv, upsert_institution


def persist_rows(db: Session, rows: list[dict[str, Any]]) -> int:
    for row in rows:
        upsert_institution(db, row)
    db.commit()
    return len(rows)


def run_crawl(db: Session, source: str, *, cities: list[str] | None = None) -> dict[str, Any]:
    settings = get_settings()
    if source == "seed_csv":
        count = load_seed_csv(db, settings.seed_csv_path)
        return {"source": source, "loaded": count}

    if source == "osm":
        rows = collect_nominatim(include_cities=True, cities=cities)
        return {"source": source, "loaded": persist_rows(db, rows)}

    if source == "sites":
        rows = collect_site_registry(settings.sites_registry_path)
        return {"source": source, "loaded": persist_rows(db, rows)}

    if source == "2gis":
        rows = collect_2gis(cities=cities)
        return {"source": source, "loaded": persist_rows(db, rows)}

    if source == "yandex":
        rows = collect_yandex(cities=cities)
        return {"source": source, "loaded": persist_rows(db, rows)}

    if source == "all_free":
        # Без коммерческих ключей: seed + OSM + официальные сайты
        summary: dict[str, Any] = {"source": source, "parts": []}
        for part in ("seed_csv", "osm", "sites"):
            summary["parts"].append(run_crawl(db, part, cities=cities))
        summary["loaded"] = sum(p.get("loaded", 0) for p in summary["parts"])
        return summary

    if source == "all":
        summary = {"source": source, "parts": []}
        for part in ("seed_csv", "osm", "sites", "2gis", "yandex"):
            try:
                summary["parts"].append(run_crawl(db, part, cities=cities))
            except Exception as exc:  # noqa: BLE001
                summary["parts"].append({"source": part, "error": str(exc), "loaded": 0})
        summary["loaded"] = sum(p.get("loaded", 0) for p in summary["parts"])
        return summary

    raise ValueError(f"Unknown crawl source: {source}")
