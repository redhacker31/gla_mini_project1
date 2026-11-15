"""OTP Session Repository."""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select
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


otp_repo = OTPSessionRepository()
