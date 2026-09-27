"""Mappings API: human-in-the-loop confirmations for unknown syntax."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.unknown_mapping import UnknownMapping
from app.schemas.mapping import MappingCreate, MappingOut
from app.services.mapping_review import find_mapping, resolve_unknown

router = APIRouter(prefix="/api/mappings", tags=["mappings"])


class ResolveRequest(BaseModel):
    vendor: str = "unknown"
    raw_pattern: str = Field(min_length=1, max_length=2000)


class ReviewUpdate(BaseModel):
    """Confirm / reject / choose-category for a pending mapping."""

    status: str = Field(examples=["confirmed", "rejected"])
    normalized_field: str | None = None
    suggested_category: str | None = None
    confirmed_by: str = ""


@router.get("", response_model=list[MappingOut])
def list_mappings(status: str | None = None, db: Session = Depends(get_db)):
    """Review queue: filter with ?status=pending | confirmed | rejected."""
    query = db.query(UnknownMapping).order_by(UnknownMapping.id.desc())
    if status:
        if status not in {"pending", "confirmed", "rejected"}:
            raise HTTPException(status_code=400, detail="Invalid status filter")
        query = query.filter_by(status=status)
    return query.all()


@router.post("", response_model=MappingOut, status_code=201)
def create_mapping(payload: MappingCreate, db: Session = Depends(get_db)):
    if payload.status not in {"pending", "confirmed", "rejected"}:
        raise HTTPException(status_code=400, detail="Invalid status")
    mapping = UnknownMapping(
        vendor=payload.vendor.lower() or "unknown",
        raw_pattern=payload.raw_pattern,
        normalized_field=payload.normalized_field,
        suggested_category=payload.suggested_category,
        confidence=payload.confidence,
        status=payload.status,
        confirmed_by=payload.confirmed_by,
    )
    db.add(mapping)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Mapping for this vendor+pattern already exists"
        )
    db.refresh(mapping)
    return mapping


@router.post("/resolve")
def resolve(payload: ResolveRequest, db: Session = Depends(get_db)):
    """Check stored mappings first; only call AI when nothing is stored."""
    return resolve_unknown(db, payload.vendor, payload.raw_pattern)


@router.patch("/{mapping_id}", response_model=MappingOut)
def review_mapping(mapping_id: int, payload: ReviewUpdate, db: Session = Depends(get_db)):
    """Human confirms or rejects: PATCH /api/mappings/{id} {status, ...}."""
    if payload.status not in {"confirmed", "rejected", "pending"}:
        raise HTTPException(status_code=400, detail="Invalid status")
    mapping = db.query(UnknownMapping).filter_by(id=mapping_id).first()
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")
    if payload.status == "confirmed" and not (payload.normalized_field or mapping.normalized_field):
        raise HTTPException(status_code=400, detail="Confirming requires a normalized_field")
    mapping.status = payload.status
    if payload.normalized_field is not None:
        mapping.normalized_field = payload.normalized_field
    if payload.suggested_category is not None:
        mapping.suggested_category = payload.suggested_category
    if payload.confirmed_by:
        mapping.confirmed_by = payload.confirmed_by
    db.commit()
    db.refresh(mapping)
    return mapping
