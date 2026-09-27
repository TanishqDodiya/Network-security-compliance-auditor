"""Reports API: download the audit PDF (built at request time from stored data)."""

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.ai.service import summarize_audit
from app.database.session import get_db
from app.models.audit_result import AuditResult
from app.models.audit_run import AuditRun
from app.models.configuration import Configuration
from app.models.device import Device
from app.models.unknown_mapping import UnknownMapping
from app.normalization import normalize_text
from app.reports import build_audit_pdf

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/{audit_id}")
def download_report(audit_id: int, db: Session = Depends(get_db)):
    run = db.query(AuditRun).filter_by(id=audit_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Audit not found")
    config = db.query(Configuration).filter_by(id=run.configuration_id).first()
    device = db.query(Device).filter_by(id=run.device_id).first()
    if not config or not device:
        raise HTTPException(status_code=404, detail="Audit data incomplete")

    rows = db.query(AuditResult).filter_by(audit_run_id=run.id).all()
    results = [
        {
            "rule_code": r.rule_code,
            "title": r.title,
            "status": r.status,
            "severity": r.severity,
            "evidence": r.evidence,
            "remediation": r.remediation,
        }
        for r in rows
    ]
    summary = summarize_audit(results)["summary"]

    # Unknown lines come from re-normalizing the stored config (nothing new stored).
    try:
        normalized = normalize_text(device.vendor, config.raw_content or "")
        unknown_lines = list(normalized.unknown_lines)
    except Exception:
        unknown_lines = []
    mappings = [
        {
            "vendor": m.vendor,
            "raw_pattern": m.raw_pattern,
            "normalized_field": m.normalized_field,
            "status": m.status,
        }
        for m in db.query(UnknownMapping).order_by(UnknownMapping.id.desc()).limit(50).all()
    ]

    try:
        pdf_bytes = build_audit_pdf(
            device_name=device.name,
            vendor=device.vendor,
            audit_id=run.id,
            finished_at=str(run.finished_at),
            compliance_percent=run.compliance_percent,
            results=results,
            summary=summary,
            unknown_lines=unknown_lines,
            mappings=mappings,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {exc}")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="audit-{run.id}.pdf"'},
    )
