import json
from datetime import datetime, timezone
from app.extensions import db

def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class Endpoint(db.Model):
    """Monitored API Endpoint model."""
    __tablename__ = "endpoints"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    url = db.Column(db.String(2048), nullable=False)
    method = db.Column(db.String(10), nullable=False, default="GET")
    headers = db.Column(db.Text, nullable=True, default="{}")  # Stored as JSON string
    body = db.Column(db.Text, nullable=True)  # Optional request body
    timeout = db.Column(db.Integer, nullable=False, default=10)  # Seconds (1-60)
    expected_status = db.Column(db.Integer, nullable=False, default=200)  # e.g., 200, 201, 204 or 0 (any 2xx)
    check_interval = db.Column(db.Integer, nullable=False, default=60)  # Seconds between checks
    is_active = db.Column(db.Boolean, nullable=False, default=True)  # Enable/pause monitoring
    tags = db.Column(db.String(255), nullable=True, default="")  # Comma-separated tags (e.g. "auth,prod")
    
    # State tracking
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)
    last_checked_at = db.Column(db.DateTime, nullable=True)
    last_status = db.Column(db.String(20), nullable=False, default="unknown")  # 'healthy', 'degraded', 'down', 'unknown'
    last_status_code = db.Column(db.Integer, nullable=True)
    last_response_time_ms = db.Column(db.Float, nullable=True)
    last_error_message = db.Column(db.Text, nullable=True)
    consecutive_failures = db.Column(db.Integer, nullable=False, default=0)
    uptime_percentage = db.Column(db.Float, nullable=False, default=100.0)

    # Relationships
    check_results = db.relationship(
        "CheckResult",
        backref="endpoint",
        lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="desc(CheckResult.checked_at)"
    )
    incidents = db.relationship(
        "Incident",
        backref="endpoint",
        lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="desc(Incident.started_at)"
    )

    def get_headers_dict(self):
        """Safely parse headers from JSON string."""
        if not self.headers:
            return {}
        try:
            parsed = json.loads(self.headers)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}

    def get_masked_headers(self):
        """Return headers with sensitive tokens masked for safe display."""
        headers = self.get_headers_dict()
        masked = {}
        sensitive_keys = {
            "authorization", "proxy-authorization", "token", "api-key",
            "x-api-key", "secret", "password", "app-key", "access-token"
        }
        for k, v in headers.items():
            key_lower = str(k).lower()
            val_str = str(v)
            if any(s in key_lower for s in sensitive_keys) and len(val_str) > 6:
                masked[k] = val_str[:3] + "•" * (len(val_str) - 6) + val_str[-3:]
            elif any(s in key_lower for s in sensitive_keys):
                masked[k] = "••••••••"
            else:
                masked[k] = v
        return masked

    def get_tags_list(self):
        """Return list of tags."""
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(",") if t.strip()]

    def to_dict(self, include_masked_headers=True):
        """Serialize endpoint to dictionary."""
        masked_headers = self.get_masked_headers()
        masked_raw_headers = json.dumps(masked_headers, indent=2) if masked_headers else "{}"
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "method": self.method.upper(),
            "headers": masked_headers if include_masked_headers else self.get_headers_dict(),
            "raw_headers": masked_raw_headers if include_masked_headers else (self.headers or "{}"),
            "body": self.body or "",
            "timeout": self.timeout,
            "expected_status": self.expected_status,
            "check_interval": self.check_interval,
            "is_active": self.is_active,
            "tags": self.get_tags_list(),
            "raw_tags": self.tags or "",
            "created_at": (self.created_at.isoformat() + "Z") if self.created_at else None,
            "updated_at": (self.updated_at.isoformat() + "Z") if self.updated_at else None,
            "last_checked_at": (self.last_checked_at.isoformat() + "Z") if self.last_checked_at else None,
            "last_status": self.last_status,
            "last_status_code": self.last_status_code,
            "last_response_time_ms": round(self.last_response_time_ms, 2) if self.last_response_time_ms is not None else None,
            "last_error_message": self.last_error_message,
            "consecutive_failures": self.consecutive_failures,
            "uptime_percentage": round(self.uptime_percentage, 2) if self.uptime_percentage is not None else 100.0
        }

    def __repr__(self):
        return f"<Endpoint #{self.id} {self.method} {self.name} [{self.last_status}]>"
