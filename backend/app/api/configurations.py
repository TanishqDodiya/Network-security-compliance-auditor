"""Configuration upload API.

Security rules for the MVP (read-only audit platform):
- Only .txt / .conf / .cfg files.
- Reject empty files and files over 2 MB.
- Sanitize filenames (no folders, no weird characters).
- Treat content as untrusted TEXT: decode, store, never execute.
- Deterministic vendor detection (Phase 5): no AI, pattern scoring.
"""

import os
import re
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.configuration import Configuration
from app.models.device import Device
from app.schemas.configuration import ConfigurationOut, UploadResponse
from app.services.vendor_detector import detect_vendor

router = APIRouter(prefix="/api/configurations", tags=["configurations"])

ALLOWED_EXTENSIONS = {".txt", ".conf", ".cfg"}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB
MAX_LINES = 20000  # Prevents giant files from bloating the PostgreSQL DB.


def sanitize_filename(filename: str) -> str:
    """Keep only the base name and safe characters (letters, digits, . _ -)."""
    base = os.path.basename(filename or "upload.txt").strip() or "upload.txt"
    # Reject hidden tricks like null bytes early (binary / path attacks).
    base = base.replace("\x00", "")
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", base)
    safe = safe.strip("._") or "upload.txt"
    return safe[:255]


def sanitize_device_name(name: str | None, fallback: str) -> str:
    """Device names come from users, so clean them the same way."""
    raw = (name or fallback or "device").strip() or "device"
    raw = raw.replace("\x00", "")
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", raw).strip("._") or "device"
    return safe[:128]


@router.post("/upload", response_model=UploadResponse, status_code=201)
async def upload_configuration(
    file: UploadFile = File(...),
    device_name: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    filename = sanitize_filename(file.filename or "upload.txt")
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{ext}'. Allowed: .txt, .conf, .cfg",
        )

    raw_bytes = await file.read()
    if len(raw_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Max 2 MB.")
    if len(raw_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file. Upload a non-empty config.")
    # Binary files (images, executables) contain null bytes. Configs never should.
    if b"\x00" in raw_bytes:
        raise HTTPException(status_code=400, detail="Binary file not allowed. Upload text config.")

    # Decode as text only. Never execute uploaded content.
    try:
        raw_text = raw_bytes.decode("utf-8", errors="replace")
    except Exception:
        raise HTTPException(status_code=400, detail="Could not read file as text.")
    # Normalize line endings so later parsers see consistent lines.
    raw_text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    if not raw_text.strip():
        raise HTTPException(status_code=400, detail="Empty file. Upload a non-empty config.")
    line_count = raw_text.count("\n") + 1
    if line_count > MAX_LINES:
        raise HTTPException(
            status_code=400, detail=f"Too many lines ({line_count}). Max {MAX_LINES}."
        )

    # Device: use given name or derive from filename. Get-or-create.
    fallback = os.path.splitext(filename)[0] or "device"
    name = sanitize_device_name(device_name, fallback)
    # Deterministic vendor detection (Phase 5). No AI, works offline.
    detected = detect_vendor(raw_text).vendor
    device = db.query(Device).filter_by(name=name).first()
    if not device:
        device = Device(name=name, vendor=detected)
        db.add(device)
        db.commit()
        db.refresh(device)
    elif device.vendor == "unknown" and detected != "unknown":
        # First upload said unknown; now we know better. Keep history honest.
        device.vendor = detected
        db.commit()

    config = Configuration(
        device_id=device.id,
        filename=filename,
        file_size=len(raw_bytes),
        detected_vendor=detected,
        raw_content=raw_text,
        status="ready",
        upload_time=datetime.utcnow(),
    )
    db.add(config)
    db.commit()
    db.refresh(config)

    return UploadResponse(
        filename=config.filename,
        detected_vendor=config.detected_vendor,
        file_size=config.file_size,
        line_count=line_count,
        upload_time=config.upload_time,
        status="Ready for Audit",
        configuration_id=config.id,
        device_id=device.id,
    )


@router.get("", response_model=list[ConfigurationOut])
def list_configurations(db: Session = Depends(get_db)):
    return db.query(Configuration).order_by(Configuration.id.desc()).all()
