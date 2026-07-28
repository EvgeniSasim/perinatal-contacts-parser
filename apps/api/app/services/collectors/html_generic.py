from pathlib import Path
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.config import get_settings
from app.services.normalize import normalize_email, normalize_phone


def _host_allowed(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    allow = {h.strip().lower() for h in get_settings().crawl_allowlist.split(",") if h.strip()}
    return any(host == a or host.endswith("." + a) for a in allow)


def parse_contacts_html(html: str, source_url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    phones: list[str] = []
    emails: list[str] = []
    for a in soup.select("a[href^=tel], a[href^=mailto]"):
        href = a.get("href", "")
        if href.startswith("tel:"):
            p = normalize_phone(href.replace("tel:", ""))
            if p:
                phones.append(p)
        if href.startswith("mailto:"):
            e = normalize_email(href.replace("mailto:", ""))
            if e:
                emails.append(e)
    import re

    for m in re.finditer(r"\+?\d[\d\-\s()]{8,}\d", text):
        p = normalize_phone(m.group(0))
        if p:
            phones.append(p)
    for m in re.finditer(r"[\w.+-]+@[\w-]+\.[\w.-]+", text):
        e = normalize_email(m.group(0))
        if e:
            emails.append(e)
    title = soup.title.get_text(strip=True) if soup.title else "Unknown"
    address_el = soup.select_one("[itemprop=address], .address, #address")
    return {
        "name": title,
        "address": address_el.get_text(" ", strip=True) if address_el else "",
        "phones": list(dict.fromkeys(phones)),
        "emails": list(dict.fromkeys(emails)),
        "source_url": source_url,
    }


def fetch_and_parse(url: str, *, html_override: str | None = None) -> dict:
    if html_override is not None:
        return parse_contacts_html(html_override, url)
    if not _host_allowed(url):
        raise ValueError(f"URL host not in crawl allowlist: {url}")
    headers = {
        "User-Agent": "PerinatalContactsBot/0.1 (+https://github.com/EvgeniSasim/perinatal-contacts-parser)"
    }
    with httpx.Client(timeout=15.0, follow_redirects=True, headers=headers) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return parse_contacts_html(resp.text, str(resp.url))


def load_fixture(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")
