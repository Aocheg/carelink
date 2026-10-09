from fastapi.testclient import TestClient


def test_root_dashboard_endpoint_returns_html(client: TestClient):
    """
    Verify that the root endpoint serves the CareLink clinical web dashboard.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "CARELINK" in response.text
    assert "NEWS2" in response.text


def test_health_check_endpoint(client: TestClient):
    """
    Verify that GET /health returns service status.
    """
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "CARELINK"


def test_static_files_serving(client: TestClient):
    """
    Verify that the static assets mount serves index.html properly.
    """
    response = client.get("/static/index.html")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
