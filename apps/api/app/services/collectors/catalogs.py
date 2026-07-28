"""Каталоги: orgpage, medadvisor, kp, zdrav.expert, russiamedtravel, vademec, murman PDF."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from pypdf import PdfReader

from app.services.collectors.base import host_allowed, http_client, rate_sleep, to_institution

BASE_HEADERS = {
    "User-Agent": "PerinatalContactsBot/0.1 (+https://github.com/EvgeniSasim/perinatal-contacts-parser)",
    "Accept-Language": "ru",
}

ORGPAGE_START = "https://www.orgpage.ru/rossiya/perinatalnye-tsentry/"
MEDADVISOR_REGIONS = [
    "russia",
    "moskva",
    "sankt-peterburg",
    "novosibirsk",
    "ekaterinburg",
    "kazan",
    "nizhnii-novgorod",
    "samara",
    "rostov-na-donu",
    "krasnodar",
    "ufa",
    "perm",
    "voronezh",
    "volgograd",
    "krasnoyarsk",
    "saratov",
    "tyumen",
    "irkutsk",
    "khabarovsk",
    "yaroslavl",
    "vladivostok",
    "tomsk",
    "orenburg",
    "kemerovo",
    "ryazan",
    "astrahan",
    "penza",
    "lipetsk",
    "kirov",
    "kaliningrad",
    "tula",
    "kursk",
    "stavropol",
    "ivanovo",
    "bryansk",
    "belgorod",
    "tver",
    "sochi",
    "chelyabinsk",
    "omsk",
    "barnaul",
    "ulyanovsk",
    "izhevsk",
]

PHONE_RE = re.compile(r"\+?\d[\d\-\s()]{8,}\d")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
SITE_RE = re.compile(r"(?:https?://)?(?:www\.)?([a-z0-9.-]+\.[a-z]{2,})", re.I)


def _split_region_city(address: str) -> tuple[str, str, str]:
    parts = [p.strip() for p in re.split(r",", address or "") if p.strip()]
    region = parts[0] if parts else ""
    city = ""
    rest = address or ""
    for p in parts[1:]:
        if p.lower().startswith(("г.", "г ", "город")) or re.match(r"^г\.?\s", p, re.I):
            city = re.sub(r"^г\.?\s*", "", p, flags=re.I).strip()
            break
    if not city and len(parts) >= 2:
        city = parts[1]
    return region, city, rest


def _phones_from_text(text: str) -> list[str]:
    return list(dict.fromkeys(PHONE_RE.findall(text or "")))


def collect_orgpage(*, max_region_pages: int = 80, max_list_pages: int = 6) -> list[dict[str, Any]]:
    """OrgPage: /rossiya/perinatalnye-tsentry/{n}/ и региональные разделы. Без query (?)."""
    results: list[dict[str, Any]] = []
    seen: set[str] = set()

    def parse_list(html: str, source_url: str) -> None:
        soup = BeautifulSoup(html, "html.parser")
        for it in soup.select(".object-item.similar-item, .similar-item"):
            company_a = None
            for a in it.select("a[href]"):
                href = a.get("href") or ""
                if "/otzivy/" in href or "otzyv" in href:
                    continue
                if re.search(r"/[a-z0-9-]+/[a-z0-9-]+-\d+\.html$", href):
                    company_a = a
                    break
            if not company_a:
                continue
            href = urljoin(source_url, company_a.get("href"))
            name = company_a.get_text(" ", strip=True)
            if not name:
                img = it.select_one("img[alt]")
                name = (img.get("alt") if img else "") or ""
            if not name or name.lower().startswith("отзыв") or re.fullmatch(r"\d+\s*отзыв\w*", name, re.I):
                # decode slug: kogbuz-kirovskiy-...-5528893
                slug = href.rstrip("/").split("/")[-1].replace(".html", "")
                slug = re.sub(r"-\d+$", "", slug).replace("-", " ")
                name = slug.upper()
            cols = [c.get_text(" ", strip=True) for c in it.select(".similar-item__address-col")]
            phone_blob = cols[0] if cols else ""
            addr_blob = next((c for c in cols[1:] if c and not c.startswith("+")), "")
            phones = _phones_from_text(phone_blob)
            website = None
            for token in phone_blob.split():
                if "@" in token or token.startswith("+") or re.search(r"\d{3}", token) and ":" not in token and "." not in token:
                    continue
                if re.match(r"^[a-z0-9.-]+\.[a-z]{2,}$", token, re.I) and "bus.gov" not in token.lower():
                    website = "https://" + token.lower()
                    break
            region, city, _ = _split_region_city(addr_blob)
            if href in seen:
                continue
            seen.add(href)
            results.append(
                to_institution(
                    name=re.sub(r"^\d+\.\s*", "", name),
                    type_="perinatal_center",
                    region=region,
                    city=city,
                    address=addr_blob or "—",
                    phones=phones,
                    emails=[],
                    website=website,
                    source_url=href,
                    verification_status="pending",
                )
            )

    with http_client(timeout=35.0) as client:
        # country pages 1..N via path
        for page in range(1, max_list_pages + 1):
            url = ORGPAGE_START if page == 1 else f"https://www.orgpage.ru/rossiya/perinatalnye-tsentry/{page}/"
            if not host_allowed(url):
                continue
            resp = client.get(url)
            if resp.status_code != 200:
                break
            before = len(results)
            parse_list(resp.text, str(resp.url))
            rate_sleep()
            if len(results) == before and page > 1:
                break
            # discover region links from page 1
            if page == 1:
                soup = BeautifulSoup(resp.text, "html.parser")
                region_urls = []
                for a in soup.select("a[href*='perinatalnye-tsentry']"):
                    href = urljoin(str(resp.url), a.get("href") or "")
                    path = urlparse(href).path
                    if path.count("/") >= 2 and "/rossiya/" not in path and re.search(r"perinatalnye-tsentry/?$", path):
                        region_urls.append(href.rstrip("/") + "/")
                region_urls = list(dict.fromkeys(region_urls))[:max_region_pages]
                for rurl in region_urls:
                    if not host_allowed(rurl):
                        continue
                    try:
                        rr = client.get(rurl)
                        if rr.status_code == 200:
                            parse_list(rr.text, str(rr.url))
                    except Exception:
                        pass
                    rate_sleep()
    return results


def collect_medadvisor(*, regions: list[str] | None = None) -> list[dict[str, Any]]:
    """MedAdvisor: JSON в :item у brands-search-card. Без ?page= (robots Disallow)."""
    results: list[dict[str, Any]] = []
    seen: set[int] = set()
    with http_client(timeout=35.0) as client:
        for slug in regions or MEDADVISOR_REGIONS:
            url = f"https://medadvisor.ru/{slug}/clinics/rodilnye-doma-i-perinatalnye-tsentry"
            if not host_allowed(url):
                continue
            resp = client.get(url)
            if resp.status_code != 200:
                rate_sleep()
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            for card in soup.select("brands-search-card"):
                raw = card.get(":item")
                if not raw:
                    continue
                try:
                    obj = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                cid = obj.get("id")
                if cid in seen:
                    continue
                seen.add(cid)
                city_obj = obj.get("city") or {}
                name = obj.get("nameShort") or obj.get("name") or "—"
                address = obj.get("address") or "—"
                phone = obj.get("phone") or ""
                region, city, _ = _split_region_city(address)
                city = city_obj.get("name") or city
                typ = "maternity_hospital"
                low = name.lower()
                if "перинатал" in low:
                    typ = "perinatal_center"
                elif "женск" in low:
                    typ = "womens_clinic"
                source = f"https://medadvisor.ru/{slug}/clinic/{cid}" if cid else url
                results.append(
                    to_institution(
                        name=name,
                        type_=typ,
                        region=region or slug,
                        city=city or slug,
                        address=address,
                        phones=[phone] if phone and phone != "122" else [],
                        emails=[],
                        website=None,
                        source_url=source,
                        verification_status="pending",
                    )
                )
            rate_sleep()
    return results


def collect_kp() -> list[dict[str, Any]]:
    url = "https://www.kp.ru/russia/lechenie-v-rossii/roddoma/"
    if not host_allowed(url):
        return []
    with http_client(timeout=40.0) as client:
        resp = client.get(url)
        resp.raise_for_status()
        text = BeautifulSoup(resp.text, "html.parser").get_text("\n", strip=True)
    results: list[dict[str, Any]] = []
    # blocks like: Name Адрес ... Телефон +7...
    pattern = re.compile(
        r"(?P<name>(?:Перинатальный центр|ГБУЗ|ГБУ|Родильный дом|Роддом)[^\n]{5,120}?)\s+"
        r"Адрес\s+(?P<address>[^\n]+?)\s+Телефон\s+(?P<phone>\+?[\d\-\s()]+)",
        re.I,
    )
    for m in pattern.finditer(text):
        name = m.group("name").strip()
        address = m.group("address").strip()
        phone = m.group("phone").strip()
        region, city, _ = _split_region_city(address)
        if not city:
            city = address.split(",")[0].strip()
        results.append(
            to_institution(
                name=name,
                type_="maternity_hospital" if "родильн" in name.lower() or "роддом" in name.lower() else "perinatal_center",
                region=region or "Россия",
                city=city,
                address=address,
                phones=[phone],
                emails=[],
                website=None,
                source_url=url,
                verification_status="pending",
            )
        )
    return results


def collect_zdrav_expert() -> list[dict[str, Any]]:
    url = (
        "https://zdrav.expert/index.php/"
        "%D0%A1%D1%82%D0%B0%D1%82%D1%8C%D1%8F:%D0%9F%D0%B5%D1%80%D0%B8%D0%BD%D0%B0%D1%82%D0%B0%D0%BB%D1%8C%D0%BD%D1%8B%D0%B5_"
        "%D1%86%D0%B5%D0%BD%D1%82%D1%80%D1%8B_%D0%B2_%D0%A0%D0%BE%D1%81%D1%81%D0%B8%D0%B8"
    )
    if not host_allowed(url):
        return []
    with http_client(timeout=40.0) as client:
        resp = client.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
    content = soup.select_one("#content, .pub_body, .ta-content") or soup
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for tag in content.select("h2, h3"):
        text = tag.get_text(" ", strip=True)
        if "перинатальн" not in text.lower():
            continue
        if len(text) > 120 or "млн" in text.lower() or "₽" in text:
            # news headlines — extract only "... перинатальный центр ..."
            m = re.search(
                r"((?:[А-ЯЁ][\w\-]+(?:ский|ской|ский)?\s+)?(?:областной|краевой|республиканский|городской)?\s*перинатальн(?:ый|ого)\s+центр[^₽\d]{0,40})",
                text,
                re.I,
            )
            if not m:
                continue
            name = m.group(1).strip(" -—,.")
        else:
            name = text
        key = name.lower()
        if key in seen or len(name) < 18:
            continue
        seen.add(key)
        city = "—"
        for c in [
            "Москва",
            "Санкт-Петербург",
            "Новосибирск",
            "Казань",
            "Тула",
            "Якутск",
            "Петрозаводск",
            "Ульяновск",
            "Тамбов",
            "Грозный",
            "Чечня",
            "Татарстан",
        ]:
            if c.lower() in text.lower():
                city = "Грозный" if c == "Чечня" else ("Казань" if c == "Татарстан" else c)
                break
        results.append(
            to_institution(
                name=name,
                type_="perinatal_center",
                region="Россия",
                city=city,
                address="—",
                phones=[],
                emails=[],
                website=None,
                source_url=url,
                verification_status="pending",
            )
        )
    return results


def collect_russiamedtravel() -> list[dict[str, Any]]:
    url = "https://russiamedtravel.ru/catalog/akusherstvo/"
    if not host_allowed(url):
        return []
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    with http_client(timeout=45.0) as client:
        # first page without query; then PAGEN if robots allow catalog queries
        urls = [url]
        for page in range(2, 8):
            urls.append(f"{url}?PAGEN_1={page}")
        for u in urls:
            try:
                resp = client.get(u)
            except Exception:
                break
            if resp.status_code != 200:
                break
            soup = BeautifulSoup(resp.text, "html.parser")
            before = len(results)
            for a in soup.select("a[href*='/catalog/']"):
                href = urljoin(u, a.get("href") or "")
                name = a.get_text(" ", strip=True)
                if not name or len(name) < 10:
                    continue
                low = name.lower()
                if not any(x in low for x in ["перинатал", "родильн", "акушер", "эко", "репродуктив", "женск"]):
                    continue
                if href.rstrip("/") in {"https://russiamedtravel.ru/catalog", "https://russiamedtravel.ru/catalog/akusherstvo"}:
                    continue
                if href in seen:
                    continue
                seen.add(href)
                # region often prefixed in link text
                region = ""
                city = ""
                # "Ростовская область ..." pattern
                m = re.match(r"^(.+?(?:область|край|республика|округ))\s+(.+)$", name, re.I)
                if m:
                    region, name = m.group(1).strip(), m.group(2).strip()
                typ = "obgyn_clinic"
                if "перинатал" in low:
                    typ = "perinatal_center"
                elif "родильн" in low:
                    typ = "maternity_hospital"
                results.append(
                    to_institution(
                        name=name,
                        type_=typ,
                        region=region or "Россия",
                        city=city or "—",
                        address="—",
                        phones=[],
                        emails=[],
                        website=None,
                        source_url=href,
                        verification_status="pending",
                    )
                )
            rate_sleep()
            if len(results) == before and "?PAGEN" in u:
                break
    return results


def collect_vademec() -> list[dict[str, Any]]:
    url = "https://vademec.ru/news/2017/09/15/predstavlen-reyting-perinatalnykh-tsentrov/"
    if not host_allowed(url):
        return []
    with http_client(timeout=30.0) as client:
        resp = client.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
    results: list[dict[str, Any]] = []
    for table in soup.select("table"):
        headers = [th.get_text(" ", strip=True).lower() for th in table.select("tr th")]
        if not any("перинатал" in h for h in headers) and not any("город" in h for h in headers):
            # still try body
            pass
        for tr in table.select("tr")[1:]:
            cells = [td.get_text(" ", strip=True) for td in tr.select("td")]
            if len(cells) < 3:
                continue
            # #, name, city, score
            name = cells[1]
            city = cells[2]
            if "перинатал" not in name.lower() and "центр" not in name.lower():
                continue
            results.append(
                to_institution(
                    name=name,
                    type_="perinatal_center",
                    region="Россия",
                    city=city,
                    address=city,
                    phones=[],
                    emails=[],
                    website=None,
                    source_url=url,
                    verification_status="pending",
                )
            )
    return results


def collect_murman_pdf() -> list[dict[str, Any]]:
    url = "https://minzdrav.gov-murman.ru/activities/akusherstvo/doc/list.pdf"
    if not host_allowed(url):
        return []
    with http_client(timeout=60.0) as client:
        resp = client.get(url)
        resp.raise_for_status()
    from io import BytesIO

    reader = PdfReader(BytesIO(resp.content))
    text = "\n".join((p.extract_text() or "") for p in reader.pages)
    text = re.sub(r"[ \t]+", " ", text)
    # Find org; INDEX, City, address
    pattern = re.compile(
        r"((?:[А-ЯA-Z«\"].{5,160}?));\s*(\d{6}),\s*([^,\n]{2,60}),\s*([^\n]{5,120})",
        re.S,
    )
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for m in pattern.finditer(text):
        name = re.sub(r"\s+", " ", m.group(1)).strip()
        # drop preamble leftovers
        if "Перечень медицинских" in name:
            name = name.split("России", 1)[-1].strip(" .;")
        name = name.strip()
        if len(name) < 10:
            continue
        city = m.group(3).strip()
        address = re.sub(r"\s+", " ", m.group(4)).strip()
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        low = name.lower()
        typ = "obgyn_clinic"
        if "перинатал" in low:
            typ = "perinatal_center"
        results.append(
            to_institution(
                name=name,
                type_=typ,
                region="Россия",
                city=re.sub(r"^г\.?\s*", "", city, flags=re.I),
                address=f"{city}, {address}",
                phones=[],
                emails=[],
                website=None,
                source_url=url,
                verification_status="pending",
            )
        )
    return results


def collect_catalogs(sources: list[str] | None = None) -> list[dict[str, Any]]:
    mapping = {
        "orgpage": collect_orgpage,
        "medadvisor": collect_medadvisor,
        "kp": collect_kp,
        "zdrav": collect_zdrav_expert,
        "russiamedtravel": collect_russiamedtravel,
        "vademec": collect_vademec,
        "murman_pdf": collect_murman_pdf,
    }
    wanted = sources or list(mapping)
    rows: list[dict[str, Any]] = []
    for key in wanted:
        fn = mapping[key]
        part = fn()
        rows.extend(part)
    return rows
