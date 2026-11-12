from unittest.mock import patch, MagicMock
import requests
from app.extensions import db
from app.models.endpoint import Endpoint
from app.models.check_result import CheckResult
from app.models.incident import Incident
from app.services.monitor import execute_health_check

def test_execute_health_check_success(app):
    ep = Endpoint(
        name="GitHub Status",
        url="https://api.github.com",
        method="GET",
        expected_status=200,
        timeout=5
    )
    db.session.add(ep)
    db.session.commit()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.reason = "OK"
    mock_resp.headers = {"Content-Type": "application/json", "Content-Length": "128"}
    mock_resp.iter_content.return_value = [b'{"status": "ok"}']

    with patch("requests.request", return_value=mock_resp):
        res = execute_health_check(ep)

    assert res["is_success"] is True
    assert res["status"] == "healthy"
    assert res["status_code"] == 200
    assert ep.last_status == "healthy"
    assert ep.consecutive_failures == 0
    assert ep.uptime_percentage == 100.0

    # Ensure check result was created
    cr = CheckResult.query.filter_by(endpoint_id=ep.id).first()
    assert cr is not None
    assert cr.is_success is True

def test_execute_health_check_status_code_mismatch_creates_incident(app):
    ep = Endpoint(
        name="Payment API",
        url="https://pay.example.com/checkout",
        method="POST",
        expected_status=200,
        timeout=5
    )
    db.session.add(ep)
    db.session.commit()

    mock_resp = MagicMock()
    mock_resp.status_code = 503
    mock_resp.reason = "Service Unavailable"
    mock_resp.headers = {}
    mock_resp.iter_content.return_value = [b"Service Unavailable"]

    with patch("requests.request", return_value=mock_resp):
        res = execute_health_check(ep, allow_local=True)

    assert res["is_success"] is False
    assert res["status"] == "down"
    assert res["status_code"] == 503
    assert ep.last_status == "down"
    assert ep.consecutive_failures == 1
    assert ep.uptime_percentage == 0.0

    # Incident should be generated
    inc = Incident.query.filter_by(endpoint_id=ep.id, is_active=True).first()
    assert inc is not None
    assert "HTTP 503" in inc.error_message

    # Recovery check: subsequent 200 resolves the incident
    mock_resp_ok = MagicMock()
    mock_resp_ok.status_code = 200
    mock_resp_ok.reason = "OK"
    mock_resp_ok.headers = {}
    mock_resp_ok.iter_content.return_value = [b"OK"]

    with patch("requests.request", return_value=mock_resp_ok):
        res_recovered = execute_health_check(ep, allow_local=True)

    assert res_recovered["is_success"] is True
    assert ep.last_status == "healthy"
    assert ep.consecutive_failures == 0
    # Uptime should now be 50% (1 failed out of 2 checks)
    assert ep.uptime_percentage == 50.0

    # Incident should now be resolved
    inc_resolved = Incident.query.filter_by(endpoint_id=ep.id, is_active=False).first()
    assert inc_resolved is not None
    assert inc_resolved.resolved_at is not None

def test_execute_health_check_timeout(app):
    ep = Endpoint(
        name="Slow API",
        url="https://slow.example.com",
        timeout=2
    )
    db.session.add(ep)
    db.session.commit()

    with patch("requests.request", side_effect=requests.exceptions.Timeout("Connection timed out")):
        res = execute_health_check(ep, allow_local=True)

    assert res["is_success"] is False
    assert res["status"] == "down"
    assert "timed out" in res["error_message"].lower()

def test_execute_health_check_connection_error(app):
    ep = Endpoint(
        name="Unreachable API",
        url="https://unreachable.example.com",
        timeout=5
    )
    db.session.add(ep)
    db.session.commit()

    with patch("requests.request", side_effect=requests.exceptions.ConnectionError("Connection refused")):
        res = execute_health_check(ep, allow_local=True)

    assert res["is_success"] is False
    assert res["status"] == "down"
    assert "Connection refused" in res["error_message"]
