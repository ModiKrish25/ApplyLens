import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    # Managed Postgres (e.g. DATABASE_URL injected by the platform) wins when
    # present; SQLite keeps local development zero-config.
    _db_url = os.environ.get("DATABASE_URL", "")
    if _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = _db_url or "sqlite:///" + os.path.join(BASE_DIR, "instance", "app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.path.join(BASE_DIR, "instance", "uploads")
    REPORT_FOLDER = os.path.join(BASE_DIR, "instance", "reports")
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB
    ALLOWED_EXTENSIONS = {"pdf", "docx"}

    # S3-compatible object storage (Cloudflare R2, AWS S3, MinIO, ...).
    # When S3_BUCKET is unset, uploads fall back to local disk (dev only).
    S3_ENDPOINT_URL = os.environ.get("S3_ENDPOINT_URL", "")
    S3_BUCKET = os.environ.get("S3_BUCKET", "")
    S3_ACCESS_KEY_ID = os.environ.get("S3_ACCESS_KEY_ID", "")
    S3_SECRET_ACCESS_KEY = os.environ.get("S3_SECRET_ACCESS_KEY", "")
    S3_REGION = os.environ.get("S3_REGION", "auto")
