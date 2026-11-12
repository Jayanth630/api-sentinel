from datetime import datetime, timezone
from app.extensions import db

def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class Incident(db.Model):
    """Tracks downtime incidents from failure detection until recovery."""
    __tablename__ = "incidents"

    id = db.Column(db.Integer, primary_key=True)
    endpoint_id = db.Column(
        db.Integer,
        db.ForeignKey("endpoints.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    started_at = db.Column(
        db.DateTime,
        nullable=False,
        default=utc_now,
        index=True
    )
    resolved_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    error_message = db.Column(db.Text, nullable=False)
    last_status_code = db.Column(db.Integer, nullable=True)
    duration_seconds = db.Column(db.Integer, nullable=True)

    def resolve(self):
        """Mark incident as resolved and compute duration."""
        self.resolved_at = utc_now()
        self.is_active = False
        if self.started_at and self.resolved_at:
            delta = (self.resolved_at - self.started_at).total_seconds()
            self.duration_seconds = max(1, int(delta))

    def to_dict(self):
        """Serialize incident to dictionary."""
        return {
            "id": self.id,
            "endpoint_id": self.endpoint_id,
            "endpoint_name": self.endpoint.name if self.endpoint else "Unknown",
            "endpoint_url": self.endpoint.url if self.endpoint else "",
            "started_at": (self.started_at.isoformat() + "Z") if self.started_at else None,
            "resolved_at": (self.resolved_at.isoformat() + "Z") if self.resolved_at else None,
            "is_active": self.is_active,
            "error_message": self.error_message,
            "last_status_code": self.last_status_code,
            "duration_seconds": self.duration_seconds,
        }

    def __repr__(self):
        return f"<Incident #{self.id} endpoint={self.endpoint_id} active={self.is_active}>"
