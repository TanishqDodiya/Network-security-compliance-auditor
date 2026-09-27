"""Mapping review service: stored knowledge BEFORE AI (never retraining).

Beginner idea: when an unknown line appears we check the notebook first.
- Confirmed mapping exists -> reuse it, no AI call, no human needed.
- Pending mapping exists -> show it for review, no new AI call.
- Nothing stored -> ask AI for a suggestion (still needs human confirmation).
This is "learning through a stored mapping layer", NOT model retraining.
"""

from sqlalchemy.orm import Session

from app.ai.service import analyze_unknown
from app.models.unknown_mapping import UnknownMapping


def find_mapping(db: Session, vendor: str, raw_pattern: str) -> UnknownMapping | None:
    """Exact lookup on (vendor, raw_pattern). Case-insensitive vendor."""
    return (
        db.query(UnknownMapping)
        .filter_by(vendor=(vendor or "unknown").lower(), raw_pattern=raw_pattern)
        .first()
    )


def resolve_unknown(db: Session, vendor: str, raw_pattern: str) -> dict:
    """Return a suggestion, preferring stored knowledge over AI."""
    vendor = (vendor or "unknown").lower()
    stored = find_mapping(db, vendor, raw_pattern)
    if stored and stored.status == "confirmed":
        return {
            "source": "stored",
            "mapping_id": stored.id,
            "vendor": stored.vendor,
            "raw_pattern": stored.raw_pattern,
            "suggested_category": stored.suggested_category,
            "suggested_field": stored.normalized_field,
            "confidence": stored.confidence,
            "requires_confirmation": False,
            "message": "Reused confirmed mapping. No AI call, no review needed.",
        }
    if stored:  # pending or rejected: show it instead of calling AI again
        return {
            "source": "stored",
            "mapping_id": stored.id,
            "vendor": stored.vendor,
            "raw_pattern": stored.raw_pattern,
            "suggested_category": stored.suggested_category,
            "suggested_field": stored.normalized_field,
            "confidence": stored.confidence,
            "requires_confirmation": stored.status != "rejected",
            "status": stored.status,
            "message": f"Existing mapping is '{stored.status}'. Review it instead of creating a duplicate.",
        }
    ai = analyze_unknown(raw_pattern, vendor)
    return {
        "source": "ai",
        "mapping_id": None,
        "vendor": vendor,
        "raw_pattern": raw_pattern,
        "suggested_category": ai["suggested_category"],
        "suggested_field": ai["suggested_field"],
        "confidence": ai["confidence"],
        "meaning": ai["meaning"],
        "requires_confirmation": True,
        "ai_available": ai["ai_available"],
        "message": "AI suggestion. Confirm or correct it to save for reuse.",
    }
