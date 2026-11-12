import os
import atexit
from flask import Flask, jsonify, request
from sqlalchemy import event
from sqlalchemy.engine import Engine
from app.config import config_by_name
from app.extensions import db
from app.services.scheduler import scheduler
import app.models  # Imported at module level so it never overwrites local variables

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enforce foreign key constraints on SQLite connections."""
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception:
        pass

def create_app(config_name=None):
    """Application factory for API Sentinel."""
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")

    flask_app = Flask(__name__)
    flask_app.config.from_object(config_by_name.get(config_name, config_by_name["default"]))

    # Initialize extensions
    db.init_app(flask_app)

    # Register blueprints
    from app.routes.api import api_bp
    from app.routes.web import web_bp
    flask_app.register_blueprint(api_bp)
    flask_app.register_blueprint(web_bp)

    # Create tables
    with flask_app.app_context():
        db.create_all()

    # Start background scheduler if enabled
    if flask_app.config.get("ENABLE_BACKGROUND_SCHEDULER") and not flask_app.config.get("TESTING"):
        scheduler.init_app(flask_app)
        scheduler.start()
        # Clean shutdown on process exit
        atexit.register(scheduler.stop)

    # Safe error handlers
    @flask_app.errorhandler(404)
    def not_found_handler(e):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "Requested API endpoint not found"}), 404
        return jsonify({"success": False, "error": "Page not found"}), 404

    @flask_app.errorhandler(500)
    def internal_error_handler(e):
        return jsonify({"success": False, "error": "Internal server error occurred"}), 500

    return flask_app
