"""User Repository for account profiles and behavioral tracking."""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    """Data access operations for User entities."""

    @staticmethod
    def get_by_hash(db: Session, user_hash: str) -> Optional[User]:
        """Fetch user by salted SHA-256 hash."""
        stmt = select(User).where(User.user_hash == user_hash)
        return db.scalars(stmt).first()

    @staticmethod
    def get_or_create(db: Session, user_hash: str, masked_display: str) -> User:
        """Fetch existing user or initialize a new profile."""
        user = UserRepository.get_by_hash(db, user_hash)
        if not user:
            user = User(
                user_hash=user_hash,
                masked_display=masked_display,
                account_status="ACTIVE",
                risk_multiplier=1.0,
                total_transactions=0,
                flagged_count=0,
                created_at=datetime.now(timezone.utc),
                last_active_at=datetime.now(timezone.utc),
            )
            db.add(user)
            db.flush()
        return user

    @staticmethod
    def increment_stats(
        db: Session,
        user_hash: str,
        is_flagged: bool = False,
    ) -> Optional[User]:
        """Update transaction counter and security flag metrics for a user."""
        user = UserRepository.get_by_hash(db, user_hash)
        if user:
            user.total_transactions += 1
            if is_flagged:
                user.flagged_count += 1
            user.last_active_at = datetime.now(timezone.utc)
            db.flush()
        return user


user_repo = UserRepository()
