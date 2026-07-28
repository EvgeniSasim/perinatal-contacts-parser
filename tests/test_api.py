import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
os.environ["DATABASE_URL"] = "sqlite+pysqlite:////tmp/pnc-test.db"
os.environ["ADMIN_API_KEY"] = "test-key"
os.environ["SEED_CSV_PATH"] = str(ROOT / "data" / "seed" / "institutions.csv")
os.environ["STORAGE_DIR"] = str(ROOT / "storage")
os.environ["CRAWL_ALLOWLIST"] = "example.com,localhost"

from app.config import get_settings
from app.db import Base, engine, init_db
from app.main import create_app
from app.services.collectors.html_generic import fetch_and_parse, load_fixture
from app.services.normalize import normalize_name, normalize_phone


@pytest.fixture(autouse=True)
def _fresh_db():
    get_settings.cache_clear()
    Base.metadata.drop_all(bind=engine)
    init_db()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_normalize():
    assert normalize_phone("8 (495) 123-45-67") == "74951234567"
    assert "перинатальный" in normalize_name('ГБУЗ «Перинатальный центр»')


def test_health_and_list(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    r = client.get("/api/v1/institutions?page_size=5")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 100
    assert len(data["items"]) == 5


def test_filter_search(client):
    r = client.get("/api/v1/institutions", params={"region": "Москва", "page_size": 50})
    assert r.status_code == 200
    assert r.json()["total"] >= 1
    r = client.get("/api/v1/institutions", params={"q": "НМИЦ", "page_size": 10})
    assert r.json()["total"] >= 1
    r = client.get("/api/v1/institutions", params={"has_email": True, "page_size": 10})
    assert all(i["emails"] for i in r.json()["items"])


def test_admin_auth_and_export(client):
    r = client.post("/api/v1/admin/export", json={})
    assert r.status_code == 401
    r = client.post("/api/v1/admin/export", json={"region": "Москва"}, headers={"X-API-Key": "test-key"})
    assert r.status_code == 202
    job = r.json()
    assert job["status"] == "done"
    file_r = client.get(f"/api/v1/admin/export/{job['id']}/file", headers={"X-API-Key": "test-key"})
    assert file_r.status_code == 200
    assert file_r.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


def test_mailing_dry_run(client):
    r = client.post(
        "/api/v1/admin/mailings",
        json={"subject": "t", "body_html": "<p>x</p>", "dry_run": True, "filter": {"has_email": True}},
        headers={"X-API-Key": "test-key"},
    )
    assert r.status_code == 202
    body = r.json()
    assert body["status"] == "done"
    assert body["skipped_count"] > 0
    assert body["sent_count"] == 0


def test_html_collector_fixture():
    html = load_fixture(ROOT / "data" / "fixtures" / "sample_contacts.html")
    parsed = fetch_and_parse("https://example.com/contacts", html_override=html)
    assert "info@example.com" in parsed["emails"]
    assert any(p.endswith("4951234567") or "74951234567" in p for p in parsed["phones"])


def test_ssrf_blocked():
    with pytest.raises(ValueError):
        fetch_and_parse("https://evil.example.net/x")
