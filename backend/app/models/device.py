"""devices table: one row per network device (router/firewall)."""

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # Example: "Cisco-Router-01"
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    # "cisco" | "juniper" | "paloalto" | "unknown" (lowercase by convention)
    vendor: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    configurations: Mapped[list["Configuration"]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )
    audit_runs: Mapped[list["AuditRun"]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )
