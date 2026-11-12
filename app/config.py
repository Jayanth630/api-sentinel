import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(parents=True, exist_ok=True)

class Config:
    """Base application configuration."""
    SECRET_KEY = os.getenv("SECRET_KEY", "api-sentinel-default-secret-key-2026")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # SQLite default path inside instance/
    DEFAULT_DB_PATH = f"sqlite:///{INSTANCE_DIR / 'api_sentinel.db'}"
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", DEFAULT_DB_PATH)
    
    # Fix postgres:// URL prefix for SQLAlchemy if deployed to Render/Heroku with PostgreSQL
    if SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)

    # Scheduler settings
    SCHEDULER_INTERVAL_SECONDS = int(os.getenv("SCHEDULER_INTERVAL_SECONDS", "10"))
    ENABLE_BACKGROUND_SCHEDULER = os.getenv("ENABLE_BACKGROUND_SCHEDULER", "true").lower() in ("true", "1", "yes")

    # Security settings
    ALLOW_LOCAL_MONITORING = os.getenv("ALLOW_LOCAL_MONITORING", "false").lower() in ("true", "1", "yes")
    MAX_REQUEST_TIMEOUT = 60
    MIN_REQUEST_TIMEOUT = 1
    DEFAULT_REQUEST_TIMEOUT = 10
    MAX_RESPONSE_BODY_SIZE = 512 * 1024  # 512 KB

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False

class TestingConfig(Config):
    DEBUG = False
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    ENABLE_BACKGROUND_SCHEDULER = False
    ALLOW_LOCAL_MONITORING = False

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False

config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig
}
