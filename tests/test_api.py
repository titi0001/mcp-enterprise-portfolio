from starlette.testclient import TestClient

from retail_mcp.api import app


def test_liveness() -> None:
    with TestClient(app) as client:
        response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "live"


def test_mcp_transport_requires_authentication() -> None:
    with TestClient(app) as client:
        response = client.post("/mcp", json={})
    assert response.status_code == 401
    assert response.json()["error"] == "authentication_failed"
