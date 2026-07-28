"""Поиск официального сайта учреждения.

Без поисковых API возможности ограничены, поэтому стратегии применяются по порядку
надёжности: уже известный сайт → Nominatim по названию и городу → сопоставление с
записями справочников → ручной реестр → платные API (если заданы ключи).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from app.config import get_settings
from app.services.collectors.base import classify_network_error, http_client, rate_sleep
from app.services.normalize import normalize_name

BAD_HOSTS = {
    "vk.com",
    "ok.ru",
    "facebook.com",
    "instagram.com",
    "t.me",
    "youtube.com",
    "wikipedia.org",
    "gosuslugi.ru",
    "2gis.ru",
    "yandex.ru",
    "zoon.ru",
    "prodoctorov.ru",
    "napopravku.ru",
    "docdoc.ru",
}

STOP_WORDS = re.compile(
    r"^(гбуз|гауз|гбу|фгбу|фгбоу|огбуз|бу|кгбуз|мбуз|обуз|краевое|областное|"
    r"государственное|бюджетное|учреждение|здравоохранения|им|имени|no|№)$",
    re.I,
)


@dataclass
class DiscoveredSite:
    url: str
    strategy: str


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").lower().removeprefix("www.")


def is_plausible_site(url: str) -> bool:
    host = _host(url)
    if not host or "." not in host:
        return False
    return not any(host == bad or host.endswith("." + bad) for bad in BAD_HOSTS)


def _keywords(name: str) -> list[str]:
    tokens = re.findall(r"[а-яёa-z0-9]+", normalize_name(name))
    return [t for t in tokens if len(t) > 3 and not STOP_WORDS.match(t)]


def verify_site(url: str, name: str, city: str) -> tuple[bool, int | None, str]:
    """Проверить, что домен живой и похож на сайт этого учреждения."""
    candidates = [url]
    if url.startswith("https://"):
        candidates.append("http://" + url[len("https://") :])
    detail = "unreachable"
    for candidate in candidates:
        resp = None
        for verify in (True, False):
            try:
                with http_client(timeout=12, verify=verify) as client:
                    resp = client.get(candidate)
                break
            except Exception as exc:  # noqa: BLE001 — любая сетевая ошибка = домен не подтверждён
                detail = classify_network_error(exc)
                # смысл повторять без проверки TLS есть только при ошибке сертификата
                if detail != "ssl_error":
                    break
        if resp is None:
            rate_sleep(0.5)
            continue
        if resp.status_code >= 400:
            return False, resp.status_code, f"http_{resp.status_code}"
        text = resp.text[:200000].lower()
        city_hit = bool(city) and city.lower().replace("ё", "е") in text.replace("ё", "е")
        kw_hit = any(kw in text for kw in _keywords(name)[:6])
        if city_hit or kw_hit:
            return True, resp.status_code, "matched"
        return False, resp.status_code, "content_mismatch"
    return False, None, detail


def discover_via_nominatim(name: str, city: str) -> str | None:
    query = f"{name} {city}".strip()
    with http_client(timeout=30) as client:
        try:
            resp = client.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "q": query,
                    "countrycodes": "ru",
                    "format": "jsonv2",
                    "extratags": 1,
                    "limit": 5,
                },
            )
            resp.raise_for_status()
            items = resp.json()
        except Exception:  # noqa: BLE001
            return None
    rate_sleep(1.1)
    for item in items:
        extra = item.get("extratags") or {}
        site = extra.get("website") or extra.get("contact:website") or extra.get("url")
        if site and is_plausible_site(site):
            return site if site.startswith("http") else "https://" + site
    return None


def discover_via_2gis(name: str, city: str) -> str | None:
    key = get_settings().dgis_api_key
    if not key:
        return None
    with http_client(timeout=30) as client:
        try:
            resp = client.get(
                "https://catalog.api.2gis.com/3.0/items",
                params={
                    "q": f"{name} {city}",
                    "fields": "items.contact_groups",
                    "key": key,
                    "page_size": 5,
                },
            )
            resp.raise_for_status()
            items = (resp.json().get("result") or {}).get("items") or []
        except Exception:  # noqa: BLE001
            return None
    rate_sleep(0.5)
    for item in items:
        for group in item.get("contact_groups") or []:
            for contact in group.get("contacts") or []:
                if contact.get("type") == "website":
                    value = contact.get("url") or contact.get("value") or ""
                    if value and is_plausible_site(value):
                        return value if value.startswith("http") else "https://" + value
    return None


def discover_site(name: str, city: str, existing: str | None = None) -> DiscoveredSite | None:
    """Найти сайт учреждения. Возвращает None, если ни одна стратегия не сработала."""
    if existing and existing.strip() and is_plausible_site(existing):
        return DiscoveredSite(url=existing.strip(), strategy="existing")
    for strategy, finder in (
        ("osm", discover_via_nominatim),
        ("2gis", discover_via_2gis),
    ):
        found = finder(name, city)
        if found and is_plausible_site(found):
            return DiscoveredSite(url=found, strategy=strategy)
    return None
