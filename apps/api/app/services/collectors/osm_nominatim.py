"""OpenStreetMap via Nominatim — публичный геокодер, без API-ключа.

Policy: max 1 req/sec, корректный User-Agent.
https://operations.osmfoundation.org/policies/nominatim/
"""

from __future__ import annotations

from typing import Any

from app.services.collectors.base import http_client, rate_sleep, to_institution

DEFAULT_QUERIES: list[tuple[str, str]] = [
    ("перинатальный центр", "perinatal_center"),
    ("областной перинатальный центр", "perinatal_center_regional"),
    ("родильный дом", "maternity_hospital"),
    ("женская консультация", "womens_clinic"),
    ("клиника акушерства и гинекологии", "obgyn_clinic"),
    ("НМИЦ акушерства", "nmic"),
]

MAJOR_CITIES = [
    "Москва",
    "Санкт-Петербург",
    "Новосибирск",
    "Екатеринбург",
    "Казань",
    "Нижний Новгород",
    "Самара",
    "Ростов-на-Дону",
    "Краснодар",
    "Воронеж",
    "Пермь",
    "Уфа",
    "Красноярск",
    "Владивосток",
    "Иркутск",
    "Тюмень",
    "Хабаровск",
    "Ярославль",
    "Калининград",
    "Владимир",
    "Киров",
    "Омск",
    "Челябинск",
    "Саратов",
    "Волгоград",
]


def _city_queries(cities: list[str] | None = None) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for city in cities or MAJOR_CITIES:
        out.append((f"перинатальный центр {city}", "perinatal_center"))
        out.append((f"родильный дом {city}", "maternity_hospital"))
        out.append((f"женская консультация {city}", "womens_clinic"))
    return out


def _map_item(item: dict[str, Any], default_type: str) -> dict[str, Any]:
    addr = item.get("address") or {}
    extr = item.get("extratags") or {}
    name = item.get("name") or (item.get("display_name") or "").split(",")[0]
    city = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("county") or ""
    region = addr.get("state") or addr.get("region") or ""
    parts = [addr.get("road"), addr.get("house_number")]
    address = ", ".join([p for p in parts if p]) or (item.get("display_name") or "")
    phone = extr.get("phone") or extr.get("contact:phone") or ""
    email = extr.get("email") or extr.get("contact:email") or ""
    website = extr.get("website") or extr.get("contact:website") or ""
    source = f"https://www.openstreetmap.org/{item.get('osm_type')}/{item.get('osm_id')}"
    return to_institution(
        name=name,
        type_=default_type,
        region=region,
        city=city,
        address=address,
        phones=phone,
        emails=email,
        website=website,
        source_url=source,
        verification_status="pending",
    )


def collect_nominatim(
    *,
    include_cities: bool = True,
    cities: list[str] | None = None,
    limit_per_query: int = 40,
) -> list[dict[str, Any]]:
    queries = list(DEFAULT_QUERIES)
    if include_cities:
        queries.extend(_city_queries(cities))
    seen: set[str] = set()
    results: list[dict[str, Any]] = []
    with http_client(timeout=60.0) as client:
        for q, typ in queries:
            resp = client.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "q": q,
                    "countrycodes": "ru",
                    "format": "jsonv2",
                    "addressdetails": 1,
                    "extratags": 1,
                    "limit": limit_per_query,
                },
            )
            resp.raise_for_status()
            for item in resp.json():
                key = f"{item.get('osm_type')}:{item.get('osm_id')}"
                if key in seen:
                    continue
                seen.add(key)
                results.append(_map_item(item, typ))
            rate_sleep(1.1)
    return results
