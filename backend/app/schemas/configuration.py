"""Schemas for uploaded configurations."""

from datetime import datetime

from pydantic import BaseModel


class ConfigurationOut(BaseModel):
    id: int
    device_id: int
    filename: str
    file_size: int
    detected_vendor: str
    status: str
    upload_time: datetime

    model_config = {"from_attributes": True}


class UploadResponse(BaseModel):
    """What the frontend shows right after upload (Phase 4 demo flow)."""

    filename: str
    detected_vendor: str
    file_size: int
    line_count: int
    upload_time: datetime
    status: str
    configuration_id: int
    device_id: int
    message: str = "Ready for Audit"
