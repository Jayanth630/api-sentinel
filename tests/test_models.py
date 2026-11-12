from datetime import datetime, timedelta, timezone
from app.extensions import db
from app.models.endpoint import Endpoint
from app.models.check_result import CheckResult
from app.models.incident import Incident

def test_endpoint_creation_and_defaults(app):
    ep = Endpoint(name="Auth Microservice", url="https://auth.example.com/health")
    db.session.add(ep)
    db.session.commit()

    assert ep.id is not None
    assert ep.method == "GET"
    assert ep.timeout == 10
    assert ep.expected_status == 200
    assert ep.check_interval == 60
    assert ep.is_active is True
    assert ep.last_status == "unknown"
    assert ep.uptime_percentage == 100.0

def test_endpoint_headers_parsing_and_masking(app):
    ep = Endpoint(
        name="Payments Service",
        url="https://pay.example.com/ping",
        headers='{"Authorization": "Bearer secret-token-12345", "Content-Type": "application/json", "X-Api-Key": "my-secret-key-999"}'
    )
    db.session.add(ep)
    db.session.commit()

    raw_headers = ep.get_headers_dict()
    assert raw_headers["Authorization"] == "Bearer secret-token-12345"
    assert raw_headers["Content-Type"] == "application/json"

    masked = ep.get_masked_headers()
    # Sensitive values should be masked
    assert "secret-token-12345" not in masked["Authorization"]
    assert "•" in masked["Authorization"]
    assert "my-secret-key-999" not in masked["X-Api-Key"]
    assert "•" in masked["X-Api-Key"]
    # Non-sensitive value remains untouched
    assert masked["Content-Type"] == "application/json"

def test_cascade_delete_check_results_and_incidents(app):
    ep = Endpoint(name="User API", url="https://user.example.com/health")
    db.session.add(ep)
    db.session.commit()

    # Add CheckResult
    cr = CheckResult(
        endpoint_id=ep.id,
        status_code=200,
        response_time_ms=120.5,
        is_success=True
    )
    db.session.add(cr)

    # Add Incident
    inc = Incident(
        endpoint_id=ep.id,
        error_message="HTTP 500",
        last_status_code=500
    )
    db.session.add(inc)
    db.session.commit()

    assert CheckResult.query.filter_by(endpoint_id=ep.id).count() == 1
    assert Incident.query.filter_by(endpoint_id=ep.id).count() == 1

    # Delete endpoint
    db.session.delete(ep)
    db.session.commit()

    # Children should be cascade deleted
    assert CheckResult.query.filter_by(endpoint_id=ep.id).count() == 0
    assert Incident.query.filter_by(endpoint_id=ep.id).count() == 0

def test_incident_resolution_duration(app):
    ep = Endpoint(name="Billing API", url="https://billing.example.com/health")
    db.session.add(ep)
    db.session.commit()

    start_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=5)
    inc = Incident(
        endpoint_id=ep.id,
        started_at=start_time,
        error_message="Connection timed out",
        is_active=True
    )
    db.session.add(inc)
    db.session.commit()

    assert inc.is_active is True
    assert inc.duration_seconds is None

    # Resolve
    inc.resolve()
    db.session.commit()

    assert inc.is_active is False
    assert inc.resolved_at is not None
    assert inc.duration_seconds >= 290  # ~300 seconds
