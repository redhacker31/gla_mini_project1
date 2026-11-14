"""Cryptographic Append-Only Audit Log Ledger Model."""
from datetime import datetime, timezone
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class AuditLog(Base):
    """Tamper-evident audit ledger record.

    Employs a sequential cryptographic hash chain where each log entry's
    `record_hash` is computed over its contents AND the previous entry's hash.
    Any retroactive modification, row deletion, or insertion breaks the chain.
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )  # TRANSACTION, RISK_ASSESSMENT, OTP_SESSION, USER, SYSTEM
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # EVALUATED, CHALLENGED, APPROVED, FROZEN, etc.
    actor: Mapped[str] = mapped_column(String(50), default="SYSTEM")  # SYSTEM, RISK_ENGINE, USER, ANALYST
    details_json: Mapped[str] = mapped_column(Text, nullable=False)
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    record_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, entity={self.entity_type}:{self.entity_id[:8]}, action={self.action})>"
