"""Persistent Security Policy and Threat Blacklist ORM Models."""
from datetime import datetime, timezone
from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class BlacklistEntry(Base):
    """Persisted fraudulent/flagged recipient VPA entry."""

    __tablename__ = "blacklist_entries"

    vpa: Mapped[str] = mapped_column(String(100), primary_key=True, index=True)
    vpa_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(250), default="")
    added_by: Mapped[str] = mapped_column(String(50), default="SYSTEM")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class SystemPolicy(Base):
    """Singleton row storing dynamic composite risk threshold configuration."""

    __tablename__ = "system_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    threshold_low: Mapped[float] = mapped_column(Float, nullable=False, default=0.45)
    threshold_high: Mapped[float] = mapped_column(Float, nullable=False, default=0.80)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
