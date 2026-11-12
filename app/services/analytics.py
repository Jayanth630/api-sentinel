import io
import csv
from datetime import datetime, timedelta, timezone
from sqlalchemy import func
from app.extensions import db
from app.models.endpoint import Endpoint
from app.models.check_result import CheckResult
from app.models.incident import Incident

def get_dashboard_summary() -> dict:
    """
    Compute comprehensive dashboard KPIs and aggregated metrics.
    All statistics are strictly computed from real database records.
    """
    total_endpoints = Endpoint.query.count()
    active_endpoints = Endpoint.query.filter_by(is_active=True).count()
    paused_endpoints = Endpoint.query.filter_by(is_active=False).count()

    healthy_count = Endpoint.query.filter_by(is_active=True, last_status="healthy").count()
    degraded_count = Endpoint.query.filter_by(is_active=True, last_status="degraded").count()
    down_count = Endpoint.query.filter_by(is_active=True, last_status="down").count()
    unknown_count = Endpoint.query.filter_by(is_active=True, last_status="unknown").count()

    # System-wide overall uptime percentage
    total_checks = CheckResult.query.count()
    successful_checks = CheckResult.query.filter_by(is_success=True).count()
    if total_checks > 0:
        system_uptime = round((successful_checks / total_checks) * 100.0, 2)
    else:
        system_uptime = 100.0

    # System average response time (ms) for successful checks
    avg_latency_query = db.session.query(func.avg(CheckResult.response_time_ms)).filter(
        CheckResult.is_success == True
    ).scalar()
    system_avg_latency = round(float(avg_latency_query), 2) if avg_latency_query is not None else 0.0

    # Active incidents
    active_incidents_count = Incident.query.filter_by(is_active=True).count()

    # Latency trend over recent checks (up to last 30 checks chronologically)
    recent_checks_trend = (
        CheckResult.query.order_by(CheckResult.checked_at.desc())
        .limit(30)
        .all()
    )
    # Reverse so it flows left-to-right in chart
    recent_checks_trend.reverse()

    trend_labels = [c.checked_at.strftime("%H:%M:%S") for c in recent_checks_trend]
    trend_latencies = [round(c.response_time_ms, 1) for c in recent_checks_trend]
    trend_timestamps = [(c.checked_at.isoformat() + "Z") for c in recent_checks_trend]

    # HTTP Status distribution
    status_distribution = {
        "2xx": 0,
        "3xx": 0,
        "4xx": 0,
        "5xx": 0,
        "Network_Error": 0
    }
    all_check_codes = db.session.query(
        CheckResult.status_code, func.count(CheckResult.id)
    ).group_by(CheckResult.status_code).all()

    for code, count in all_check_codes:
        if code is None:
            status_distribution["Network_Error"] += count
        elif 200 <= code < 300:
            status_distribution["2xx"] += count
        elif 300 <= code < 400:
            status_distribution["3xx"] += count
        elif 400 <= code < 500:
            status_distribution["4xx"] += count
        elif 500 <= code < 600:
            status_distribution["5xx"] += count
        else:
            status_distribution["Network_Error"] += count

    # Recent activity feed
    recent_activity = (
        CheckResult.query.order_by(CheckResult.checked_at.desc())
        .limit(10)
        .all()
    )
    activity_feed = []
    for r in recent_activity:
        activity_feed.append({
            "id": r.id,
            "endpoint_id": r.endpoint_id,
            "endpoint_name": r.endpoint.name if r.endpoint else "Unknown",
            "endpoint_url": r.endpoint.url if r.endpoint else "",
            "checked_at": (r.checked_at.isoformat() + "Z"),
            "status_code": r.status_code,
            "response_time_ms": round(r.response_time_ms, 2),
            "is_success": r.is_success,
            "error_message": r.error_message
        })

    return {
        "total_endpoints": total_endpoints,
        "active_endpoints": active_endpoints,
        "paused_endpoints": paused_endpoints,
        "healthy_count": healthy_count,
        "degraded_count": degraded_count,
        "down_count": down_count,
        "unknown_count": unknown_count,
        "system_uptime": system_uptime,
        "system_avg_latency": system_avg_latency,
        "total_checks": total_checks,
        "active_incidents_count": active_incidents_count,
        "trend_labels": trend_labels,
        "trend_latencies": trend_latencies,
        "trend_timestamps": trend_timestamps,
        "status_distribution": status_distribution,
        "recent_activity": activity_feed
    }

def get_endpoint_analytics(endpoint_id: int, hours: int = 24) -> dict | None:
    """
    Detailed analytics for a specific endpoint over the given timeframe.
    """
    endpoint = db.session.get(Endpoint, endpoint_id)
    if not endpoint:
        return None

    cutoff_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=hours)

    checks_query = CheckResult.query.filter(
        CheckResult.endpoint_id == endpoint_id,
        CheckResult.checked_at >= cutoff_time
    ).order_by(CheckResult.checked_at.asc())

    checks = checks_query.all()
    total_checks = len(checks)
    successful_checks = sum(1 for c in checks if c.is_success)
    failed_checks = total_checks - successful_checks

    uptime_pct = round((successful_checks / total_checks) * 100.0, 2) if total_checks > 0 else 100.0

    latencies = [c.response_time_ms for c in checks if c.is_success]
    if latencies:
        avg_latency = round(sum(latencies) / len(latencies), 2)
        min_latency = round(min(latencies), 2)
        max_latency = round(max(latencies), 2)
        sorted_lat = sorted(latencies)
        p95_index = int(len(sorted_lat) * 0.95)
        p95_latency = round(sorted_lat[min(p95_index, len(sorted_lat) - 1)], 2)
    else:
        avg_latency = 0.0
        min_latency = 0.0
        max_latency = 0.0
        p95_latency = 0.0

    # Hourly latency buckets
    hourly_history = []
    for c in checks[-50:]:  # Last 50 checks for clear chart display
        ts_label = c.checked_at.strftime("%b %d %H:%M") if hours > 24 else c.checked_at.strftime("%H:%M:%S")
        hourly_history.append({
            "timestamp": ts_label,
            "iso_timestamp": (c.checked_at.isoformat() + "Z"),
            "latency_ms": round(c.response_time_ms, 2),
            "status_code": c.status_code,
            "is_success": c.is_success,
            "error_message": c.error_message
        })

    # Recent incidents for this endpoint
    incidents = Incident.query.filter_by(endpoint_id=endpoint_id).order_by(
        Incident.started_at.desc()
    ).limit(10).all()

    return {
        "endpoint": endpoint.to_dict(),
        "timeframe_hours": hours,
        "total_checks": total_checks,
        "successful_checks": successful_checks,
        "failed_checks": failed_checks,
        "uptime_percentage": uptime_pct,
        "avg_latency_ms": avg_latency,
        "min_latency_ms": min_latency,
        "max_latency_ms": max_latency,
        "p95_latency_ms": p95_latency,
        "history": hourly_history,
        "incidents": [inc.to_dict() for inc in incidents]
    }

def get_comparison_metrics() -> list:
    """
    Get side-by-side performance comparison for all endpoints.
    Prioritizes problematic/down endpoints first, followed by degraded, then healthy by speed.
    """
    endpoints = Endpoint.query.all()
    comparison = []

    for ep in endpoints:
        checks_count = CheckResult.query.filter_by(endpoint_id=ep.id).count()
        success_count = CheckResult.query.filter_by(endpoint_id=ep.id, is_success=True).count()
        failed_count = checks_count - success_count

        avg_lat = db.session.query(func.avg(CheckResult.response_time_ms)).filter(
            CheckResult.endpoint_id == ep.id,
            CheckResult.is_success == True
        ).scalar()

        comparison.append({
            "id": ep.id,
            "name": ep.name,
            "url": ep.url,
            "method": ep.method,
            "is_active": ep.is_active,
            "last_status": ep.last_status,
            "uptime_percentage": round(ep.uptime_percentage, 2),
            "avg_latency_ms": round(float(avg_lat), 2) if avg_lat is not None else 0.0,
            "total_checks": checks_count,
            "failed_checks": failed_count,
            "failure_rate": round((failed_count / checks_count) * 100.0, 2) if checks_count > 0 else 0.0
        })

    # Sort: Active down first, then degraded, then healthy by latency, then paused
    status_order = {"down": 0, "degraded": 1, "unknown": 2, "healthy": 3}
    comparison.sort(
        key=lambda x: (
            0 if x["is_active"] else 1,
            status_order.get(x["last_status"], 4),
            x["avg_latency_ms"] if x["avg_latency_ms"] > 0 else 999999
        )
    )
    return comparison

def generate_endpoints_csv() -> str:
    """Export monitored endpoints summary to CSV."""
    endpoints = Endpoint.query.order_by(Endpoint.name.asc()).all()
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "ID", "Name", "URL", "Method", "Expected Status",
        "Check Interval (s)", "Timeout (s)", "Status", "Uptime %",
        "Last Status Code", "Last Latency (ms)", "Consecutive Failures",
        "Last Checked (UTC)", "Tags"
    ])

    for ep in endpoints:
        writer.writerow([
            ep.id,
            ep.name,
            ep.url,
            ep.method,
            ep.expected_status,
            ep.check_interval,
            ep.timeout,
            ep.last_status,
            f"{ep.uptime_percentage:.2f}%",
            ep.last_status_code if ep.last_status_code is not None else "N/A",
            f"{ep.last_response_time_ms:.2f}" if ep.last_response_time_ms is not None else "N/A",
            ep.consecutive_failures,
            ep.last_checked_at.isoformat() if ep.last_checked_at else "Never",
            ep.tags or ""
        ])

    return output.getvalue()

def generate_checks_csv(endpoint_id: int | None = None) -> str:
    """Export check results logs to CSV."""
    query = CheckResult.query
    if endpoint_id:
        query = query.filter_by(endpoint_id=endpoint_id)
    
    checks = query.order_by(CheckResult.checked_at.desc()).limit(1000).all()
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Check ID", "Endpoint ID", "Endpoint Name", "Endpoint URL",
        "Checked At (UTC)", "HTTP Status", "Latency (ms)", "Success",
        "Response Size (Bytes)", "Error Details"
    ])

    for c in checks:
        ep_name = c.endpoint.name if c.endpoint else "Unknown"
        ep_url = c.endpoint.url if c.endpoint else "Unknown"
        writer.writerow([
            c.id,
            c.endpoint_id,
            ep_name,
            ep_url,
            c.checked_at.isoformat(),
            c.status_code if c.status_code is not None else "N/A",
            f"{c.response_time_ms:.2f}",
            "TRUE" if c.is_success else "FALSE",
            c.response_size_bytes,
            c.error_message or ""
        ])

    return output.getvalue()
