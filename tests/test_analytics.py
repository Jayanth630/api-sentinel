from datetime import datetime, timedelta, timezone
from app.extensions import db
from app.models.endpoint import Endpoint
from app.models.check_result import CheckResult
from app.services.analytics import (
    get_dashboard_summary,
    get_endpoint_analytics,
    get_comparison_metrics
)

def test_analytics_calculations(app):
    ep = Endpoint(name="Auth API", url="https://auth.example.com", method="GET")
    db.session.add(ep)
    db.session.commit()

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    # Add 10 check results: 8 successes (latencies: 50, 60, 70, 80, 90, 100, 110, 200), 2 failures
    latencies = [50.0, 60.0, 70.0, 80.0, 90.0, 100.0, 110.0, 200.0]
    for i, lat in enumerate(latencies):
        cr = CheckResult(
            endpoint_id=ep.id,
            checked_at=now - timedelta(minutes=10 - i),
            status_code=200,
            response_time_ms=lat,
            is_success=True
        )
        db.session.add(cr)

    # 2 failures
    for i in range(2):
        cr = CheckResult(
            endpoint_id=ep.id,
            checked_at=now - timedelta(minutes=2 - i),
            status_code=500,
            response_time_ms=300.0,
            is_success=False,
            error_message="HTTP 500 Internal Error"
        )
        db.session.add(cr)

    db.session.commit()

    # Test endpoint analytics
    analytics = get_endpoint_analytics(ep.id, hours=24)
    assert analytics is not None
    assert analytics["total_checks"] == 10
    assert analytics["successful_checks"] == 8
    assert analytics["failed_checks"] == 2
    # 8 / 10 = 80.0%
    assert analytics["uptime_percentage"] == 80.0
    # Avg latency of successes: (50+60+70+80+90+100+110+200)/8 = 760/8 = 95.0ms
    assert analytics["avg_latency_ms"] == 95.0
    assert analytics["min_latency_ms"] == 50.0
    assert analytics["max_latency_ms"] == 200.0
    # P95 should be close to 200.0
    assert analytics["p95_latency_ms"] >= 110.0

    # Test comparison metrics
    comp = get_comparison_metrics()
    assert len(comp) == 1
    assert comp[0]["total_checks"] == 10
    assert comp[0]["failed_checks"] == 2
    assert comp[0]["failure_rate"] == 20.0
