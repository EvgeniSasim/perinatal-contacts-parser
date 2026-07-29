"""Тесты извлечения персон — офлайн, на фикстурах и синтетических блоках."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:////tmp/pnc-test-persons.db")
os.environ.setdefault("ADMIN_API_KEY", "test-key")

from app.services.collectors.page_finder import normalize_site_url
from app.services.collectors.person_extractor import (
    detect_role,
    extract_persons,
    normalize_person_name,
    page_kind,
    pick_field_values,
)
from app.services.collectors.site_discovery import is_plausible_site
from app.services.mailing import render_template


class _FakeInstitution:
    name = "ГБУЗ «Областной перинатальный центр»"
    city = "Владимир"
    region = "Владимирская область"
    address = "ул. Токарева, 1"
    chief_physician = "Денисова Наталья Михайловна"


def test_detect_role_deputy_before_chief():
    assert detect_role("Заместитель главного врача по лечебной работе")[0] == "deputy"
    assert detect_role("Главный врач")[0] == "chief"


def test_deputy_abbreviated_without_space():
    """«Зам.главного врача» без пробела — тоже заместитель, а не главврач."""
    assert detect_role("Зам.главного врача по медицинской части")[0] == "deputy"
    assert detect_role("Зам. главного врача по клинико-экспертной работе")[0] == "deputy"


def test_detect_role_pathology():
    role, _ = detect_role("Заведующий отделением патологии беременности")
    assert role == "pathology_head"
    role, _ = detect_role("Заведующий кардиологическим отделением")
    assert role == "head"


def test_chief_trap_is_rejected():
    # ловушка: приёмная главного врача и секретарь рядом
    assert detect_role("Приемная главного врача, секретарь") is None
    assert detect_role("Главный бухгалтер") is None
    assert detect_role("Главная медицинская сестра") is None


def test_block_level_association():
    """Заместители в списке не должны становиться главврачом."""
    html = """
    <table>
      <tr><td>Главный врач</td><td>Денисова Наталья Михайловна</td></tr>
      <tr><td>Заместитель главного врача</td><td>Александрова Ирина Сергеевна</td></tr>
      <tr><td>Заместитель главного врача</td><td>Шабалин Дмитрий Валерьевич</td></tr>
      <tr><td>Заведующий отделением патологии беременности</td><td>Петрова Анна Ивановна</td></tr>
    </table>
    """
    persons = extract_persons(html, "https://example.com/rukovodstvo", kind="leadership")
    fields = pick_field_values(persons)
    assert fields["chief_physician"] == "Денисова Наталья Михайловна"
    assert fields["pathology_head"] == "Петрова Анна Ивановна"
    deputies = {p.full_name for p in persons if p.role == "deputy"}
    assert deputies == {"Александрова Ирина Сергеевна", "Шабалин Дмитрий Валерьевич"}


def test_fio_split_by_br_is_joined():
    html = "<tr><td>Главный врач</td><td>Хабибуллина<br>Рамзия Талгатовна</td></tr>"
    persons = extract_persons(html, "https://example.com/management", kind="leadership")
    assert persons and persons[0].full_name == "Хабибуллина Рамзия Талгатовна"


def test_initials_formats():
    html = "<p>Главный врач Иванов И.И.</p>"
    persons = extract_persons(html, "https://example.com/glavnyy-vrach", kind="leadership")
    assert persons[0].full_name == "Иванов И.И."
    html = "<p>Главный врач А.Б. Сидоров</p>"
    persons = extract_persons(html, "https://example.com/glavnyy-vrach", kind="leadership")
    assert persons[0].full_name == "Сидоров А.Б."


def test_confidence_depends_on_page_kind():
    html = "<tr><td>Главный врач</td><td>Иванов Иван Иванович</td></tr>"
    high = extract_persons(html, "https://example.com/rukovodstvo", kind="leadership")
    medium = extract_persons(html, "https://example.com/kontakty", kind="contacts")
    assert high[0].confidence == "high"
    assert medium[0].confidence == "medium"


def test_low_confidence_not_promoted_to_fields():
    persons = extract_persons(
        "<tr><td>Главный врач</td><td>Иванов Иван Иванович</td></tr>",
        "https://example.com/kontakty",
        kind="contacts",
    )
    for person in persons:
        person.confidence = "low"
    assert pick_field_values(persons)["chief_physician"] is None


def test_pathology_of_pregnancy_preferred():
    html = """
    <ul>
      <li>Заведующий отделением патологии новорожденных Кадырова Нурзиля Асхатовна</li>
      <li>Заведующий отделением патологии беременности Мирошниченко Наталья Алексеевна</li>
    </ul>
    """
    persons = extract_persons(html, "https://example.com/rukovodstvo", kind="leadership")
    assert pick_field_values(persons)["pathology_head"] == "Мирошниченко Наталья Алексеевна"


def test_noise_pages_yield_nothing():
    html = "<div>Отзывы о врачах. Записаться к врачу Иванов Иван Иванович главный врач</div>"
    assert extract_persons(html, "https://example.com/otzyvy") == []


def test_review_text_is_not_a_person():
    html = "<div>Мою операцию проводил заведующий отделением Касян Геворг Рудикович. Спасибо!</div>"
    assert extract_persons(html, "https://example.com/about") == []


def test_insurance_director_is_not_a_chief():
    """На странице страховых компаний их директора не должны стать главврачом."""
    html = "<tr><td>Директор</td><td>Кузнецова Иннеса Юрьевна</td><td>страховая компания</td></tr>"
    assert extract_persons(html, "https://example.com/rukovodstvo", kind="leadership") == []


def test_bare_director_is_not_a_chief():
    """Бареное «Директор» на странице контактов — это директор страховой, не главврач."""
    html = "<tr><td>Директор</td><td>Воллин Дмитрий Леонидович</td></tr>"
    assert extract_persons(html, "https://example.com/contact", kind="contacts") == []


def test_qualified_director_is_a_chief():
    html = "<tr><td>Директор центра</td><td>Кузнецова Иннеса Юрьевна</td></tr>"
    persons = extract_persons(html, "https://example.com/rukovodstvo", kind="leadership")
    assert persons and persons[0].role == "chief"


def test_too_many_chiefs_on_page_are_demoted():
    """Три «главврача» на одной странице — это список сторонних организаций."""
    html = """
    <ul>
      <li>Главный врач Иванов Иван Иванович</li>
      <li>Главный врач Петров Петр Петрович</li>
      <li>Главный врач Сидоров Сидор Сидорович</li>
    </ul>
    """
    persons = extract_persons(html, "https://example.com/rukovodstvo", kind="leadership")
    assert all(p.role == "other" for p in persons)
    assert pick_field_values(persons)["chief_physician"] is None


def test_role_in_sibling_label_definition_list():
    """Должность в dt, ФИО в dd — самая частая разметка контактов."""
    html = """
    <dl>
      <dt>Главный врач</dt><dd>Ниманихина Алла Владимировна</dd>
      <dt>Заведующий отделением патологии беременности</dt><dd>Петрова Анна Ивановна</dd>
    </dl>
    """
    persons = extract_persons(html, "https://example.com/contact", kind="contacts")
    by_role = {p.role: p.full_name for p in persons}
    assert by_role["chief"] == "Ниманихина Алла Владимировна"
    assert by_role["pathology_head"] == "Петрова Анна Ивановна"


def test_role_in_sibling_label_heading():
    html = "<div><h3>Главный врач</h3><p>Соколова Елена Юрьевна</p></div>"
    persons = extract_persons(html, "https://example.com/rukovodstvo", kind="leadership")
    assert persons and persons[0].role == "chief"
    assert persons[0].confidence == "high"


def test_sibling_label_with_own_fio_is_not_reused():
    """Список ФИО подряд: должность первого не должна распространиться на остальных."""
    html = """
    <div>
      <h3>Главный врач</h3>
      <p>Соколова Елена Юрьевна</p>
      <p>Кузнецова Мария Ивановна</p>
    </div>
    """
    persons = extract_persons(html, "https://example.com/rukovodstvo", kind="leadership")
    assert [p.full_name for p in persons] == ["Соколова Елена Юрьевна"]


def test_sibling_label_does_not_bypass_director_trap():
    html = "<dl><dt>Директор страховой компании</dt><dd>Кузнецова Иннеса Юрьевна</dd></dl>"
    assert extract_persons(html, "https://example.com/contact", kind="contacts") == []


def test_genitive_fio_is_not_promoted_to_field():
    """«Прием главного врача А.В. Ниманихиной» — форма косвенная, в поле не годится."""
    html = "<p>Прием главного врача А.В. Ниманихиной по личным вопросам</p>"
    persons = extract_persons(html, "https://example.com/priem-administraciey", kind="leadership")
    assert persons and persons[0].confidence == "low"
    assert pick_field_values(persons)["chief_physician"] is None
    # именительная форма на той же должности остаётся пригодной
    nominative = extract_persons(
        "<p>Главный врач Ниманихина Алла Владимировна</p>",
        "https://example.com/contact",
        kind="contacts",
    )
    assert pick_field_values(nominative)["chief_physician"] == "Ниманихина Алла Владимировна"


def test_eponym_initials_are_not_a_person():
    """«ГКБ им. С.П. Боткина» — не ФИО заместителя."""
    html = "<p>Заместитель директора ГКБ им. С.П. Боткина</p>"
    assert extract_persons(html, "https://example.com/about", kind="leadership") == []


def test_page_kind_handles_percent_encoded_urls():
    assert page_kind("https://x.ru/%D0%BA%D0%BE%D0%BD%D1%82%D0%B0%D0%BA%D1%82%D1%8B") == "contacts"
    assert page_kind("https://x.ru/rukovodstvo") == "leadership"


def test_person_name_normalization():
    assert normalize_person_name("Алёшина  Мария  Петровна") == "алешина мария петровна"


def test_site_url_normalization():
    assert normalize_site_url("opc33.ru") == "https://opc33.ru"
    assert normalize_site_url("rodipenza.ru;www.penza-filatova.ru/") == "https://rodipenza.ru"
    assert normalize_site_url("") is None


def test_social_networks_are_not_official_sites():
    assert not is_plausible_site("https://vk.com/perinatal")
    assert not is_plausible_site("https://2gis.ru/moscow/firm/123")
    assert is_plausible_site("https://opc33.ru")


def test_mailing_template_personalization():
    body = "<p>Уважаемый(ая) {{chief}}! Приглашаем {{name}} ({{city}}).</p>"
    rendered = render_template(body, _FakeInstitution())
    assert "Денисова Наталья Михайловна" in rendered
    assert "Владимир" in rendered
    assert "{{" not in rendered


def test_mailing_template_degrades_without_chief():
    inst = _FakeInstitution()
    inst.chief_physician = None
    assert render_template("Уважаемый(ая) {{chief}}!", inst) == "Уважаемый(ая) коллега!"


def test_mailing_html_escapes_substituted_values():
    """Название учреждения приходит с чужого сайта — разметка в нём не должна исполняться."""
    inst = _FakeInstitution()
    inst.name = '<img src=x onerror="alert(1)">Роддом «Тест»'
    rendered = render_template("<p>{{name}}</p>", inst, html=True)
    assert "<img" not in rendered
    assert "&lt;img" in rendered
    # в теме письма экранирование не нужно — это plain text
    assert "<img" in render_template("{{name}}", inst)


def test_robots_is_checked_with_request_user_agent():
    from urllib.robotparser import RobotFileParser

    from app.services.collectors import page_finder

    parser = RobotFileParser()
    parser.parse(["User-agent: PerinatalContactsBot", "Disallow: /rukovodstvo"])
    page_finder._robots_cache["https://example.com"] = parser
    try:
        assert not page_finder.robots_allows("https://example.com/rukovodstvo")
        assert page_finder.robots_allows("https://example.com/kontakty")
    finally:
        page_finder._robots_cache.pop("https://example.com", None)


def test_extract_from_real_fixture():
    """Реальная страница руководства (сохранённая) должна дать главврача."""
    fixtures = sorted((ROOT / "data" / "fixtures" / "persons").glob("*.html"))
    if not fixtures:
        return
    found = 0
    for path in fixtures:
        persons = extract_persons(path.read_text(encoding="utf-8"), f"https://example.com/{path.stem}")
        if any(p.role == "chief" for p in persons):
            found += 1
    assert found >= 1
