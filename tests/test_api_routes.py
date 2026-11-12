import json
from unittest.mock import patch, MagicMock
from app.extensions import db
from app.models.endpoint import Endpoint
from app.models.check_result import CheckResult

def test_get_endpoints_empty(client):
    res = client.get("/api/endpoints")
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["success"] is True
    assert json_data["data"] == []

def test_create_endpoint_success(client):
    payload = {
        "name": "GitHub Status",
        "url": "https://api.github.com",
        "method": "GET",
        "timeout": 10,
        "check_interval": 30,
        "tags": "core,github"
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.reason = "OK"
    mock_resp.headers = {}
    mock_resp.iter_content.return_value = [b"{}"]

    with patch("requests.request", return_value=mock_resp):
        res = client.post("/api/endpoints", json=payload)

    assert res.status_code == 201
    json_data = res.get_json()
    assert json_data["success"] is True
    assert json_data["data"]["name"] == "GitHub Status"
    assert json_data["data"]["tags"] == ["core", "github"]

def test_create_endpoint_ssrf_blocked(client):
    payload = {
        "name": "Internal DB Admin",
        "url": "http://127.0.0.1:8080/admin",
        "method": "GET"
    }
    res = client.post("/api/endpoints", json=payload)
    assert res.status_code == 403
    json_data = res.get_json()
    assert json_data["success"] is False
    assert "SSRF" in json_data["error"]

def test_update_endpoint(client, sample_endpoint):
    update_payload = {
        "name": "Updated GitHub Name",
        "url": "https://api.github.com/v3",
        "method": "GET",
        "timeout": 20,
        "expected_status": 200,
        "check_interval": 300,
        "tags": "updated,github"
    }
    res = client.put(f"/api/endpoints/{sample_endpoint.id}", json=update_payload)
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["success"] is True
    assert json_data["data"]["name"] == "Updated GitHub Name"
    assert json_data["data"]["timeout"] == 20

def test_delete_endpoint(client, sample_endpoint):
    res = client.delete(f"/api/endpoints/{sample_endpoint.id}")
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["success"] is True

    # Verify deleted
    fetch_res = client.get(f"/api/endpoints/{sample_endpoint.id}")
    assert fetch_res.status_code == 404

def test_toggle_endpoint_active(client, sample_endpoint):
    assert sample_endpoint.is_active is True
    res = client.post(f"/api/endpoints/{sample_endpoint.id}/toggle")
    assert res.status_code == 200
    assert res.get_json()["data"]["is_active"] is False

    res2 = client.post(f"/api/endpoints/{sample_endpoint.id}/toggle")
    assert res2.status_code == 200
    assert res2.get_json()["data"]["is_active"] is True

def test_check_endpoint_now_route(client, sample_endpoint):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.reason = "OK"
    mock_resp.headers = {}
    mock_resp.iter_content.return_value = [b"OK"]

    with patch("requests.request", return_value=mock_resp):
        res = client.post(f"/api/endpoints/{sample_endpoint.id}/check")

    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["success"] is True
    assert json_data["data"]["check_result"]["is_success"] is True

def test_dashboard_stats_route(client, sample_endpoint):
    res = client.get("/api/dashboard/stats")
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["success"] is True
    assert json_data["data"]["total_endpoints"] == 1
    assert "status_distribution" in json_data["data"]

def test_export_csv_routes(client, sample_endpoint):
    # Endpoints CSV
    res_ep = client.get("/api/export/endpoints/csv")
    assert res_ep.status_code == 200
    assert "text/csv" in res_ep.content_type
    assert "Name,URL,Method" in res_ep.data.decode("utf-8")
    assert sample_endpoint.name in res_ep.data.decode("utf-8")

    # Checks CSV
    res_checks = client.get("/api/export/checks/csv")
    assert res_checks.status_code == 200
    assert "text/csv" in res_checks.content_type
    assert "Check ID,Endpoint ID" in res_checks.data.decode("utf-8")

def test_secret_preservation_on_update(client, app):
    """Ensure that editing an endpoint without touching masked headers retains the original raw secret."""
    ep = Endpoint(
        name="Secure Vault",
        url="https://api.github.com",
        method="GET",
        headers='{"Authorization": "Bearer super-secret-jwt-token-99999", "X-Custom": "custom-val"}',
        is_active=True
    )
    db.session.add(ep)
    db.session.commit()

    # Client receives masked header: e.g. "Bea••••999"
    masked_dict = ep.get_masked_headers()
    assert "super-secret-jwt-token-99999" not in masked_dict["Authorization"]

    # User edits timeout from 10 to 25 and sends back the form containing the masked value
    update_payload = {
        "name": "Secure Vault Updated",
        "url": "https://api.github.com",
        "method": "GET",
        "timeout": 25,
        "headers": masked_dict
    }
    res = client.put(f"/api/endpoints/{ep.id}", json=update_payload)
    assert res.status_code == 200

    # Verify that in database, the raw unmasked secret is STILL intact!
    db.session.refresh(ep)
    raw_headers = ep.get_headers_dict()
    assert raw_headers["Authorization"] == "Bearer super-secret-jwt-token-99999"
    assert raw_headers["X-Custom"] == "custom-val"

def test_paused_state_preserved_on_edit(client, app):
    """Ensure that editing an endpoint when it is paused does NOT accidentally unpause it."""
    ep = Endpoint(
        name="Paused API",
        url="https://api.github.com",
        method="GET",
        is_active=False
    )
    db.session.add(ep)
    db.session.commit()

    update_payload = {
        "name": "Paused API Renamed",
        "url": "https://api.github.com",
        "method": "GET",
        "timeout": 15
        # is_active not passed (e.g. from standard form)
    }
    res = client.put(f"/api/endpoints/{ep.id}", json=update_payload)
    assert res.status_code == 200
    assert res.get_json()["data"]["is_active"] is False

    db.session.refresh(ep)
    assert ep.is_active is False

def test_toggle_pause_resolves_active_incidents(client, app):
    """Ensure that pausing an endpoint marks any active outage incident as resolved."""
    from app.models.incident import Incident
    ep = Endpoint(name="Failing API", url="https://api.github.com", is_active=True, last_status="down")
    db.session.add(ep)
    db.session.commit()

    inc = Incident(endpoint_id=ep.id, error_message="HTTP 500 Outage", is_active=True)
    db.session.add(inc)
    db.session.commit()

    assert Incident.query.filter_by(endpoint_id=ep.id, is_active=True).count() == 1

    # Toggle to paused
    res = client.post(f"/api/endpoints/{ep.id}/toggle")
    assert res.status_code == 200
    assert res.get_json()["data"]["is_active"] is False

    # Incident should now be resolved
    active_count = Incident.query.filter_by(endpoint_id=ep.id, is_active=True).count()
    assert active_count == 0
    db.session.refresh(inc)
    assert inc.is_active is False
    assert "Monitoring paused" in inc.error_message

def test_welcome_page_route(client):
    """Ensure GET / serves the professional Welcome / Landing Page."""
    res = client.get("/")
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "API SENTINEL" in html
    assert "Start Live Demo" in html
    assert "Real-Time API Health Monitoring" in html
    assert "Network Error &" in html
    assert "HTTP 5xx &" in html
    assert "High-Resolution Latency Analytics" in html
    assert "Automated Incident Management" in html

def test_dashboard_routes(client):
    """Ensure GET /dashboard and GET /app serve the main Dashboard SPA interface."""
    for path in ["/dashboard", "/app"]:
      res = client.get(path)
      assert res.status_code == 200
      html = res.get_data(as_text=True)
      assert "Dashboard Overview" in html or "kpiTotalApis" in html
      assert "navDashboard" in html
      assert "analyticsEndpointSelect" in html
