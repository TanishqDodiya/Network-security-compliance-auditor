"""Rules API: list and add demo security rules."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.compliance_rule import ComplianceRule
from app.schemas.rule import RuleCreate, RuleOut

router = APIRouter(prefix="/api/rules", tags=["rules"])


@router.get("", response_model=list[RuleOut])
def list_rules(db: Session = Depends(get_db)):
    return db.query(ComplianceRule).order_by(ComplianceRule.rule_code).all()


@router.post("", response_model=RuleOut, status_code=201)
def create_rule(payload: RuleCreate, db: Session = Depends(get_db)):
    existing = db.query(ComplianceRule).filter_by(rule_code=payload.rule_code).first()
    if existing:
        raise HTTPException(status_code=409, detail="Rule code already exists")
    rule = ComplianceRule(
        rule_code=payload.rule_code,
        title=payload.title,
        category=payload.category,
        severity=payload.severity.upper(),
        framework=payload.framework,
        field=payload.field,
        expected=payload.expected,
        description=payload.description,
        remediation=payload.remediation,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule
