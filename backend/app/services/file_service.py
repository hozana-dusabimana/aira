from __future__ import annotations

import os
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.config import settings


ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def _ensure_upload_dir() -> Path:
    p = Path(settings.UPLOAD_DIR).resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def save_upload(upload: UploadFile) -> tuple[str, bytes]:
    """Validate and save an uploaded image. Returns (relative_url, raw_bytes)."""
    if upload.content_type not in ALLOWED_MIME:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported content type: {upload.content_type}",
        )

    ext = os.path.splitext(upload.filename or "")[1].lower()
    if ext not in ALLOWED_EXT:
        ext = ".jpg"

    contents = upload.file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
    if len(contents) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {settings.MAX_UPLOAD_BYTES} bytes",
        )

    name = f"{uuid.uuid4().hex}{ext}"
    folder = _ensure_upload_dir()
    full_path = folder / name
    full_path.write_bytes(contents)
    return f"/uploads/{name}", contents
