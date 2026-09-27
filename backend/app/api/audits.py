"""Audits API: run compliance evaluation and read results back.

Pipeline: configuration text -> vendor parser -> normalized model
-> compliance engine (vendor-independent) -> stored PASS/FAIL results.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.compliance import compliance_percent, evaluate_all
from app.compliance.rules_data import DEMO_RULES
from app.database.session import get_db
from app.models.audit_result import AuditResult
from app.models.audit_run import AuditRun
from app.models.compliance_rule import ComplianceRule
from app.models.configuration import Configuration
from app.normalization import normalize_text
from app.schemas.audit import AuditCreate, AuditResultOut, AuditRunOut

router = APIRouter(tags=["audits"])


@router.post("/api/audits", response_model=AuditRunOut, status_code=201)
def create_audit(payload: AuditCreate, db: Session = Depends(get_db)):
    config = db.query(Configuration).filter_by(id=payload.configuration_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    vendor = (config.detected_vendor or "unknown").lower()
    normalized = normalize_text(vendor, config.raw_content or "")

    # Rules live in the DB (seeded via seed_rules.py). Fall back to built-in
    # demo data if the DB is empty so the demo never breaks.
    db_rules = db.query(ComplianceRule).order_by(ComplianceRule.rule_code).all()
    rules = db_rules if db_rules else DEMO_RULES
    results = evaluate_all(normalized, rules)
    percent = compliance_percent(results)

    run = AuditRun(
        device_id=config.device_id,
        configuration_id=config.id,
        status="completed",
        compliance_percent=percent,
        started_at=datetime.utcnow(),
        finished_at=datetime.utcnow(),
    )
    db.add(run)
    db.flush()  # get run.id before inserting results

    rule_id_by_code = {r.rule_code: r.id for r in db_rules}
    for res in results:
        db.add(
            AuditResult(
                audit_run_id=run.id,
                rule_id=rule_id_by_code.get(res.rule_code),
                rule_code=res.rule_code,
                title=res.title,
                status=res.status,
                severity=res.severity,
                evidence=res.evidence,
                remediation=res.remediation,
            )
        )
    config.status = "audited"
    db.commit()
    db.refresh(run)
    return run


@router.get("/api/audits", response_model=list[AuditRunOut])
def list_audits(limit: int = 50, db: Session = Depends(get_db)):
    """Recent audit runs for the dashboard (Phase 13)."""
    limit = max(1, min(limit, 200))
    return db.query(AuditRun).order_by(AuditRun.id.desc()).limit(limit).all()


@router.get("/api/audits/{audit_id}", response_model=AuditRunOut)
def get_audit(audit_id: int, db: Session = Depends(get_db)):
    run = db.query(AuditRun).filter_by(id=audit_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Audit not found")
    return run


@router.get("/api/results/{audit_id}", response_model=list[AuditResultOut])
def get_results(audit_id: int, db: Session = Depends(get_db)):
    run = db.query(AuditRun).filter_by(id=audit_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Audit not found")
    return db.query(AuditResult).filter_by(audit_run_id=audit_id).all()
