"""File storage for uploads.

Uses an S3-compatible bucket (Cloudflare R2, AWS S3, MinIO, ...) when
S3_BUCKET is configured, and falls back to local disk otherwise. Local disk
is fine for development but never survives a redeploy on a PaaS.
"""
import os

from flask import current_app

_MISSING = ("404", "NoSuchKey", "NotFound")


def s3_enabled():
    return bool(current_app.config.get("S3_BUCKET"))


def _client():
    import boto3  # imported lazily so local dev works without boto3 installed

    cfg = current_app.config
    return boto3.client(
        "s3",
        endpoint_url=cfg.get("S3_ENDPOINT_URL") or None,
        aws_access_key_id=cfg.get("S3_ACCESS_KEY_ID") or None,
        aws_secret_access_key=cfg.get("S3_SECRET_ACCESS_KEY") or None,
        region_name=cfg.get("S3_REGION", "auto"),
    )


def save_bytes(key, data, content_type="application/octet-stream"):
    """Store bytes under `key` (e.g. "u1_ab12cd34ef56.pdf")."""
    if s3_enabled():
        _client().put_object(
            Bucket=current_app.config["S3_BUCKET"], Key=key,
            Body=data, ContentType=content_type,
        )
        return
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], key)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


def open_file(key):
    """Return a binary file-like object for the stored file."""
    if s3_enabled():
        from io import BytesIO
        obj = _client().get_object(Bucket=current_app.config["S3_BUCKET"], Key=key)
        return BytesIO(obj["Body"].read())
    return open(os.path.join(current_app.config["UPLOAD_FOLDER"], key), "rb")


def exists(key):
    if not key:
        return False
    if s3_enabled():
        try:
            _client().head_object(Bucket=current_app.config["S3_BUCKET"], Key=key)
            return True
        except Exception as e:
            code = getattr(getattr(e, "response", None), "get", lambda *_: {}) \
                ("Error", {}).get("Code", "")
            return code not in _MISSING
    return os.path.exists(os.path.join(current_app.config["UPLOAD_FOLDER"], key))


def delete_file(key):
    if not key:
        return
    if s3_enabled():
        _client().delete_object(Bucket=current_app.config["S3_BUCKET"], Key=key)
        return
    try:
        os.remove(os.path.join(current_app.config["UPLOAD_FOLDER"], key))
    except OSError:
        pass
