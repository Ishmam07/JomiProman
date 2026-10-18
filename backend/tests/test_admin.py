"""Admin console authentication, activity trail, filtering and export tests."""

ADMIN = {"X-Admin-Key": "test-admin-key"}
REGISTRAR = {"X-Registrar-Key": "test-key"}


def test_admin_console_requires_separate_admin_key(client):
    assert client.get("/api/admin/overview").status_code == 401
    assert client.get("/api/admin/overview", headers={"X-Admin-Key": "wrong"}).status_code == 401
    # Registrar access alone must not authorize an admin view.
    assert client.get("/api/admin/overview", headers=REGISTRAR).status_code == 401
    ok = client.get("/api/admin/overview", headers=ADMIN)
    assert ok.status_code == 200
    assert "metrics" in ok.json() and "services" in ok.json()


def test_admin_overview_tracks_core_metrics_and_service_state(client):
    r = client.get("/api/admin/overview", headers=ADMIN)
    data = r.json()
    assert data["metrics"]["plots"] == 7
    assert data["metrics"]["deeds_total"] >= 2
    assert data["services"]["signing_algorithm"] == "Ed25519"
    assert set(data["risk_breakdown"]) == {"GREEN", "AMBER", "RED"}


def test_admin_audit_tracks_deed_registration_and_plot_check(client):
    client.get("/api/plots/রহিমপুর/412")
    body = {
        "mouza": "রহিমপুর", "dag": 412, "seller": "করিম", "buyer": "রফিক",
        "area": 6, "deed_date": "2026-10-17",
    }
    created = client.post("/api/deeds", json=body, headers=REGISTRAR)
    assert created.status_code == 201
    assert client.get("/api/admin/overview", headers=ADMIN).status_code == 200

    result = client.get("/api/admin/audit", headers=ADMIN, params={"page": 1, "page_size": 100})
    assert result.status_code == 200
    actions = [item["action"] for item in result.json()["items"]]
    assert "land.plot_check" in actions
    assert "deed.register" in actions
    assert "admin.overview.view" in actions


def test_admin_deed_and_plot_search_and_audit_csv(client):
    d = client.get("/api/admin/deeds", headers=ADMIN, params={"q": "D-0001"})
    assert d.status_code == 200
    assert d.json()["total"] >= 1
    p = client.get("/api/admin/plots", headers=ADMIN, params={"q": "রহিমপুর"})
    assert p.status_code == 200
    assert p.json()["total"] >= 3
    csv = client.get("/api/admin/audit.csv", headers=ADMIN)
    assert csv.status_code == 200
    assert "text/csv" in csv.headers["content-type"]
    assert "action" in csv.text and "summary" in csv.text


def test_invalid_registrar_access_is_recorded_without_storing_key(client):
    secret = "this-should-never-be-stored"
    result = client.post("/api/deeds", json={
        "mouza": "রহিমপুর", "dag": 412, "seller": "করিম", "buyer": "রফিক",
        "area": 1, "deed_date": "2026-10-17",
    }, headers={"X-Registrar-Key": secret})
    assert result.status_code == 401

    audit = client.get("/api/admin/audit", headers=ADMIN, params={"action": "registrar.access.denied"})
    assert audit.status_code == 200
    assert audit.json()["total"] == 1
    item = audit.json()["items"][0]
    assert item["outcome"] == "denied"
    assert secret not in str(item)


def test_admin_csv_neutralizes_spreadsheet_formulas(client, db):
    from app.models import AuditEvent

    db.add(AuditEvent(
        actor_type="public", action="test.csv", entity_type="test", outcome="ok",
        summary="=HYPERLINK(\"https://example.invalid\",\"open\")",
        details={"note": "formula-shaped content stays JSON-encoded"},
    ))
    db.commit()
    response = client.get("/api/admin/audit.csv", headers=ADMIN)
    assert response.status_code == 200
    assert "'=HYPERLINK" in response.text
