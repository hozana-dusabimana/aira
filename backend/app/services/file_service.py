from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.config import settings


logger = logging.getLogger(__name__)

ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

# Sub-folder of UPLOAD_DIR where rejected ("spam") uploads are quarantined.
SPAM_SUBDIR = "spam"


def _ensure_upload_dir() -> Path:
    p = Path(settings.UPLOAD_DIR).resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def _resolve_upload_path(image_url: str) -> Path:
    """Map a stored ``/uploads/...`` URL back to its absolute file path."""
    rel = image_url.lstrip("/")
    path = Path(settings.UPLOAD_DIR).resolve().parent / rel
    if not path.exists():
        # Fall back to a flat layout (file directly under UPLOAD_DIR).
        path = Path(settings.UPLOAD_DIR).resolve() / Path(rel).name
    return path


def unquarantine_upload_file(image_url: str | None) -> str | None:
    """Move a quarantined upload back out of the spam folder.

    The inverse of :func:`quarantine_upload_file`, used when an officer marks a
    spam report as "not spam". Returns the restored ``/uploads/<file>`` URL, or
    ``None`` if the file could not be found/moved (caller keeps the spam URL).
    Best-effort: never raises.
    """
    if not image_url:
        return None
    try:
        src = _resolve_upload_path(image_url)
        if not src.exists():
            logger.warning("Cannot restore missing spam upload: %s", image_url)
            return None
        dest = _ensure_upload_dir() / src.name
        src.replace(dest)
        return f"/uploads/{src.name}"
    except Exception:  # noqa: BLE001
        logger.exception("Could not restore spam upload: %s", image_url)
        return None


def quarantine_upload_file(image_url: str | None) -> str | None:
    """Move a rejected upload into the spam folder instead of deleting it.

    Returns the new ``/uploads/spam/<file>`` URL on success, or ``None`` if the
    source file could not be found/moved (in which case the caller should keep
    the original URL). Best-effort: never raises.
    """
    if not image_url:
        return None
    try:
        src = _resolve_upload_path(image_url)
        if not src.exists():
            logger.warning("Cannot quarantine missing upload: %s", image_url)
            return None
        spam_dir = _ensure_upload_dir() / SPAM_SUBDIR
        spam_dir.mkdir(parents=True, exist_ok=True)
        dest = spam_dir / src.name
        src.replace(dest)
        return f"/uploads/{SPAM_SUBDIR}/{src.name}"
    except Exception:  # noqa: BLE001
        logger.exception("Could not quarantine rejected upload: %s", image_url)
        return None


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
