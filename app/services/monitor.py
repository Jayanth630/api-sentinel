import json
import time
from datetime import datetime, timezone
import requests

from app.extensions import db
from app.models.endpoint import Endpoint
from app.models.check_result import CheckResult
from app.models.incident import Incident
from app.services.security import validate_url, SecurityValidationError

# Latency threshold above which a healthy response is marked as 'degraded'
LATENCY_DEGRADED_THRESHOLD_MS = 1200.0

def execute_health_check(endpoint: Endpoint, allow_local: bool = False) -> dict:
    """
    Perform a real HTTP health check against the endpoint.
    Records metrics, writes to database, manages incident lifecycle, and updates uptime %.
    """
    start_time = time.perf_counter()
    status_code = None
    latency_ms = 0.0
    is_success = False
    error_message = None
    response_size = 0
    response_headers_summary = {}

    # Defense-in-depth: Re-validate URL for SSRF protection at check time
    try:
        validated_url = validate_url(endpoint.url, allow_local=allow_local)
    except SecurityValidationError as e:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        error_message = f"Security Policy Violation: {str(e)}"
        return _record_check_result(
            endpoint=endpoint,
            status_code=None,
            latency_ms=latency_ms,
            is_success=False,
            error_message=error_message,
            response_size=0,
            headers_summary={}
        )
    except Exception as e:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        error_message = f"Invalid URL: {str(e)}"
        return _record_check_result(
            endpoint=endpoint,
            status_code=None,
            latency_ms=latency_ms,
            is_success=False,
            error_message=error_message,
            response_size=0,
            headers_summary={}
        )

    # Prepare HTTP headers
    request_headers = endpoint.get_headers_dict()
    if "User-Agent" not in request_headers and "user-agent" not in request_headers:
        request_headers["User-Agent"] = "API-Sentinel-HealthCheck/1.0 (+https://apisentinel.local)"

    # Prepare body payload if applicable
    body_data = None
    if endpoint.method.upper() in ("POST", "PUT", "PATCH", "DELETE") and endpoint.body:
        body_data = endpoint.body.encode("utf-8")

    # Send actual HTTP request
    response = None
    try:
        req_start = time.perf_counter()
        response = requests.request(
            method=endpoint.method.upper(),
            url=validated_url,
            headers=request_headers,
            data=body_data,
            timeout=endpoint.timeout,
            allow_redirects=True,
            stream=True
        )
        # Measure latency in milliseconds
        latency_ms = round((time.perf_counter() - req_start) * 1000, 2)
        status_code = response.status_code

        # Read response content with size limit (up to 512 KB to avoid excessive memory)
        content_chunks = []
        bytes_read = 0
        max_bytes = 512 * 1024
        for chunk in response.iter_content(chunk_size=8192):
            content_chunks.append(chunk)
            bytes_read += len(chunk)
            if bytes_read >= max_bytes:
                break
        response_size = bytes_read

        # Extract headers summary
        for k in ("Content-Type", "Server", "Date", "Content-Length"):
            if k in response.headers:
                response_headers_summary[k] = response.headers[k]

        # Evaluate success condition
        if endpoint.expected_status == 0:
            # Any 2xx code is acceptable
            if 200 <= status_code < 300:
                is_success = True
            else:
                is_success = False
                error_message = f"Received HTTP {status_code} ({response.reason or 'Error'}), expected 2xx"
        else:
            if status_code == endpoint.expected_status:
                is_success = True
            else:
                is_success = False
                error_message = f"Received HTTP {status_code} ({response.reason or 'Error'}), expected {endpoint.expected_status}"

    except requests.exceptions.Timeout:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        is_success = False
        error_message = f"Request timed out after {endpoint.timeout}s"
    except requests.exceptions.SSLError as ssl_err:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        is_success = False
        error_message = f"SSL Certificate error: {str(ssl_err).split(':')[-1].strip()}"
    except requests.exceptions.ConnectionError:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        is_success = False
        error_message = "Connection refused or host unreachable"
    except requests.exceptions.TooManyRedirects:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        is_success = False
        error_message = "Too many HTTP redirects"
    except requests.exceptions.RequestException as req_err:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        is_success = False
        error_message = f"HTTP Request failed: {str(req_err)}"
    except Exception as e:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        is_success = False
        error_message = f"Unexpected monitor error: {str(e)}"
    finally:
        if response is not None:
            try:
                response.close()
            except Exception:
                pass

    return _record_check_result(
        endpoint=endpoint,
        status_code=status_code,
        latency_ms=latency_ms,
        is_success=is_success,
        error_message=error_message,
        response_size=response_size,
        headers_summary=response_headers_summary
    )

def _record_check_result(
    endpoint: Endpoint,
    status_code: int | None,
    latency_ms: float,
    is_success: bool,
    error_message: str | None,
    response_size: int,
    headers_summary: dict
) -> dict:
    """Save the check result to database and update endpoint status."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Determine status string
    if is_success:
        if latency_ms >= LATENCY_DEGRADED_THRESHOLD_MS:
            status = "degraded"
        else:
            status = "healthy"
    else:
        status = "down"

    # Create check result record
    check_result = CheckResult(
        endpoint_id=endpoint.id,
        checked_at=now,
        status_code=status_code,
        response_time_ms=latency_ms,
        is_success=is_success,
        response_size_bytes=response_size,
        error_message=error_message,
        response_headers=json.dumps(headers_summary) if headers_summary else None
    )
    db.session.add(check_result)

    # Update endpoint state
    endpoint.last_checked_at = now
    endpoint.last_status = status
    endpoint.last_status_code = status_code
    endpoint.last_response_time_ms = latency_ms
    endpoint.last_error_message = error_message

    if is_success:
        endpoint.consecutive_failures = 0
        # Resolve active incident if present
        active_incidents = Incident.query.filter_by(endpoint_id=endpoint.id, is_active=True).all()
        for inc in active_incidents:
            inc.resolve()
    else:
        endpoint.consecutive_failures += 1
        # Create incident if not already active
        existing_incident = Incident.query.filter_by(endpoint_id=endpoint.id, is_active=True).first()
        if not existing_incident:
            new_incident = Incident(
                endpoint_id=endpoint.id,
                started_at=now,
                error_message=error_message or "Health check failed",
                last_status_code=status_code,
                is_active=True
            )
            db.session.add(new_incident)

    # Re-calculate uptime percentage from actual check history
    # We query check results for this endpoint (including the new one)
    try:
        db.session.flush()
        total_checks = CheckResult.query.filter_by(endpoint_id=endpoint.id).count()
        success_checks = CheckResult.query.filter_by(endpoint_id=endpoint.id, is_success=True).count()
        if total_checks > 0:
            endpoint.uptime_percentage = round((success_checks / total_checks) * 100.0, 2)
        else:
            endpoint.uptime_percentage = 100.0

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e

    return {
        "endpoint_id": endpoint.id,
        "endpoint_name": endpoint.name,
        "status": status,
        "status_code": status_code,
        "response_time_ms": latency_ms,
        "is_success": is_success,
        "error_message": error_message,
        "response_size_bytes": response_size,
        "uptime_percentage": endpoint.uptime_percentage,
        "checked_at": now.isoformat() + "Z"
    }
