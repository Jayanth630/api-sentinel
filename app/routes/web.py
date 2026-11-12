from flask import Blueprint, render_template, current_app

web_bp = Blueprint("web", __name__)

@web_bp.route("/")
def index():
    """Render the main API Sentinel application interface."""
    return render_template(
        "index.html",
        app_name="API Sentinel",
        version="1.0.0",
        allow_local=current_app.config.get("ALLOW_LOCAL_MONITORING", False)
    )

@web_bp.route("/health")
def health_check():
    """System self-health check endpoint for Render/Kubernetes probes."""
    return {"status": "ok", "service": "api-sentinel"}
