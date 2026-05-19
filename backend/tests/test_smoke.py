"""Smoke tests: el backend arranca y responde en modo demo (sin credenciales)."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_chat_demo_mode():
    r = client.post("/chat", json={"message": "¿Cómo van las ventas esta semana?"})
    assert r.status_code == 200
    body = r.json()
    assert body["is_demo"] is True
    assert body["tenant_id"] == "demo-restaurant"
    # Las métricas se calculan fuera del LLM, deben existir siempre.
    assert "ingresos_ultimos_7d" in body["metrics"]


def test_auth_demo_flow():
    # En modo demo /auth/login devuelve sesión ficticia...
    r = client.post(
        "/auth/login", json={"email": "demo@example.com", "password": "x"}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["is_demo"] is True
    token = body["access_token"]

    # ...y el token sirve para /auth/me.
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["tenant_id"] == "demo-restaurant"


def test_tenant_config_demo():
    # GET /tenant en demo no requiere setup real.
    r = client.get("/tenant")
    assert r.status_code == 200
    assert r.json()["is_demo"] is True

    # PUT /tenant/sheet acepta URL completa y extrae el ID (no persiste).
    url = "https://docs.google.com/spreadsheets/d/ABC123_xy/edit#gid=0"
    r2 = client.put("/tenant/sheet", json={"sheet": url})
    assert r2.status_code == 200
    assert r2.json()["sheet_id"] == "ABC123_xy"


def test_google_status_not_configured():
    # Sin OAuth de Google configurado, el endpoint degrada sin romper.
    r = client.get("/google/status")
    assert r.status_code == 200
    body = r.json()
    assert body["oauth_configured"] is False
    assert body["connected"] is False
