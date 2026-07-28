"""2GIS Places API — официальный API, нужен ключ DGIS_API_KEY.

Docs: https://docs.2gis.com/en/api/search/places/overview
Не скрапим HTML 2gis.ru (ToS) — только Places API.
"""

from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.services.collectors.base import http_client, rate_sleep, to_institution

CITY_POINTS: dict[str, tuple[float, float]] = {
    "Москва": (37.6173, 55.7558),
    "Санкт-Петербург": (30.3351, 59.9343),
    "Новосибирск": (82.9346, 55.0302),
    "Екатеринбург": (60.5975, 56.8389),
    "Казань": (49.1221, 55.7887),
    "Нижний Новгород": (44.0020, 56.3269),
    "Самара": (50.1500, 53.1959),
    "Ростов-на-Дону": (39.7200, 47.2357),
    "Краснодар": (38.9753, 45.0355),
    "Воронеж": (39.1843, 51.6720),
    "Пермь": (56.2502, 58.0105),
    "Уфа": (55.9721, 54.7388),
    "Красноярск": (92.8672, 56.0153),
    "Владивосток": (131.8855, 43.1155),
    "Челябинск": (61.4026, 55.1644),
    "Омск": (73.3682, 54.9885),
    "Тюмень": (65.5343, 57.1522),
    "Иркутск": (104.2806, 52.2869),
    "Хабаровск": (135.0720, 48.4827),
    "Волгоград": (44.5018, 48.7080),
}

SEARCH_QUERIES = [
    ("перинатальный центр", "perinatal_center"),
    ("родильный дом", "maternity_hospital"),
    ("женская консультация", "womens_clinic"),
    ("акушерство гинекология", "obgyn_clinic"),
]


def _extract_contacts(item: dict[str, Any]) -> tuple[list[str], list[str], str | None]:
    phones: list[str] = []
    emails: list[str] = []
    website = None
    for group in item.get("contact_groups") or []:
        for c in group.get("contacts") or []:
            ctype = (c.get("type") or "").lower()
            value = c.get("value") or c.get("text") or ""
            if ctype in {"phone", "phone_emergency", "whatsapp"}:
                phones.append(value)
            elif ctype == "email":
                emails.append(value)
            elif ctype in {"website", "url"} and not website:
                website = value
    return phones, emails, website


def _map_item(item: dict[str, Any], default_type: str, city: str) -> dict[str, Any]:
    phones, emails, website = _extract_contacts(item)
    address = item.get("address_name") or item.get("full_address_name") or "—"
    region = city
    for adm in item.get("adm_div") or []:
        if adm.get("type") == "region":
            region = adm.get("name") or region
    source = f"https://2gis.ru/geo/{item.get('id')}" if item.get("id") else "https://catalog.api.2gis.com"
    return to_institution(
        name=item.get("name") or "—",
        type_=default_type,
        region=region,
        city=city,
        address=address,
        phones=phones,
        emails=emails,
        website=website,
        source_url=source,
        verification_status="pending",
    )


def collect_2gis(
    *,
    cities: list[str] | None = None,
    page_size: int = 10,
    max_pages: int = 3,
) -> list[dict[str, Any]]:
    key = get_settings().dgis_api_key
    if not key:
        raise RuntimeError("DGIS_API_KEY is not set. Get a key at https://platform.2gis.ru/")

    city_map = {c: CITY_POINTS[c] for c in (cities or list(CITY_POINTS)) if c in CITY_POINTS}
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    fields = "items.point,items.address_name,items.full_address_name,items.adm_div,items.contact_groups,items.name"

    with http_client(timeout=30.0) as client:
        for city, (lon, lat) in city_map.items():
            for q, typ in SEARCH_QUERIES:
                for page in range(1, max_pages + 1):
                    resp = client.get(
                        "https://catalog.api.2gis.com/3.0/items",
                        params={
                            "q": q,
                            "key": key,
                            "location": f"{lon},{lat}",
                            "type": "branch",
                            "page": page,
                            "page_size": page_size,
                            "fields": fields,
                            "locale": "ru_RU",
                        },
                    )
                    data = resp.json()
                    items = ((data.get("result") or {}).get("items")) or []
                    if not items:
                        break
                    for item in items:
                        iid = str(item.get("id") or "")
                        if not iid or iid in seen:
                            continue
                        seen.add(iid)
                        results.append(_map_item(item, typ, city))
                    rate_sleep()
                    if len(items) < page_size:
                        break
    return results
