"""Normalization preview endpoint (testing + future UI)."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.normalization import NormalizedConfig, normalize_text

router = APIRouter(prefix="/api/normalize", tags=["normalize"])


class NormalizeRequest(BaseModel):
    vendor: str = Field(examples=["cisco"])
    text: str = Field(min_length=1, max_length=2 * 1024 * 1024)


@router.post("", response_model=NormalizedConfig)
def normalize(payload: NormalizeRequest):
    return normalize_text(payload.vendor, payload.text)
