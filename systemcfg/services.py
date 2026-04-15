from __future__ import annotations

import mimetypes
import os
import uuid
from pathlib import Path

import boto3
import requests
from django.conf import settings

from .models import SystemStorageSetting


def get_active_storage_setting() -> SystemStorageSetting:
    cfg = SystemStorageSetting.objects.filter(is_active=True).order_by("-updated_at").first()
    if cfg:
        return cfg
    return SystemStorageSetting.objects.create(name="default", backend=SystemStorageSetting.Backend.LOCAL)


def _safe_ext(filename: str) -> str:
    ext = Path(filename).suffix.lower()[:10]
    return ext if ext else ".bin"


def save_uploaded_bytes(content: bytes, original_filename: str) -> str:
    return save_uploaded_bytes_with_meta(content, original_filename)["url"]


def save_uploaded_bytes_with_meta(content: bytes, original_filename: str) -> dict:
    cfg = get_active_storage_setting()
    ext = _safe_ext(original_filename)
    object_name = f"{uuid.uuid4().hex}{ext}"

    if cfg.backend == SystemStorageSetting.Backend.S3 and cfg.s3_bucket:
        client = boto3.client(
            "s3",
            endpoint_url=cfg.s3_endpoint_url or None,
            aws_access_key_id=cfg.s3_access_key or None,
            aws_secret_access_key=cfg.s3_secret_key or None,
            region_name=cfg.s3_region or None,
        )
        key = f"{(cfg.local_subdir or 'uploads').strip('/')}/{object_name}"
        content_type, _ = mimetypes.guess_type(original_filename)
        client.put_object(Bucket=cfg.s3_bucket, Key=key, Body=content, ContentType=content_type or "application/octet-stream")
        if cfg.s3_base_url:
            return {"url": f"{cfg.s3_base_url.rstrip('/')}/{key}", "backend": cfg.backend, "object_key": key}
        if cfg.s3_endpoint_url:
            return {
                "url": f"{cfg.s3_endpoint_url.rstrip('/')}/{cfg.s3_bucket}/{key}",
                "backend": cfg.backend,
                "object_key": key,
            }
        return {"url": f"/media/{key}", "backend": cfg.backend, "object_key": key}

    if cfg.backend == SystemStorageSetting.Backend.WEBDAV and cfg.webdav_base_url:
        upload_path = (cfg.webdav_upload_path or "uploads/").strip("/") + "/"
        url = f"{cfg.webdav_base_url.rstrip('/')}/{upload_path}{object_name}"
        r = requests.put(url, data=content, auth=(cfg.webdav_username, cfg.webdav_password), timeout=30)
        r.raise_for_status()
        return {"url": url, "backend": cfg.backend, "object_key": f"{upload_path}{object_name}"}

    # local default
    local_subdir = (cfg.local_subdir or "uploads").strip("/\\")
    base_path = Path(settings.MEDIA_ROOT) / local_subdir
    os.makedirs(base_path, exist_ok=True)
    file_path = base_path / object_name
    with open(file_path, "wb") as f:
        f.write(content)

    if cfg.local_base_url:
        return {
            "url": f"{cfg.local_base_url.rstrip('/')}/{local_subdir}/{object_name}",
            "backend": cfg.backend,
            "object_key": f"{local_subdir}/{object_name}",
        }
    return {"url": f"{settings.MEDIA_URL}{local_subdir}/{object_name}", "backend": cfg.backend, "object_key": f"{local_subdir}/{object_name}"}

