"""Risk Assessment Evaluation Record Model."""
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.transaction import Transaction


class RiskAssessment(Base):
    """Detailed risk scoring breakdown and behavioral feature snapshot for each transaction."""

    __tablename__ = "risk_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    txn_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("transactions.txn_id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    composite_score: Mapped[float] = mapped_column(Float, nullable=False)
    ml_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_tier: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # LOW, MEDIUM, HIGH
    action: Mapped[str] = mapped_column(String(30), nullable=False)  # ALLOW, CHALLENGE_OTP, FREEZE_REVIEW
    challenge_required: Mapped[bool] = mapped_column(Boolean, default=False)
    triggered_rules_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    features_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationship
    transaction: Mapped["Transaction"] = relationship("Transaction", back_populates="risk_assessment")

    def __repr__(self) -> str:
        return f"<RiskAssessment(txn_id={self.txn_id}, tier={self.risk_tier}, score={self.composite_score})>"
