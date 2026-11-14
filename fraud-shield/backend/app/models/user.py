"""User Account and Behavioral Profile Model."""
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List
from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.transaction import Transaction


class User(Base):
    """User account entity storing pseudonymized user identifiers and risk metrics."""

    __tablename__ = "users"

    # Primary Key is the salted SHA-256 hash of the real user identifier (DPDP Act compliant)
    user_hash: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    masked_display: Mapped[str] = mapped_column(String(32), nullable=False)
    account_status: Mapped[str] = mapped_column(String(20), default="ACTIVE", index=True)  # ACTIVE, SUSPENDED, FROZEN
    risk_multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    total_transactions: Mapped[int] = mapped_column(Integer, default=0)
    flagged_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User(user_hash={self.user_hash[:8]}..., status={self.account_status}, txns={self.total_transactions})>"
