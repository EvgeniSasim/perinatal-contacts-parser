"""Извлечение ФИО руководства из HTML страниц учреждений.

Ключевое отличие от наивного подхода: ФИО связывается с должностью только внутри
одного структурного блока (строка таблицы, элемент списка, карточка, абзац), а не по
окну символов. На реальных страницах руководства окно символов даёт неверную роль —
заместители попадают в chief. См. docs/roles-dictionary.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable
from urllib.parse import unquote

from bs4 import BeautifulSoup, Comment, Tag

FIO_FULL = re.compile(
    r"\b([А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)?)\s+([А-ЯЁ][а-яё]+)\s+"
    r"([А-ЯЁ][а-яё]+(?:ович|евич|ьевич|овна|евна|ична|инична))\b"
)
FIO_SURNAME_INITIALS = re.compile(r"\b([А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)?)\s+([А-ЯЁ])\.\s?([А-ЯЁ])\.")
FIO_INITIALS_SURNAME = re.compile(r"\b([А-ЯЁ])\.\s?([А-ЯЁ])\.\s?([А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)?)\b")

ROLE_DEPUTY = re.compile(
    # разделитель необязателен: в реальности встречается «Зам.главного врача» без пробела
    r"(заместител\w*|зам\.)\s*(главн\w+\s+врача|директора|руководител\w+)",
    re.I,
)
ROLE_CHIEF = re.compile(
    r"(и\.?\s?о\.?\s+|исполняющ\w+\s+обязанности\s+)?"
    r"(главн\w+\s+врач|начальник\s+(?:центра|учреждени\w+)|руководител\w+\s+центра|"
    # «директор» принимается только с уточнением: бареное «Директор» на страницах
    # контактов — это директор страховой компании или фонда, а не главврач
    r"директор\w*\s+(?:центра|института|учреждени\w+|больницы|роддома|перинатальн\w+))",
    re.I,
)
DIRECTOR_TRAPS = re.compile(
    r"страхов|компани|\bфонд\b|филиал|департамент|\bооо\b|\bоао\b|\bзао\b|\bпао\b|"
    r"финансов|коммерческ|исполнительн|технически|по\s+развитию|университет",
    re.I,
)
# у учреждения один главврач (максимум плюс «и.о.»); больше — значит это список
# сторонних организаций, а не руководство
MAX_CHIEFS_PER_PAGE = 2
ROLE_HEAD = re.compile(r"(заведующ\w+|начальник\s+отделени\w+)", re.I)
PATHOLOGY = re.compile(r"отделени\w*\s+патологии|патологии\s+беременн|\bОПБ\b", re.I)
DEPARTMENT = re.compile(r"отделени\w*[^,.;:!?()]{0,60}", re.I)

# Контексты, в которых «главный врач» рядом с ФИО не означает, что это главврач
CHIEF_TRAPS = re.compile(
    r"приемн\w+\s+главн|секретар|помощник\s+главн|бухгалтер|медицинск\w+\s+сестр|"
    r"главн\w+\s+медсестр|внештатн\w+|по\s+кадрам|отдел\s+кадров",
    re.I,
)
SPECIALIST_ONLY = re.compile(r"врач-(акушер|гинеколог|неонатолог|анестезиолог|узи|терапевт)", re.I)
NOISE = re.compile(
    r"записаться|отзыв|новост|вакансия|прейскурант|расписание\s+приема|"
    r"мо[йюе]\s+операц|мне\s+сделали|благодар\w+\s+врач|спасибо\s+",
    re.I,
)
# «ГКБ им. С.П. Боткина» — инициалы в названии учреждения, а не ФИО руководителя
EPONYM = re.compile(r"(им\.|имени)\s*$", re.I)

# «Прием главного врача А.В. Ниманихиной»: должность в родительном падеже — значит и ФИО
# тоже, а в поле нужна именительная форма. Такая запись остаётся в персонах, но с low.
GENITIVE_ROLE = re.compile(r"главн(?:ого|ому|ым)\s+врач|заведующ(?:его|ему)|заместител(?:я|ю)", re.I)
OBLIQUE_SURNAME = re.compile(r"(ой|ого|ому|ым|ых|ей|ых)$", re.I)

BLOCK_TAGS = ("tr", "li", "td", "th", "p", "dd", "dt", "h1", "h2", "h3", "h4", "h5", "figcaption")
CARD_TAGS = ("div", "article", "section", "span", "strong", "b", "em")

PHONE_IN_BLOCK = re.compile(r"(?:\+7|8|7)?[\s(-]*\d{3,5}[\s)-]*\d{2,3}[\s-]?\d{2}[\s-]?\d{2}")
EMAIL_IN_BLOCK = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

MAX_BLOCK_LEN = 400
# Должность в подписи, ФИО в соседнем блоке: «<dt>Главный врач</dt><dd>Иванова А.В.</dd>»,
# «<th>Заведующий</th><td>…</td>», «<h3>Руководство</h3>» + карточка. Оба блока должны быть
# короткими, иначе это не пара, а разные части страницы.
MAX_LABEL_LEN = 120
MAX_LABELED_BLOCK_LEN = 120
MAX_SIBLINGS_LOOKBACK = 3

LEADERSHIP_PAGE_KINDS = {"leadership"}
MEDIUM_PAGE_KINDS = {"contacts", "departments"}


@dataclass
class ExtractedPerson:
    full_name: str
    role: str
    position_raw: str | None = None
    department: str | None = None
    phone: str | None = None
    email: str | None = None
    confidence: str = "low"
    source_url: str = ""
    _depth: int = field(default=0, repr=False, compare=False)


def normalize_person_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower().replace("ё", "е"))


def _match_fio(text: str) -> str | None:
    m = FIO_FULL.search(text)
    if m:
        return f"{m.group(1)} {m.group(2)} {m.group(3)}"
    m = FIO_SURNAME_INITIALS.search(text)
    if m:
        return f"{m.group(1)} {m.group(2)}.{m.group(3)}."
    for m in FIO_INITIALS_SURNAME.finditer(text):
        if EPONYM.search(text[max(0, m.start() - 10) : m.start()]):
            continue
        return f"{m.group(3)} {m.group(1)}.{m.group(2)}."
    return None


def detect_role(text: str) -> tuple[str, str | None] | None:
    """Определить роль по тексту блока. Порядок важен: deputy проверяется раньше chief."""
    if NOISE.search(text):
        return None
    if ROLE_DEPUTY.search(text):
        return "deputy", ROLE_DEPUTY.search(text).group(0)
    if ROLE_HEAD.search(text):
        position = ROLE_HEAD.search(text).group(0)
        if PATHOLOGY.search(text):
            return "pathology_head", position
        return "head", position
    chief = ROLE_CHIEF.search(text)
    if chief and not CHIEF_TRAPS.search(text):
        position = chief.group(0)
        if "директор" in position.lower() and DIRECTOR_TRAPS.search(text):
            return None
        return "chief", position
    if SPECIALIST_ONLY.search(text):
        return "other", SPECIALIST_ONLY.search(text).group(0)
    return None


def page_kind(url: str, title: str = "", body_text: str = "") -> str:
    haystack = f"{unquote(url)} {title}".lower()
    if re.search(r"rukovod|administra|glavn|leadership|management|nachalstvo|руководств|администрац", haystack):
        return "leadership"
    if re.search(r"kontakt|contact|контакт", haystack):
        return "contacts"
    if re.search(r"otdel|department|подразделен|отделен", haystack):
        return "departments"
    if re.search(r"руководств|администрация центра", body_text[:4000].lower()):
        return "leadership"
    return "other"


def _confidence_for(kind: str, role_in_block: bool) -> str:
    if not role_in_block:
        return "low"
    if kind in LEADERSHIP_PAGE_KINDS:
        return "high"
    if kind in MEDIUM_PAGE_KINDS:
        return "medium"
    return "medium"


def _blocks(soup: BeautifulSoup) -> Iterable[Tag]:
    for tag in soup.find_all(list(BLOCK_TAGS) + list(CARD_TAGS)):
        yield tag


def _depth(tag: Tag) -> int:
    return len(list(tag.parents))


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _label_role(tag: Tag) -> tuple[tuple[str, str | None], str] | None:
    """Найти должность в ближайшей предыдущей подписи-соседе.

    Разметка контактов часто разносит должность и ФИО по соседним элементам, и тогда
    внутри одного блока их не связать: `dl` не сканируется как блок намеренно, иначе
    «Главный врач: X» и «Заместитель: Y» в одном `dl` дадут перепутанные роли.

    Учитывается только ближайший непустой сосед: если в нём нет должности, связывать
    ФИО не с чем.
    """
    seen = 0
    for sibling in tag.previous_siblings:
        if isinstance(sibling, Comment):
            continue
        if isinstance(sibling, Tag):
            text = _clean(sibling.get_text(" ", strip=True))
        else:
            text = _clean(str(sibling))
        if not text:
            seen += 1
            if seen > MAX_SIBLINGS_LOOKBACK:
                return None
            continue
        if len(text) > MAX_LABEL_LEN or _match_fio(text):
            # подпись с чужим ФИО — это соседняя персона, а не должность нашей
            return None
        detected = detect_role(text)
        return (detected, text) if detected else None
    return None


def _is_oblique(fio: str, context: str) -> bool:
    """ФИО в косвенном падеже — в поле такую форму пускать нельзя."""
    surname = fio.split()[0]
    return bool(GENITIVE_ROLE.search(context) and OBLIQUE_SURNAME.search(surname))


def _extract_department(text: str, role: str) -> str | None:
    if role not in {"head", "pathology_head"}:
        return None
    m = DEPARTMENT.search(text)
    return _clean(m.group(0))[:256] if m else None


def extract_persons(html: str, source_url: str, kind: str | None = None) -> list[ExtractedPerson]:
    """Извлечь персоны из HTML. Возвращает дедуплицированный список.

    Для каждого ФИО выбирается самый глубокий (наиболее специфичный) блок, в котором
    ФИО встречается вместе с должностью — так «Приемная главного врача … Секретари
    Иванова И.И.» не превращается в главврача.
    """
    soup = BeautifulSoup(html, "html.parser")
    for junk in soup(["script", "style", "noscript"]):
        junk.decompose()

    if kind is None:
        title = soup.title.get_text(strip=True) if soup.title else ""
        kind = page_kind(source_url, title, soup.get_text(" ", strip=True))

    best: dict[tuple[str, str], ExtractedPerson] = {}
    for tag in _blocks(soup):
        text = _clean(tag.get_text(" ", strip=True))
        if not text or len(text) > MAX_BLOCK_LEN:
            continue
        fio = _match_fio(text)
        if not fio:
            continue
        context = text
        detected = detect_role(text)
        if not detected:
            if len(text) > MAX_LABELED_BLOCK_LEN or NOISE.search(text):
                continue
            labeled = _label_role(tag)
            if labeled is None:
                continue
            detected, label = labeled
            context = f"{label} {text}"
        role, position = detected
        if role == "chief" and CHIEF_TRAPS.search(context):
            continue
        if role == "chief" and "директор" in (position or "").lower() and DIRECTOR_TRAPS.search(context):
            continue

        phone_m = PHONE_IN_BLOCK.search(context)
        email_m = EMAIL_IN_BLOCK.search(context)
        person = ExtractedPerson(
            full_name=fio,
            role=role,
            position_raw=_clean(position)[:512] if position else None,
            department=_extract_department(context, role),
            phone=_clean(phone_m.group(0)) if phone_m else None,
            email=email_m.group(0).lower() if email_m else None,
            confidence=_confidence_for(kind, True),
            source_url=source_url,
            _depth=_depth(tag),
        )
        if _is_oblique(fio, context):
            person.confidence = "low"
        key = (normalize_person_name(fio), role)
        current = best.get(key)
        if current is None or person._depth > current._depth:
            best[key] = person

    # Если у одного ФИО есть и chief, и deputy — deputy достовернее (см. словарь ролей)
    names_with_deputy = {name for (name, role) in best if role == "deputy"}
    result = [p for (name, role), p in best.items() if not (role == "chief" and name in names_with_deputy)]

    chiefs = [p for p in result if p.role == "chief"]
    if len(chiefs) > MAX_CHIEFS_PER_PAGE:
        for person in chiefs:
            person.role = "other"
            person.confidence = "low"

    result.sort(key=lambda p: ({"chief": 0, "pathology_head": 1, "deputy": 2, "head": 3, "other": 4}[p.role], p.full_name))
    return result


def pick_field_values(persons: list[ExtractedPerson]) -> dict[str, str | None]:
    """Выбрать значения для денормализованных полей institutions.

    В поля попадают только high/medium — low остаётся только в institution_persons.
    """
    usable = [p for p in persons if p.confidence in {"high", "medium"}]

    def rank(person: ExtractedPerson) -> tuple[int, int]:
        conf = 0 if person.confidence == "high" else 1
        # среди «патологий» приоритет у отделения патологии беременности,
        # а не у патологии новорождённых
        pregnancy = 0 if re.search(r"беременн", person.department or "", re.I) else 1
        return (conf, pregnancy)

    def best(role: str) -> str | None:
        candidates = sorted((p for p in usable if p.role == role), key=rank)
        return candidates[0].full_name if candidates else None

    return {"chief_physician": best("chief"), "pathology_head": best("pathology_head")}
