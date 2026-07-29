"""Поиск страниц с информацией о руководстве на сайте учреждения.

Обход ограничен: тот же домен, ≤2 уровня, лимит страниц, ≤1 rps, robots.txt.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

from app.services.collectors.base import BOT_UA, classify_network_error, http_client, rate_sleep
from app.services.collectors.person_extractor import page_kind

LEAD_LINK = re.compile(
    r"руководств|администрац|главный\s+врач|начальство|сведения\s+об\s+образовательн|"
    r"о\s+(?:больнице|центре|нас|учреждении)|контакт|отделени|подразделен|структур|"
    r"rukovod|administra|glavn|leadership|management|kontakt|contact|about|otdel|struktur",
    re.I,
)
SKIP_LINK = re.compile(
    r"\.(pdf|doc|docx|xls|xlsx|zip|rar|jpg|jpeg|png|gif|svg|mp4)$|"
    r"mailto:|tel:|javascript:|#|vakans|novost|news|otzyv|review|prays|price|karta-sajta|"
    # страницы страховых компаний и партнёров дают ложных главврачей;
    # транслитерация встречается и через x (straxovye)
    r"strahov|strax|insur|partner",
    re.I,
)

MAX_PAGES = 12
MAX_DEPTH = 2
# Страницами считаются только успешные ответы, поэтому на сайте, где половина ссылок
# отдаёт 404, обход без этого лимита уходит в сотни запросов к чужому домену.
MAX_FETCHES = 30
PRIORITY = {"leadership": 0, "contacts": 1, "departments": 2, "other": 3}
# короткий таймаут: мёртвый домен не должен съедать минуту на ретраях
PAGE_TIMEOUT = 12.0

_robots_cache: dict[str, RobotFileParser | None] = {}


@dataclass
class FetchedPage:
    url: str
    kind: str
    html: str
    http_status: int


def _robots(base: str) -> RobotFileParser | None:
    origin = f"{urlparse(base).scheme}://{urlparse(base).netloc}"
    if origin in _robots_cache:
        return _robots_cache[origin]
    parser = RobotFileParser()
    try:
        with http_client(timeout=10) as client:
            resp = client.get(urljoin(origin, "/robots.txt"))
        if resp.status_code == 200:
            parser.parse(resp.text.splitlines())
        else:
            parser = None
    except Exception:  # noqa: BLE001 — недоступный robots.txt не должен ронять обход
        parser = None
    _robots_cache[origin] = parser
    return parser


def robots_allows(url: str, user_agent: str = BOT_UA) -> bool:
    """Проверять разрешение тем же User-Agent, который уходит в запросах."""
    parser = _robots(url)
    if parser is None:
        return True
    try:
        return parser.can_fetch(user_agent, url)
    except Exception:  # noqa: BLE001
        return True


def _same_host(a: str, b: str) -> bool:
    ha = (urlparse(a).hostname or "").lower().removeprefix("www.")
    hb = (urlparse(b).hostname or "").lower().removeprefix("www.")
    return ha == hb


class _Fetcher:
    """Загрузчик страниц с однократным fallback на неproверяемый TLS.

    Сертификаты Минцифры РФ отсутствуют в certifi, поэтому без fallback значительная
    часть сайтов учреждений выглядит недоступной.
    """

    def __init__(self, timeout: float = PAGE_TIMEOUT) -> None:
        self._timeout = timeout
        self._client = http_client(timeout=timeout)
        self._insecure: httpx.Client | None = None
        self.last_error: str | None = None
        self.used_insecure = False

    def __enter__(self) -> "_Fetcher":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._client.close()
        if self._insecure is not None:
            self._insecure.close()

    def _insecure_client(self) -> httpx.Client:
        if self._insecure is None:
            self._insecure = http_client(timeout=self._timeout, verify=False)
        return self._insecure

    def get(self, url: str) -> httpx.Response | None:
        clients = [self._client] if not self.used_insecure else [self._insecure_client()]
        for client in clients:
            try:
                self.last_error = None
                return client.get(url)
            except Exception as exc:  # noqa: BLE001
                kind = classify_network_error(exc)
                self.last_error = kind
                if kind == "ssl_error":
                    try:
                        response = self._insecure_client().get(url)
                        self.used_insecure = True
                        self.last_error = None
                        return response
                    except Exception as retry_exc:  # noqa: BLE001
                        self.last_error = classify_network_error(retry_exc)
                        return None
                return None
        return None


def normalize_site_url(website: str) -> str | None:
    value = (website or "").strip()
    if not value:
        return None
    value = value.split(";")[0].split(",")[0].strip()
    if not value:
        return None
    if not value.startswith(("http://", "https://")):
        value = "https://" + value
    if not urlparse(value).hostname:
        return None
    return value


def find_pages(website: str, max_pages: int = MAX_PAGES) -> tuple[list[FetchedPage], str | None]:
    """Обойти сайт и вернуть страницы, релевантные для извлечения персон.

    Возвращает (страницы, ошибка). Ошибка заполнена, если не удалось загрузить даже главную.
    """
    root = normalize_site_url(website)
    if not root:
        return [], "bad_url"
    if not robots_allows(root):
        return [], "blocked_by_robots"

    pages: list[FetchedPage] = []
    visited: set[str] = set()
    # (глубина, url)
    queue: list[tuple[int, str]] = [(0, root)]
    root_error: str | None = None

    fetches = 0
    with _Fetcher() as fetcher:
        while queue and len(pages) < max_pages and fetches < MAX_FETCHES:
            queue.sort(key=lambda item: (item[0], PRIORITY.get(page_kind(item[1]), 3)))
            depth, url = queue.pop(0)
            if url in visited or depth > MAX_DEPTH:
                continue
            visited.add(url)
            if not robots_allows(url):
                continue

            resp = fetcher.get(url)
            fetches += 1
            rate_sleep()
            if resp is None:
                if url == root:
                    root_error = fetcher.last_error or "network_error"
                continue
            if resp.status_code != 200 or "html" not in resp.headers.get("content-type", ""):
                if url == root:
                    root_error = f"http_{resp.status_code}"
                continue

            final_url = str(resp.url)
            soup = BeautifulSoup(resp.text, "html.parser")
            title = soup.title.get_text(strip=True) if soup.title else ""
            kind = page_kind(final_url, title, resp.text)
            if depth > 0 or kind != "other":
                pages.append(FetchedPage(url=final_url, kind=kind, html=resp.text, http_status=200))

            if depth >= MAX_DEPTH:
                continue
            for anchor in soup.select("a[href]"):
                href = anchor.get("href") or ""
                text = anchor.get_text(" ", strip=True)
                if SKIP_LINK.search(href):
                    continue
                if not (LEAD_LINK.search(text) or LEAD_LINK.search(href)):
                    continue
                target = urljoin(final_url, href)
                if not target.startswith(("http://", "https://")) or not _same_host(target, root):
                    continue
                target = target.split("#")[0]
                if target not in visited:
                    queue.append((depth + 1, target))

    pages.sort(key=lambda p: PRIORITY.get(p.kind, 3))
    return pages, root_error
