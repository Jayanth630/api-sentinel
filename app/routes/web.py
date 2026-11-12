from flask import Blueprint, render_template, current_app

web_bp = Blueprint("web", __name__)

@web_bp.route("/")
def index():
    """Render the professional API Sentinel Welcome / Landing Page."""
    return render_template(
        "landing.html",
        app_name="API Sentinel",
        version="1.0.0"
    )

@web_bp.route("/dashboard")
@web_bp.route("/app")
def dashboard():
    """Render the main API Sentinel application dashboard interface."""
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
