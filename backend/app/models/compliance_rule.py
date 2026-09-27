"""compliance_rules table: demo security rules (NOT official CIS/NIST unless verified).

A rule says: look at field `management.telnet_enabled`, expect `false`.
The compliance engine (Phase 10) will read this table.
"""

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class ComplianceRule(Base):
    __tablename__ = "compliance_rules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # Human-readable stable ID like "NET-001". Unique so results can reference it.
    rule_code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="General")
    # CRITICAL | HIGH | MEDIUM | LOW
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="MEDIUM")
    # Example: ["Demo Security Rule"]. Stored as JSON list.
    framework: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # Dotted path into the normalized model, e.g. "management.telnet_enabled".
    field: Mapped[str] = mapped_column(String(128), nullable=False)
    # Expected value, e.g. false. JSON so it can be bool/str/number/list.
    expected: Mapped[object] = mapped_column(JSON, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    remediation: Mapped[str] = mapped_column(Text, nullable=False, default="")

    results: Mapped[list["AuditResult"]] = relationship(back_populates="rule")
