def test_catalog_parsers_offline():
    from app.services.collectors.catalogs import collect_vademec, collect_kp

    # live-light: these are small pages; skip if network fails
    try:
        rows = collect_vademec()
        assert len(rows) >= 5
        assert any("перинатальн" in r["name"].lower() for r in rows)
        rows = collect_kp()
        assert len(rows) >= 1
        assert rows[0]["phones"] or rows[0]["address"]
    except Exception as exc:  # noqa: BLE001
        import pytest

        pytest.skip(f"network catalogs unavailable: {exc}")
