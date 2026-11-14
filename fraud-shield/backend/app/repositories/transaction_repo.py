"""Transaction and Risk Assessment Repository."""
from typing import List, Optional
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.risk_assessment import RiskAssessment
from app.models.transaction import Transaction


class TransactionRepository:
    """Data access operations for Transactions and Risk Assessments."""

    @staticmethod
    def create(
        db: Session,
        transaction: Transaction,
        assessment: Optional[RiskAssessment] = None,
    ) -> Transaction:
        """Persist a new transaction and its associated risk assessment."""
        db.add(transaction)
        if assessment:
            db.add(assessment)
        db.flush()
        return transaction

    @staticmethod
    def get_by_id(db: Session, txn_id: str) -> Optional[Transaction]:
        """Fetch transaction with eager-loaded risk assessment and OTP session."""
        stmt = (
            select(Transaction)
            .options(
                joinedload(Transaction.risk_assessment),
                joinedload(Transaction.otp_session),
            )
            .where(Transaction.txn_id == txn_id)
        )
        return db.scalars(stmt).first()

    @staticmethod
    def list(
        db: Session,
        limit: int = 50,
        user_hash: Optional[str] = None,
        status: Optional[str] = None,
        risk_tier: Optional[str] = None,
    ) -> List[Transaction]:
        """Fetch transactions in reverse chronological order with optional filtering."""
        stmt = (
            select(Transaction)
            .options(joinedload(Transaction.risk_assessment))
            .order_by(desc(Transaction.created_at))
        )

        if user_hash:
            stmt = stmt.where(Transaction.user_hash == user_hash)
        if status:
            stmt = stmt.where(Transaction.status == status)
        if risk_tier:
            stmt = stmt.join(Transaction.risk_assessment).where(
                RiskAssessment.risk_tier == risk_tier
            )

        stmt = stmt.limit(limit)
        return list(db.scalars(stmt).unique().all())

    @staticmethod
    def update_status(db: Session, txn_id: str, new_status: str) -> bool:
        """Update transaction status."""
        stmt = select(Transaction).where(Transaction.txn_id == txn_id)
        txn = db.scalars(stmt).first()
        if txn:
            txn.status = new_status
            db.flush()
            return True
        return False

    @staticmethod
    def count(db: Session, status: Optional[str] = None) -> int:
        """Return total count of transactions, optionally filtered by status."""
        stmt = select(func.count(Transaction.txn_id))
        if status:
            stmt = stmt.where(Transaction.status == status)
        return db.scalar(stmt) or 0


transaction_repo = TransactionRepository()
