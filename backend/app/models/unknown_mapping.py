"""unknown_mappings table: human-in-the-loop learning (NOT model retraining).

Flow: unknown config line -> AI suggestion -> human confirms -> stored here.
Next time the same pattern appears, we reuse this row before calling AI.
"""

from datetime import datetime

from sqlalchemy import DateTime, Float, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class UnknownMapping(Base):
    __tablename__ = "unknown_mappings"
    __table_args__ = (
        UniqueConstraint("vendor", "raw_pattern", name="uq_vendor_raw_pattern"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    vendor: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    # The exact unknown line, e.g. "set xyz secure-admin-mode enabled".
    raw_pattern: Mapped[str] = mapped_column(Text, nullable=False)
    # Where it maps in the normalized model, e.g. "management.secure_admin_mode".
    normalized_field: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    suggested_category: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    # pending | confirmed | rejected
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    confirmed_by: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
