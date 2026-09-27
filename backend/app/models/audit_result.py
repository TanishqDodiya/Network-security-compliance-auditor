"""audit_results table: PASS/FAIL for each rule in an audit run."""

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class AuditResult(Base):
    __tablename__ = "audit_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    audit_run_id: Mapped[int] = mapped_column(ForeignKey("audit_runs.id"), nullable=False)
    # Link to compliance_rules.id (kept nullable so old results survive rule edits).
    rule_id: Mapped[int | None] = mapped_column(ForeignKey("compliance_rules.id"), nullable=True)
    # Snapshot of the rule code/title at audit time, e.g. "NET-001".
    rule_code: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    # PASS | FAIL
    status: Mapped[str] = mapped_column(String(8), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="MEDIUM")
    # Why did it pass/fail? Exact config line when available.
    evidence: Mapped[str] = mapped_column(Text, nullable=False, default="")
    remediation: Mapped[str] = mapped_column(Text, nullable=False, default="")

    audit_run: Mapped["AuditRun"] = relationship(back_populates="results")
    rule: Mapped["ComplianceRule | None"] = relationship(back_populates="results")
