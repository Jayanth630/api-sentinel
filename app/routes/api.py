from flask import Blueprint, request, jsonify, Response, current_app
from app.extensions import db
from app.models.endpoint import Endpoint
from app.models.check_result import CheckResult
from app.models.incident import Incident
from app.services.security import (
    validate_endpoint_payload,
    SecurityValidationError,
    InputValidationError,
)
from app.services.monitor import execute_health_check
from app.services.analytics import (
    get_dashboard_summary,
    get_endpoint_analytics,
    get_comparison_metrics,
    generate_endpoints_csv,
    generate_checks_csv,
)

api_bp = Blueprint("api", __name__, url_prefix="/api")

# Safe error handlers for Blueprint
@api_bp.errorhandler(InputValidationError)
def handle_input_error(err):
    return jsonify({"success": False, "error": str(err)}), 400

@api_bp.errorhandler(SecurityValidationError)
def handle_security_error(err):
    return jsonify({"success": False, "error": str(err)}), 403

# -------------------------------------------------------------
# Dashboard & Analytics Endpoints
# -------------------------------------------------------------

@api_bp.route("/dashboard/stats", methods=["GET"])
def api_dashboard_stats():
    """Fetch aggregated dashboard KPIs, status breakdown, and charts data."""
    try:
        summary = get_dashboard_summary()
        return jsonify({"success": True, "data": summary})
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to load dashboard metrics: {str(e)}"}), 500

@api_bp.route("/analytics/comparison", methods=["GET"])
def api_analytics_comparison():
    """Fetch comparative metrics across all endpoints."""
    try:
        data = get_comparison_metrics()
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@api_bp.route("/analytics/endpoint/<int:endpoint_id>", methods=["GET"])
def api_endpoint_analytics(endpoint_id):
    """Fetch granular analytics and historical ping charts for a specific endpoint."""
    hours = request.args.get("hours", default=24, type=int)
    if hours < 1 or hours > 720:  # Up to 30 days
        hours = 24

    analytics = get_endpoint_analytics(endpoint_id, hours=hours)
    if not analytics:
        return jsonify({"success": False, "error": "Endpoint not found"}), 404

    return jsonify({"success": True, "data": analytics})

# -------------------------------------------------------------
# Endpoint Management (CRUD)
# -------------------------------------------------------------

@api_bp.route("/endpoints", methods=["GET"])
def list_endpoints():
    """
    List endpoints with optional search and filtering.
    Query params:
    - search: string to match name or url
    - status: 'healthy', 'degraded', 'down', 'paused', 'unknown'
    - method: 'GET', 'POST', etc.
    - tag: tag name
    """
    query = Endpoint.query

    status_filter = request.args.get("status")
    if status_filter:
        status_filter = status_filter.strip().lower()
        if status_filter == "paused":
            query = query.filter_by(is_active=False)
        elif status_filter in ("healthy", "degraded", "down", "unknown"):
            query = query.filter_by(is_active=True, last_status=status_filter)

    method_filter = request.args.get("method")
    if method_filter:
        query = query.filter(Endpoint.method.ilike(method_filter.strip()))

    search_query = request.args.get("search")
    if search_query:
        search_term = f"%{search_query.strip()}%"
        query = query.filter(
            db.or_(
                Endpoint.name.ilike(search_term),
                Endpoint.url.ilike(search_term),
                Endpoint.tags.ilike(search_term)
            )
        )

    tag_filter = request.args.get("tag")
    if tag_filter:
        tag_term = f"%{tag_filter.strip()}%"
        query = query.filter(Endpoint.tags.ilike(tag_term))

    endpoints = query.order_by(Endpoint.created_at.desc()).all()
    return jsonify({"success": True, "data": [ep.to_dict() for ep in endpoints]})

@api_bp.route("/endpoints", methods=["POST"])
def create_endpoint():
    """Create a new monitored API endpoint."""
    payload = request.get_json(silent=True) or {}
    allow_local = current_app.config.get("ALLOW_LOCAL_MONITORING", False)

    try:
        validated = validate_endpoint_payload(payload, allow_local=allow_local)
    except (InputValidationError, SecurityValidationError) as e:
        status_code = 403 if isinstance(e, SecurityValidationError) else 400
        return jsonify({"success": False, "error": str(e)}), status_code

    new_endpoint = Endpoint(
        name=validated["name"],
        url=validated["url"],
        method=validated["method"],
        headers=validated["headers"],
        body=validated["body"],
        timeout=validated["timeout"],
        expected_status=validated["expected_status"],
        check_interval=validated["check_interval"],
        is_active=validated["is_active"],
        tags=validated["tags"]
    )
    db.session.add(new_endpoint)
    db.session.commit()

    # Automatically run an initial check so the card doesn't stay 'unknown'
    initial_check = None
    if new_endpoint.is_active:
        try:
            initial_check = execute_health_check(new_endpoint, allow_local=allow_local)
        except Exception:
            pass  # Initial check failure is handled by monitor service

    return jsonify({
        "success": True,
        "message": f"Endpoint '{new_endpoint.name}' created successfully.",
        "data": new_endpoint.to_dict(),
        "initial_check": initial_check
    }), 201

@api_bp.route("/endpoints/<int:endpoint_id>", methods=["GET"])
def get_endpoint(endpoint_id):
    """Retrieve details for a single endpoint."""
    ep = db.session.get(Endpoint, endpoint_id)
    if not ep:
        return jsonify({"success": False, "error": "Endpoint not found"}), 404
    return jsonify({"success": True, "data": ep.to_dict()})

@api_bp.route("/endpoints/<int:endpoint_id>", methods=["PUT"])
def update_endpoint(endpoint_id):
    """Update an existing endpoint configuration."""
    ep = db.session.get(Endpoint, endpoint_id)
    if not ep:
        return jsonify({"success": False, "error": "Endpoint not found"}), 404

    payload = request.get_json(silent=True) or {}
    allow_local = current_app.config.get("ALLOW_LOCAL_MONITORING", False)

    try:
        validated = validate_endpoint_payload(payload, allow_local=allow_local, existing_endpoint=ep)
    except (InputValidationError, SecurityValidationError) as e:
        status_code = 403 if isinstance(e, SecurityValidationError) else 400
        return jsonify({"success": False, "error": str(e)}), status_code

    ep.name = validated["name"]
    ep.url = validated["url"]
    ep.method = validated["method"]
    ep.headers = validated["headers"]
    ep.body = validated["body"]
    ep.timeout = validated["timeout"]
    ep.expected_status = validated["expected_status"]
    ep.check_interval = validated["check_interval"]
    ep.is_active = validated["is_active"]
    ep.tags = validated["tags"]

    db.session.commit()
    return jsonify({
        "success": True,
        "message": f"Endpoint '{ep.name}' updated successfully.",
        "data": ep.to_dict()
    })

@api_bp.route("/endpoints/<int:endpoint_id>", methods=["DELETE"])
def delete_endpoint(endpoint_id):
    """Delete an endpoint and all its associated logs and incidents."""
    ep = db.session.get(Endpoint, endpoint_id)
    if not ep:
        return jsonify({"success": False, "error": "Endpoint not found"}), 404

    endpoint_name = ep.name
    db.session.delete(ep)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Endpoint '{endpoint_name}' was deleted."
    })

@api_bp.route("/endpoints/<int:endpoint_id>/check", methods=["POST"])
def check_endpoint_now(endpoint_id):
    """
    Manually trigger an immediate real HTTP health check.
    Returns live response time, status code, and updated health state.
    """
    ep = db.session.get(Endpoint, endpoint_id)
    if not ep:
        return jsonify({"success": False, "error": "Endpoint not found"}), 404

    allow_local = current_app.config.get("ALLOW_LOCAL_MONITORING", False)
    check_result = execute_health_check(ep, allow_local=allow_local)

    return jsonify({
        "success": True,
        "message": f"Check executed: {check_result['status'].upper()}",
        "data": {
            "endpoint": ep.to_dict(),
            "check_result": check_result
        }
    })

@api_bp.route("/endpoints/<int:endpoint_id>/toggle", methods=["POST"])
def toggle_endpoint_active(endpoint_id):
    """Toggle an endpoint between active and paused states."""
    ep = db.session.get(Endpoint, endpoint_id)
    if not ep:
        return jsonify({"success": False, "error": "Endpoint not found"}), 404

    ep.is_active = not ep.is_active
    if not ep.is_active:
        # Resolve any active outage incidents so paused endpoints don't cause ghost alerts
        active_incidents = Incident.query.filter_by(endpoint_id=ep.id, is_active=True).all()
        for inc in active_incidents:
            inc.error_message += " (Monitoring paused by user)"
            inc.resolve()

    db.session.commit()

    state_str = "activated" if ep.is_active else "paused"
    return jsonify({
        "success": True,
        "message": f"Endpoint '{ep.name}' is now {state_str}.",
        "data": ep.to_dict()
    })

# -------------------------------------------------------------
# Incidents
# -------------------------------------------------------------

@api_bp.route("/incidents", methods=["GET"])
def list_incidents():
    """Fetch incident history, optionally filtering by active status."""
    query = Incident.query

    active_only = request.args.get("active")
    if active_only is not None:
        is_active = active_only.lower() in ("true", "1", "yes")
        query = query.filter_by(is_active=is_active)

    incidents = query.order_by(Incident.started_at.desc()).limit(100).all()
    return jsonify({"success": True, "data": [inc.to_dict() for inc in incidents]})

# -------------------------------------------------------------
# Export Reports (CSV)
# -------------------------------------------------------------

@api_bp.route("/export/endpoints/csv", methods=["GET"])
def export_endpoints_csv():
    """Download CSV report of all monitored endpoints."""
    csv_data = generate_endpoints_csv()
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=api_sentinel_endpoints.csv"}
    )

@api_bp.route("/export/checks/csv", methods=["GET"])
def export_checks_csv():
    """Download detailed check results logs as CSV."""
    endpoint_id = request.args.get("endpoint_id", type=int)
    csv_data = generate_checks_csv(endpoint_id=endpoint_id)
    filename = f"api_sentinel_checks_ep{endpoint_id}.csv" if endpoint_id else "api_sentinel_checks.csv"
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )
