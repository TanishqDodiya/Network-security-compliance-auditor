"""Schemas for unknown-syntax mappings (human-in-the-loop)."""

from datetime import datetime

from pydantic import BaseModel, Field


class MappingCreate(BaseModel):
    vendor: str = Field(default="unknown", max_length=32)
    raw_pattern: str = Field(min_length=1, examples=["set xyz secure-admin-mode enabled"])
    normalized_field: str = Field(default="", max_length=128)
    suggested_category: str = Field(default="", max_length=64)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    status: str = Field(default="pending", examples=["pending", "confirmed", "rejected"])
    confirmed_by: str = Field(default="", max_length=64)


class MappingOut(MappingCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}
