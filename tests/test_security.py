import pytest
from unittest.mock import patch
from app.services.security import (
    validate_url,
    validate_endpoint_payload,
    is_ip_private_or_restricted,
    SecurityValidationError,
    InputValidationError
)

def test_ip_restriction_filter():
    # Loopback
    assert is_ip_private_or_restricted("127.0.0.1") is True
    assert is_ip_private_or_restricted("::1") is True

    # Private RFC 1918
    assert is_ip_private_or_restricted("10.0.0.1") is True
    assert is_ip_private_or_restricted("172.16.1.1") is True
    assert is_ip_private_or_restricted("192.168.1.1") is True

    # Link-Local & AWS/GCP/Azure Metadata
    assert is_ip_private_or_restricted("169.254.169.254") is True
    assert is_ip_private_or_restricted("fe80::1") is True

    # Carrier NAT & Multicast
    assert is_ip_private_or_restricted("100.64.0.1") is True
    assert is_ip_private_or_restricted("224.0.0.1") is True

    # Valid Public IPs (Cloudflare, Google DNS)
    assert is_ip_private_or_restricted("1.1.1.1") is False
    assert is_ip_private_or_restricted("8.8.8.8") is False

def test_url_ssrf_rejections():
    # Non-HTTP/HTTPS schemes
    with pytest.raises(SecurityValidationError, match="Scheme 'ftp' is not allowed"):
        validate_url("ftp://example.com/file.txt")

    with pytest.raises(SecurityValidationError, match="Scheme 'file' is not allowed"):
        validate_url("file:///etc/passwd")

    with pytest.raises(SecurityValidationError, match="Scheme 'gopher' is not allowed"):
        validate_url("gopher://127.0.0.1:70")

    # Localhost and internal hostnames
    with pytest.raises(SecurityValidationError, match="Access to internal host"):
        validate_url("http://localhost:5000/api")

    with pytest.raises(SecurityValidationError, match="Access to internal host"):
        validate_url("http://127.0.0.1:8080")

    with pytest.raises(SecurityValidationError):
        validate_url("http://metadata.google.internal/computeMetadata/v1/")

    with pytest.raises(SecurityValidationError):
        validate_url("http://169.254.169.254/latest/meta-data")

def test_url_allow_local_override():
    # When allow_local is True, localhost is permitted for dev/test
    url = validate_url("http://localhost:5000/test", allow_local=True)
    assert url == "http://localhost:5000/test"

def test_valid_public_url():
    with patch("socket.getaddrinfo", return_value=[(2, 1, 0, "", ("93.184.216.34", 443))]):
        url = validate_url("https://example.com/test")
        assert url == "https://example.com/test"

def test_endpoint_payload_validation_success():
    payload = {
        "name": "Stripe Webhooks",
        "url": "https://example.com/v1/health",
        "method": "POST",
        "expected_status": 200,
        "timeout": 15,
        "check_interval": 30,
        "headers": {"Content-Type": "application/json"},
        "body": '{"event": "ping"}',
        "tags": "payments, prod"
    }
    with patch("socket.getaddrinfo", return_value=[(2, 1, 0, "", ("93.184.216.34", 443))]):
        validated = validate_endpoint_payload(payload)
    assert validated["name"] == "Stripe Webhooks"
    assert validated["method"] == "POST"
    assert validated["timeout"] == 15
    assert validated["check_interval"] == 30
    assert validated["tags"] == "payments,prod"
    assert '"Content-Type": "application/json"' in validated["headers"]

def test_endpoint_payload_invalid_inputs():
    with patch("socket.getaddrinfo", return_value=[(2, 1, 0, "", ("93.184.216.34", 443))]):
        # Missing name
        with pytest.raises(InputValidationError, match="Endpoint name is required"):
            validate_endpoint_payload({"url": "https://example.com"})

        # Invalid method
        with pytest.raises(InputValidationError, match="Invalid HTTP method"):
            validate_endpoint_payload({"name": "Test", "url": "https://example.com", "method": "INVALID"})

        # Invalid timeout bounds
        with pytest.raises(InputValidationError, match="Timeout must be an integer between 1 and 60"):
            validate_endpoint_payload({"name": "Test", "url": "https://example.com", "timeout": 120})

        # Invalid interval
        with pytest.raises(InputValidationError, match="Check interval must be between 10 and 86400"):
            validate_endpoint_payload({"name": "Test", "url": "https://example.com", "check_interval": 2})

        # Malformed headers JSON
        with pytest.raises(InputValidationError, match="Headers must be a valid JSON object"):
            validate_endpoint_payload({"name": "Test", "url": "https://example.com", "headers": "{not valid json}"})
