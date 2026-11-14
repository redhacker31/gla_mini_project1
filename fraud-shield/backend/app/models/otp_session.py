"""OTP Step-Up Authentication Session Model."""
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.transaction import Transaction


class OTPSession(Base):
    """Step-Up OTP authentication challenge session entity."""

    __tablename__ = "otp_sessions"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    txn_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("transactions.txn_id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    user_hash: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("users.user_hash", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    otp_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    status: Mapped[str] = mapped_column(
        String(20),
        default="ACTIVE",
        index=True,
    )  # ACTIVE, VERIFIED, EXPIRED, LOCKED
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    transaction: Mapped["Transaction"] = relationship("Transaction", back_populates="otp_session")

    def __repr__(self) -> str:
        return f"<OTPSession(session_id={self.session_id}, status={self.status}, attempts={self.attempts})>"
