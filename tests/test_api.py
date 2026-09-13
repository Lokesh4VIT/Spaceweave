from fastapi.testclient import TestClient

from app.main import app


def test_health():
    response = TestClient(app).get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ready_reports_qdrant_and_embedding_model_separately(monkeypatch):
    """/ready should distinguish a Qdrant failure from an embedding-model
    failure instead of collapsing both into one generic error, so the
    developer can tell which dependency actually broke without needing
    Vercel function logs.
    """
    import app.api.routes as routes_module

    monkeypatch.setattr(routes_module, "ensure_collection", lambda: 42)
    monkeypatch.setattr(routes_module, "embedding_model", lambda: object())

    response = TestClient(app).get("/api/v1/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["qdrant"]["connected"] is True
    assert body["qdrant"]["points"] == 42
    assert body["embedding_model"]["loaded"] is True


def test_ready_surfaces_embedding_model_failure(monkeypatch):
    import app.api.routes as routes_module

    monkeypatch.setattr(routes_module, "ensure_collection", lambda: 10)

    def boom():
        raise OSError("[Errno 30] Read-only file system: '/home/user/.cache'")

    monkeypatch.setattr(routes_module, "embedding_model", boom)

    response = TestClient(app).get("/api/v1/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["embedding_model"]["loaded"] is False
    assert "Read-only file system" in body["embedding_model"]["error"]
