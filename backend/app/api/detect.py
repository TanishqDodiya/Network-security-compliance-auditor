"""Standalone vendor-detection endpoint (useful for testing + future UI preview)."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.vendor_detector import detect_vendor

router = APIRouter(prefix="/api/detect", tags=["detect"])


class DetectRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2 * 1024 * 1024)


class DetectResponse(BaseModel):
    vendor: str
    confidence: float
    evidence: list[str]
    scores: dict[str, int]


@router.post("", response_model=DetectResponse)
def detect(payload: DetectRequest):
    result = detect_vendor(payload.text)
    return DetectResponse(
        vendor=result.vendor,
        confidence=result.confidence,
        evidence=result.evidence,
        scores=result.scores,
    )
