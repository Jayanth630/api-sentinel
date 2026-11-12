from datetime import datetime, timezone
from app.extensions import db

def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class CheckResult(db.Model):
    """Historical record of an individual health check ping."""
    __tablename__ = "check_results"

    id = db.Column(db.Integer, primary_key=True)
    endpoint_id = db.Column(
        db.Integer,
        db.ForeignKey("endpoints.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    checked_at = db.Column(
        db.DateTime,
        nullable=False,
        default=utc_now,
        index=True
    )
    status_code = db.Column(db.Integer, nullable=True)  # HTTP status code or None on network error
    response_time_ms = db.Column(db.Float, nullable=False)  # High-precision latency in ms
    is_success = db.Column(db.Boolean, nullable=False, default=False)
    response_size_bytes = db.Column(db.Integer, nullable=False, default=0)
    error_message = db.Column(db.Text, nullable=True)
    response_headers = db.Column(db.Text, nullable=True)  # Serialized headers summary

    def to_dict(self):
        """Serialize check result to dictionary."""
        return {
            "id": self.id,
            "endpoint_id": self.endpoint_id,
            "checked_at": (self.checked_at.isoformat() + "Z") if self.checked_at else None,
            "status_code": self.status_code,
            "response_time_ms": round(self.response_time_ms, 2) if self.response_time_ms is not None else 0.0,
            "is_success": self.is_success,
            "response_size_bytes": self.response_size_bytes,
            "error_message": self.error_message,
        }

    def __repr__(self):
        return f"<CheckResult #{self.id} endpoint={self.endpoint_id} code={self.status_code} {self.response_time_ms}ms>"
