"""Transaction Entity Model."""
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.risk_assessment import RiskAssessment
    from app.models.otp_session import OTPSession


class Transaction(Base):
    """Digital micro-transaction record."""

    __tablename__ = "transactions"

    txn_id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    user_hash: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("users.user_hash", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    recipient_vpa_masked: Mapped[str] = mapped_column(String(100), nullable=False)
    merchant_category: Mapped[str] = mapped_column(String(50), default="miscellaneous")
    channel: Mapped[str] = mapped_column(String(20), default="upi")
    status: Mapped[str] = mapped_column(
        String(30),
        default="APPROVED",
        index=True,
    )  # APPROVED, PENDING_VERIFICATION, SECURITY_FLAGGED, REJECTED, EXPIRED
    session_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="transactions")
    risk_assessment: Mapped[Optional["RiskAssessment"]] = relationship(
        "RiskAssessment",
        back_populates="transaction",
        uselist=False,
        cascade="all, delete-orphan",
    )
    otp_session: Mapped[Optional["OTPSession"]] = relationship(
        "OTPSession",
        back_populates="transaction",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Transaction(id={self.txn_id}, amount={self.amount}, status={self.status})>"
