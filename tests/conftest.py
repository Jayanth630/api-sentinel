import pytest
import socket
from unittest.mock import patch
from app import create_app
from app.extensions import db
from app.models.endpoint import Endpoint
from app.models.check_result import CheckResult
from app.models.incident import Incident

@pytest.fixture(autouse=True)
def mock_dns_resolution():
    """Mock DNS resolution for standard public test hosts so tests run reliably offline."""
    real_getaddrinfo = socket.getaddrinfo

    def mocked_getaddrinfo(host, port, *args, **kwargs):
        host_lower = str(host).lower()
        if host_lower in ("api.github.com", "example.com", "api.stripe.com", "httpbin.org"):
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port or 443))]
        return real_getaddrinfo(host, port, *args, **kwargs)

    with patch("socket.getaddrinfo", side_effect=mocked_getaddrinfo):
        yield

@pytest.fixture
def app():
    """Create application configured for testing."""
    test_app = create_app("testing")
    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """Test client for HTTP requests."""
    return app.test_client()

@pytest.fixture
def sample_endpoint(app):
    """Create a sample endpoint in the database."""
    ep = Endpoint(
        name="Test API",
        url="https://api.github.com",
        method="GET",
        headers='{"Accept": "application/json"}',
        timeout=10,
        expected_status=200,
        check_interval=60,
        is_active=True,
        tags="test,core"
    )
    db.session.add(ep)
    db.session.commit()
    return ep
