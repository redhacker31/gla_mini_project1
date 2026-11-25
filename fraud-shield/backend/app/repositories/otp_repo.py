"""OTP Session Repository."""
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.otp_session import OTPSession
from app.models.transaction import Transaction


class OTPSessionRepository:
    """Data access operations for Step-Up OTP challenge sessions."""

    @staticmethod
    def create(db: Session, session: OTPSession) -> OTPSession:
        """Persist a new OTP challenge session."""
        db.add(session)
        db.flush()
        return session

    @staticmethod
    def get_by_id(db: Session, session_id: str) -> Optional[OTPSession]:
        """Fetch session by session_id with joined transaction."""
        stmt = (
            select(OTPSession)
            .options(joinedload(OTPSession.transaction))
            .where(OTPSession.session_id == session_id)
        )
        return db.scalars(stmt).first()

    @staticmethod
    def get_by_txn_id(db: Session, txn_id: str) -> Optional[OTPSession]:
        """Fetch active session by associated transaction ID."""
        stmt = (
            select(OTPSession)
            .options(joinedload(OTPSession.transaction))
            .where(OTPSession.txn_id == txn_id)
        )
        return db.scalars(stmt).first()

    @staticmethod
    def update_status(
        db: Session,
        session_id: str,
        new_status: str,
        verified_at: Optional[datetime] = None,
    ) -> bool:
        """Update OTP session lifecycle status."""
        stmt = select(OTPSession).where(OTPSession.session_id == session_id)
        sess = db.scalars(stmt).first()
        if sess:
            sess.status = new_status
            if verified_at:
                sess.verified_at = verified_at
            db.flush()
            return True
        return False

    @staticmethod
    def count_recent_failed_attempts(
        db: Session,
        user_hash: str,
        hours: int = 24,
    ) -> int:
        """Count total failed OTP attempts across recent unverified/locked sessions for a user."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        stmt = select(func.coalesce(func.sum(OTPSession.attempts), 0)).where(
            OTPSession.user_hash == user_hash,
            OTPSession.status != "VERIFIED",
            OTPSession.created_at >= cutoff,
        )
        return int(db.scalar(stmt) or 0)


otp_repo = OTPSessionRepository()
