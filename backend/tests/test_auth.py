from fastapi.testclient import TestClient

from app.auth import create_token
from app.main import app

client = TestClient(app)


def test_login_and_reports_access():
    res = client.post("/api/auth/login", json={"username": "admin", "password": "insight2026"})
    assert res.status_code == 200
    token = res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["role"] == "admin"

    reports = client.get("/api/reports", headers=headers)
    assert reports.status_code == 200


def test_manager_cannot_list_digest():
    res = client.post("/api/auth/login", json={"username": "harbourview", "password": "site2026"})
    token = res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    reports = client.get("/api/reports?week=2026-W26", headers=headers).json()["reports"]
    assert all(r["report_type"] != "digest" or r["site_id"] == "harbourview" for r in reports)
    site_reports = [r for r in reports if r["report_type"] == "site"]
    if site_reports:
        assert all(r["site_id"] == "harbourview" for r in site_reports)


def test_invalid_token_rejected():
    res = client.get("/api/auth/me", headers={"Authorization": "Bearer bad.token"})
    assert res.status_code == 401
