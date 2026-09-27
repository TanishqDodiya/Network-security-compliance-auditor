"""audit_runs table: one row per compliance check run."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class AuditRun(Base):
    __tablename__ = "audit_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), nullable=False)
    configuration_id: Mapped[int] = mapped_column(ForeignKey("configurations.id"), nullable=False)
    # pending | running | completed | failed
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="completed")
    # 0-100 compliance percentage, filled after the compliance engine runs.
    compliance_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    device: Mapped["Device"] = relationship(back_populates="audit_runs")
    results: Mapped[list["AuditResult"]] = relationship(
        back_populates="audit_run", cascade="all, delete-orphan"
    )
