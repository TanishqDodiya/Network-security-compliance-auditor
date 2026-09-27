"""configurations table: uploaded config files stored as untrusted text.

IMPORTANT: we only store and read the text. We never execute it.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class Configuration(Base):
    __tablename__ = "configurations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    detected_vendor: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    # Raw file content. Treated as untrusted text, never executed.
    raw_content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # ready | auditing | audited | error
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ready")
    upload_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    device: Mapped["Device"] = relationship(back_populates="configurations")
