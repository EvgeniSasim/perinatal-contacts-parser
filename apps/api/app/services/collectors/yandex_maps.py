"""Яндекс API Поиска по организациям — нужен ключ YANDEX_MAPS_API_KEY.

Docs: https://yandex.ru/maps-api/docs/geosearch-api/
Не скрапим HTML yandex.ru/maps (ToS) — только официальный HTTP API.
"""

from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.services.collectors.base import http_client, rate_sleep, to_institution

CITY_LL: dict[str, str] = {
    "Москва": "37.6173,55.7558",
    "Санкт-Петербург": "30.3351,59.9343",
    "Новосибирск": "82.9346,55.0302",
    "Екатеринбург": "60.5975,56.8389",
    "Казань": "49.1221,55.7887",
    "Нижний Новгород": "44.0020,56.3269",
    "Самара": "50.1500,53.1959",
    "Ростов-на-Дону": "39.7200,47.2357",
    "Краснодар": "38.9753,45.0355",
    "Воронеж": "39.1843,51.6720",
    "Пермь": "56.2502,58.0105",
    "Уфа": "55.9721,54.7388",
    "Красноярск": "92.8672,56.0153",
    "Владивосток": "131.8855,43.1155",
    "Челябинск": "61.4026,55.1644",
    "Омск": "73.3682,54.9885",
    "Тюмень": "65.5343,57.1522",
    "Иркутск": "104.2806,52.2869",
    "Хабаровск": "135.0720,48.4827",
    "Волгоград": "44.5018,48.7080",
}

SEARCH_QUERIES = [
    ("перинатальный центр", "perinatal_center"),
    ("родильный дом", "maternity_hospital"),
    ("женская консультация", "womens_clinic"),
    ("клиника акушерства и гинекологии", "obgyn_clinic"),
]


def _map_feature(feat: dict[str, Any], default_type: str, city: str) -> dict[str, Any]:
    props = feat.get("properties") or {}
    company = props.get("CompanyMetaData") or {}
    name = company.get("name") or props.get("name") or "—"
    address = company.get("address") or "—"
    phones = [p.get("formatted") or p.get("number") or "" for p in (company.get("Phones") or [])]
    urls = company.get("url") or company.get("Urls") or ""
    website = None
    if isinstance(urls, str):
        website = urls or None
    elif isinstance(urls, list) and urls:
        website = urls[0]
    href = props.get("uri") or company.get("url") or "https://yandex.ru/maps"
    source = href if isinstance(href, str) and href.startswith("http") else "https://yandex.ru/maps"
    return to_institution(
        name=name,
        type_=default_type,
        region=city,
        city=city,
        address=address,
        phones=phones,
        emails=[],
        website=website,
        source_url=source,
        verification_status="pending",
    )


def collect_yandex(
    *,
    cities: list[str] | None = None,
    results_per_query: int = 50,
) -> list[dict[str, Any]]:
    key = get_settings().yandex_maps_api_key
    if not key:
        raise RuntimeError(
            "YANDEX_MAPS_API_KEY is not set. Get a key at https://developer.tech.yandex.ru/"
        )

    city_map = {c: CITY_LL[c] for c in (cities or list(CITY_LL)) if c in CITY_LL}
    results: list[dict[str, Any]] = []
    seen: set[str] = set()

    with http_client(timeout=30.0) as client:
        for city, ll in city_map.items():
            for q, typ in SEARCH_QUERIES:
                resp = client.get(
                    "https://search-maps.yandex.ru/v1/",
                    params={
                        "apikey": key,
                        "text": f"{q}, {city}",
                        "type": "biz",
                        "lang": "ru_RU",
                        "ll": ll,
                        "spn": "0.5,0.5",
                        "rspn": 1,
                        "results": results_per_query,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                for feat in data.get("features") or []:
                    props = feat.get("properties") or {}
                    company = props.get("CompanyMetaData") or {}
                    cid = str(company.get("id") or props.get("name") or "")
                    if not cid or cid in seen:
                        continue
                    seen.add(cid)
                    results.append(_map_feature(feat, typ, city))
                rate_sleep()
    return results
