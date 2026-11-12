import ipaddress
import json
import re
import socket
from urllib.parse import urlparse

class SecurityValidationError(Exception):
    """Raised when a security validation (such as SSRF detection) fails."""
    pass

class InputValidationError(Exception):
    """Raised when user input fails validation."""
    pass

# Prohibited hostnames that point to local/internal services
RESTRICTED_HOSTNAMES = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
    "ip6-localhost",
    "ip6-loopback",
    "instance-data",
    "metadata.google.internal",
}

VALID_HTTP_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}

def is_ip_private_or_restricted(ip_str: str) -> bool:
    """
    Check if an IP address belongs to private, loopback, link-local,
    multicast, or cloud-provider metadata address space.
    """
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True  # If it cannot be parsed as a valid IP, consider unsafe

    # Standard python ipaddress checks
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        return True

    # Check IPv4 specific dangerous ranges:
    # 169.254.169.254 (AWS / GCP / Azure metadata)
    # 100.64.0.0/10 (Carrier-grade NAT)
    # 192.0.0.0/24 (IETF Protocol Assignments)
    # 198.18.0.0/15 (Network benchmark tests)
    if isinstance(ip, ipaddress.IPv4Address):
        dangerous_networks = [
            ipaddress.ip_network("100.64.0.0/10"),
            ipaddress.ip_network("192.0.0.0/24"),
            ipaddress.ip_network("198.18.0.0/15"),
            ipaddress.ip_network("169.254.0.0/16"),
        ]
        for net in dangerous_networks:
            if ip in net:
                return True

    return False

def validate_url(url_string: str, allow_local: bool = False) -> str:
    """
    Validate an endpoint URL against SSRF and protocol manipulation.
    Ensures URL uses http/https and does not resolve to internal network addresses.
    """
    if not url_string or not isinstance(url_string, str):
        raise InputValidationError("URL cannot be empty.")

    url_string = url_string.strip()
    if len(url_string) > 2048:
        raise InputValidationError("URL length exceeds maximum limit of 2048 characters.")

    try:
        parsed = urlparse(url_string)
    except Exception as e:
        raise InputValidationError(f"Invalid URL structure: {str(e)}")

    # Strictly enforce http or https schemes
    if parsed.scheme.lower() not in ("http", "https"):
        raise SecurityValidationError(
            f"Scheme '{parsed.scheme}' is not allowed. Only HTTP and HTTPS are permitted."
        )

    hostname = parsed.hostname
    if not hostname:
        raise InputValidationError("URL must include a valid host name.")

    hostname_lower = hostname.lower()

    # If local monitoring is explicitly permitted (e.g. testing local server), bypass IP check
    if allow_local:
        return url_string

    # Check against known restricted hostnames
    if hostname_lower in RESTRICTED_HOSTNAMES or hostname_lower.endswith(".localhost") or hostname_lower.endswith(".local") or hostname_lower.endswith(".internal"):
        raise SecurityValidationError(
            f"Access to internal host '{hostname}' is blocked to prevent SSRF vulnerabilities."
        )

    # Perform DNS resolution to inspect underlying IP addresses
    try:
        addr_info = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        raise SecurityValidationError(f"Could not resolve host '{hostname}': {str(e)}")
    except Exception as e:
        raise SecurityValidationError(f"DNS resolution error for host '{hostname}': {str(e)}")

    if not addr_info:
        raise SecurityValidationError(f"No IP addresses resolved for host '{hostname}'.")

    # Inspect all resolved IPs
    for family, socktype, proto, canonname, sockaddr in addr_info:
        ip_addr = sockaddr[0]
        if is_ip_private_or_restricted(ip_addr):
            raise SecurityValidationError(
                f"Host '{hostname}' resolved to restricted/private IP address ({ip_addr}). "
                "Monitoring of private, loopback, or metadata addresses is strictly forbidden."
            )

    return url_string

def merge_headers_preserving_secrets(existing_headers_json: str | None, incoming_headers_dict: dict) -> str:
    """
    If an incoming header value contains masked characters ('•' or '••••'),
    preserve the existing unmasked secret value from the database.
    """
    if not existing_headers_json:
        return json.dumps(incoming_headers_dict)
    
    try:
        existing = json.loads(existing_headers_json)
        if not isinstance(existing, dict):
            existing = {}
    except Exception:
        existing = {}

    merged = {}
    for key, val in incoming_headers_dict.items():
        val_str = str(val)
        if "•" in val_str or "••••" in val_str:
            # Preserve original if present in existing
            if key in existing:
                merged[key] = existing[key]
            else:
                merged[key] = val
        else:
            merged[key] = val

    return json.dumps(merged)

def validate_endpoint_payload(data: dict, allow_local: bool = False, existing_endpoint = None) -> dict:
    """
    Validate and sanitize endpoint creation or update payload.
    Preserves active status and unmasked credentials if updating existing endpoint.
    """
    if not isinstance(data, dict):
        raise InputValidationError("Request body must be a JSON object.")

    # Name validation
    name = data.get("name")
    if not name or not isinstance(name, str) or not name.strip():
        raise InputValidationError("Endpoint name is required.")
    name = name.strip()
    if len(name) > 120:
        raise InputValidationError("Endpoint name must be 120 characters or fewer.")

    # URL validation with SSRF check
    raw_url = data.get("url")
    if not raw_url:
        raise InputValidationError("Endpoint URL is required.")
    validated_url = validate_url(raw_url, allow_local=allow_local)

    # Method validation
    method = str(data.get("method", "GET")).strip().upper()
    if method not in VALID_HTTP_METHODS:
        raise InputValidationError(f"Invalid HTTP method '{method}'. Allowed methods: {', '.join(sorted(VALID_HTTP_METHODS))}")

    # Timeout validation (1 to 60 seconds)
    timeout = data.get("timeout", 10)
    try:
        timeout = int(timeout)
        if timeout < 1 or timeout > 60:
            raise ValueError()
    except (ValueError, TypeError):
        raise InputValidationError("Timeout must be an integer between 1 and 60 seconds.")

    # Expected status code (0 for any 2xx, or 100-599)
    expected_status = data.get("expected_status", 200)
    try:
        expected_status = int(expected_status)
        if expected_status != 0 and (expected_status < 100 or expected_status > 599):
            raise ValueError()
    except (ValueError, TypeError):
        raise InputValidationError("Expected status code must be a valid HTTP status (100-599) or 0 (any 2xx).")

    # Check interval validation (10 to 86400 seconds)
    check_interval = data.get("check_interval", 60)
    try:
        check_interval = int(check_interval)
        if check_interval < 10 or check_interval > 86400:
            raise ValueError()
    except (ValueError, TypeError):
        raise InputValidationError("Check interval must be between 10 and 86400 seconds (minimum 10s).")

    # Headers validation
    raw_headers = data.get("headers")
    headers_dict = {}
    if raw_headers is not None:
        if isinstance(raw_headers, dict):
            headers_dict = {str(k).strip(): str(v) for k, v in raw_headers.items() if str(k).strip()}
        elif isinstance(raw_headers, str):
            trimmed = raw_headers.strip()
            if trimmed:
                try:
                    parsed = json.loads(trimmed)
                    if not isinstance(parsed, dict):
                        raise ValueError()
                    headers_dict = {str(k).strip(): str(v) for k, v in parsed.items() if str(k).strip()}
                except Exception:
                    raise InputValidationError("Headers must be a valid JSON object of key-value pairs.")
            else:
                headers_dict = {}
        else:
            raise InputValidationError("Headers must be an object or a JSON string.")

    # If updating an existing endpoint, preserve secrets if masked values were submitted
    if existing_endpoint is not None and hasattr(existing_endpoint, "headers"):
        headers_json = merge_headers_preserving_secrets(existing_endpoint.headers, headers_dict)
    else:
        headers_json = json.dumps(headers_dict)

    # Body validation
    raw_body = data.get("body")
    body_str = None
    if raw_body is not None:
        if isinstance(raw_body, str):
            body_str = raw_body
        else:
            try:
                body_str = json.dumps(raw_body)
            except Exception:
                body_str = str(raw_body)

    # Active status: if existing endpoint and is_active is omitted, preserve existing status
    if "is_active" in data:
        is_active = data["is_active"]
        if not isinstance(is_active, bool):
            is_active = str(is_active).lower() in ("true", "1", "yes")
    elif existing_endpoint is not None:
        is_active = existing_endpoint.is_active
    else:
        is_active = True

    # Tags validation
    raw_tags = data.get("tags", "")
    if isinstance(raw_tags, list):
        tags_str = ",".join(str(t).strip() for t in raw_tags if str(t).strip())
    elif isinstance(raw_tags, str):
        tags_str = ",".join(t.strip() for t in raw_tags.split(",") if t.strip())
    else:
        tags_str = ""

    return {
        "name": name,
        "url": validated_url,
        "method": method,
        "headers": headers_json,
        "body": body_str,
        "timeout": timeout,
        "expected_status": expected_status,
        "check_interval": check_interval,
        "is_active": is_active,
        "tags": tags_str,
    }
