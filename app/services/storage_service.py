from __future__ import annotations

import os
import time
from pathlib import Path
from urllib.parse import quote

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename


def _allowed_extension(filename: str) -> bool:
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in current_app.config["ALLOWED_EXTENSIONS"]


def _local_root() -> Path:
    root = Path(current_app.config["LOCAL_STORAGE_PATH"]).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _object_key(office_id, entity_type: str, entity_id, filename: str):
    timestamp = int(time.time())
    safe_name = secure_filename(filename)
    return f"{office_id}/{entity_type}/{entity_id}/{timestamp}_{safe_name}"


def _s3_client():
    try:
        import boto3
        from botocore.client import Config as BotoConfig
    except ImportError as exc:
        raise RuntimeError("boto3 is required when STORAGE_BACKEND is set to s3") from exc

    return boto3.client(
        "s3",
        region_name=current_app.config.get("S3_REGION"),
        aws_access_key_id=current_app.config.get("S3_ACCESS_KEY_ID"),
        aws_secret_access_key=current_app.config.get("S3_SECRET_ACCESS_KEY"),
        endpoint_url=current_app.config.get("S3_ENDPOINT_URL"),
        config=BotoConfig(signature_version="s3v4"),
    )


def upload_file(file: FileStorage, office_id, entity_type: str, entity_id):
    if not file:
        raise ValueError("No file provided")
    if not _allowed_extension(file.filename or ""):
        raise ValueError("File extension not allowed")

    key = _object_key(office_id, entity_type, entity_id, file.filename)
    backend = current_app.config.get("STORAGE_BACKEND", "local")

    if backend == "s3":
        bucket = current_app.config["S3_BUCKET"]
        _s3_client().upload_fileobj(file.stream, bucket, key)
        return f"s3://{bucket}/{key}", key

    root = _local_root()
    full_path = root / key
    full_path.parent.mkdir(parents=True, exist_ok=True)
    file.save(full_path)
    return str(full_path), key


def build_download_url(file_url: str, key: str):
    backend = current_app.config.get("STORAGE_BACKEND", "local")
    if backend == "s3":
        bucket = current_app.config["S3_BUCKET"]
        client = _s3_client()
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=24 * 3600,
        )
    return f"/files/{quote(key)}"


def build_preview_url(file_url: str, key: str):
    return build_download_url(file_url, key)


def delete_file(file_url: str, key: str):
    backend = current_app.config.get("STORAGE_BACKEND", "local")
    if backend == "s3":
        bucket = current_app.config["S3_BUCKET"]
        _s3_client().delete_object(Bucket=bucket, Key=key)
        return

    path = Path(file_url)
    if path.exists():
        path.unlink()
