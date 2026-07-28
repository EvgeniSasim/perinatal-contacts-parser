"""Добор контактов с официальных сайтов учреждений (allowlist)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from app.services.collectors.base import host_allowed, http_client, rate_sleep, to_institution
from app.services.collectors.html_generic import parse_contacts_html


def load_registry(path: str | Path) -> list[dict[str, Any]]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return list(data.get("institutions") or [])


def collect_site_registry(path: str | Path) -> list[dict[str, Any]]:
    rows = load_registry(path)
    results: list[dict[str, Any]] = []
    with http_client(timeout=25.0) as client:
        for row in rows:
            url = row["source_url"]
            if not host_allowed(url):
                continue
            try:
                resp = client.get(url)
                resp.raise_for_status()
                parsed = parse_contacts_html(resp.text, str(resp.url))
            except Exception:
                rate_sleep()
                continue
            phones = row.get("phones") or parsed.get("phones") or []
            emails = row.get("emails") or parsed.get("emails") or []
            if isinstance(phones, str):
                phones = re.split(r"[;,]", phones)
            if isinstance(emails, str):
                emails = re.split(r"[;,]", emails)
            results.append(
                to_institution(
                    name=row["name"],
                    type_=row.get("type") or "perinatal_center",
                    region=row.get("region") or "",
                    city=row.get("city") or "",
                    address=row.get("address") or parsed.get("address") or "—",
                    phones=phones,
                    emails=emails,
                    website=row.get("website"),
                    chief_physician=row.get("chief_physician"),
                    pathology_head=row.get("pathology_head"),
                    nmic_ref=row.get("nmic_ref"),
                    source_url=url,
                    verification_status=row.get("verification_status") or "verified",
                )
            )
            rate_sleep()
    return results
