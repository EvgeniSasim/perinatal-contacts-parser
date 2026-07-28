from __future__ import annotations

import time
from typing import Any
from urllib.parse import urlparse

import httpx

from app.config import get_settings
from app.services.normalize import normalize_email, normalize_phone, split_multi

BOT_UA = "PerinatalContactsBot/0.1 (+https://github.com/EvgeniSasim/perinatal-contacts-parser)"


def classify_type(name: str, default: str = "perinatal_center") -> str:
    n = (name or "").lower()
    if "нмиц" in n or "кулакова" in n:
        return "nmic"
    if "женск" in n and "консульт" in n:
        return "womens_clinic"
    if "родильн" in n or "роддом" in n:
        return "maternity_hospital"
    if "областн" in n and "перинатал" in n:
        return "perinatal_center_regional"
    if "городск" in n and "перинатал" in n:
        return "perinatal_center_city"
    if "перинатал" in n:
        return "perinatal_center"
    if "кафедр" in n and ("акушер" in n or "гинеколог" in n):
        return "obgyn_chair"
    if "акушер" in n or "гинеколог" in n:
        return "obgyn_clinic"
    return default


def to_institution(
    *,
    name: str,
    type_: str,
    region: str,
    city: str,
    address: str,
    phones: list[str] | str | None = None,
    emails: list[str] | str | None = None,
    website: str | None = None,
    chief_physician: str | None = None,
    pathology_head: str | None = None,
    nmic_ref: str | None = None,
    source_url: str,
    verification_status: str = "pending",
) -> dict[str, Any]:
    if isinstance(phones, str):
        phones = split_multi(phones)
    if isinstance(emails, str):
        emails = split_multi(emails)
    phones = [p for p in (normalize_phone(x) or x for x in (phones or [])) if p]
    # keep human-readable if normalize failed partially — prefer E.164-ish
    emails = [e for e in (normalize_email(x) for x in (emails or [])) if e]
    return {
        "name": name.strip(),
        "type": classify_type(name, type_),
        "region": region or "Россия",
        "city": city or "—",
        "address": address or "—",
        "phones": phones,
        "emails": emails,
        "website": website or None,
        "chief_physician": chief_physician or None,
        "pathology_head": pathology_head or None,
        "nmic_ref": nmic_ref or None,
        "source_url": source_url,
        "verification_status": verification_status,
    }


def host_allowed(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    allow = {h.strip().lower() for h in get_settings().crawl_allowlist.split(",") if h.strip()}
    return any(host == a or host.endswith("." + a) for a in allow)


def http_client(timeout: float = 30.0) -> httpx.Client:
    return httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": BOT_UA, "Accept-Language": "ru"},
    )


def rate_sleep(seconds: float | None = None) -> None:
    time.sleep(seconds if seconds is not None else get_settings().crawl_delay_sec)
