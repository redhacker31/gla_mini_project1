"""Adaptive Step-Up OTP Authentication Service.

Manages the out-of-band challenge lifecycle for Medium-Risk transactions:
  1. Cryptographically secure 6-digit OTP generation (CSPRNG via secrets)
  2. Salted SHA-256 storage (Zero raw OTP persistence)
  3. Constant-time comparison (hmac.compare_digest)
  4. 180s Time-To-Live (TTL) expiration
  5. Max 3 verification attempts before account lockout & rejection
  6. Rate-limited resends (max 2 per transaction)
  7. State transitions: PENDING_VERIFICATION -> APPROVED or REJECTED
  8. Append-only cryptographic audit logging
"""
from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Dict, Optional, Tuple
import uuid

from sqlalchemy.orm import Session

from app.config import settings
from app.models.otp_session import OTPSession
from app.repositories.audit_repo import audit_repo
from app.repositories.otp_repo import otp_repo
from app.repositories.transaction_repo import transaction_repo
from app.repositories.user_repo import user_repo
from app.security.hashing import generate_csprng_otp, hash_otp, verify_otp_hash
from app.services.sms_gateway import sms_gateway

logger = logging.getLogger(__name__)


def _to_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensure datetime is offset-aware UTC for safe comparisons."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class OTPService:
    """Coordinates OTP generation, dispatch, verification, and state transitions."""

    def __init__(self):
        self.ttl = settings.OTP_EXPIRY_SECONDS
        self.max_attempts = settings.OTP_MAX_ATTEMPTS
        self.resend_max = settings.OTP_RESEND_MAX

    def is_active(self) -> bool:
        """Service health indicator."""
        return True

    def create_challenge(
        self,
        db: Session,
        txn_id: str,
        user_hash: str,
        amount: float,
        recipient_vpa: str,
        phone: Optional[str] = None,
        custom_session_id: Optional[str] = None,
    ) -> Tuple[OTPSession, str]:
        """Generate CSPRNG OTP challenge session, persist hash, and dispatch via SMS gateway."""
        session_id = custom_session_id or f"otp_sess_{uuid.uuid4().hex[:16]}"
        raw_otp = generate_csprng_otp(length=6)
        otp_digest = hash_otp(raw_otp)

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=settings.OTP_EXPIRY_SECONDS)
        target_phone = phone or "+91 98765 43210"

        # 1. Create and persist OTPSession
        otp_session = OTPSession(
            session_id=session_id,
            txn_id=txn_id,
            user_hash=user_hash,
            otp_hash=otp_digest,
            attempts=0,
            max_attempts=settings.OTP_MAX_ATTEMPTS,
            resends_used=0,
            phone_masked=sms_gateway._mask_phone(target_phone),
            status="ACTIVE",
            expires_at=expires_at,
            created_at=now,
        )
        otp_repo.create(db, otp_session)

        # 2. Append audit ledger entry
        audit_repo.append_log(
            db=db,
            entity_type="OTP_SESSION",
            entity_id=session_id,
            action="CHALLENGE_CREATED",
            actor="RISK_ENGINE",
            details={
                "txn_id": txn_id,
                "user_hash": user_hash,
                "ttl_seconds": settings.OTP_EXPIRY_SECONDS,
                "max_attempts": settings.OTP_MAX_ATTEMPTS,
            },
            timestamp=now,
        )

        # 3. Dispatch out-of-band SMS
        sms_gateway.send_otp_sms(
            phone=target_phone,
            otp=raw_otp,
            amount=amount,
            recipient_vpa=recipient_vpa,
            session_id=session_id,
        )

        db.commit()
        return otp_session, raw_otp

    def verify_otp(
        self,
        db: Session,
        session_id: str,
        candidate_otp: str,
    ) -> Dict[str, Any]:
        """Validate candidate OTP against stored hash with attempt limiting and state promotion."""
        session = otp_repo.get_by_id(db, session_id)
        if not session:
            return {
                "success": False,
                "status": "NOT_FOUND",
                "txn_id": "",
                "session_id": session_id,
                "remaining_attempts": 0,
                "message": f"Verification session '{session_id}' not found.",
            }

        now = datetime.now(timezone.utc)

        # Check if already verified
        if session.status == "VERIFIED":
            return {
                "success": True,
                "status": "APPROVED",
                "txn_id": session.txn_id,
                "session_id": session_id,
                "remaining_attempts": session.max_attempts - session.attempts,
                "message": "Transaction already verified and approved.",
            }

        # Check if locked
        if session.status == "LOCKED":
            return {
                "success": False,
                "status": "REJECTED",
                "txn_id": session.txn_id,
                "session_id": session_id,
                "remaining_attempts": 0,
                "message": "Verification session is locked due to excessive failed attempts. Transaction rejected.",
            }

        # Check if expired
        if session.status == "EXPIRED" or now > _to_utc(session.expires_at):
            session.status = "EXPIRED"
            transaction_repo.update_status(db, session.txn_id, "EXPIRED")
            audit_repo.append_log(
                db=db,
                entity_type="OTP_SESSION",
                entity_id=session_id,
                action="EXPIRED",
                actor="AUTH_SERVICE",
                details={"txn_id": session.txn_id},
                timestamp=now,
            )
            db.commit()
            return {
                "success": False,
                "status": "EXPIRED",
                "txn_id": session.txn_id,
                "session_id": session_id,
                "remaining_attempts": 0,
                "message": "OTP challenge expired (180s TTL elapsed). Please initiate a new transaction.",
            }

        # Increment attempt counter
        session.attempts += 1

        # Constant-time hash verification
        is_valid = verify_otp_hash(candidate_otp, session.otp_hash)

        if is_valid:
            # 1. Promote session and transaction
            session.status = "VERIFIED"
            session.verified_at = now
            transaction_repo.update_status(db, session.txn_id, "APPROVED")

            # 2. Append audit ledger
            audit_repo.append_log(
                db=db,
                entity_type="OTP_SESSION",
                entity_id=session_id,
                action="VERIFIED",
                actor="USER",
                details={"txn_id": session.txn_id, "attempt_number": session.attempts},
                timestamp=now,
            )
            audit_repo.append_log(
                db=db,
                entity_type="TRANSACTION",
                entity_id=session.txn_id,
                action="STATUS_CHANGE",
                actor="AUTH_SERVICE",
                details={"old_status": "PENDING_VERIFICATION", "new_status": "APPROVED"},
                timestamp=now,
            )

            db.commit()
            return {
                "success": True,
                "status": "APPROVED",
                "txn_id": session.txn_id,
                "session_id": session_id,
                "remaining_attempts": session.max_attempts - session.attempts,
                "message": "OTP verification successful. Transaction approved.",
            }

        else:
            # Check for lockout threshold
            remaining = session.max_attempts - session.attempts
            if remaining <= 0:
                # Max attempts reached -> LOCK SESSION & REJECT TRANSACTION
                session.status = "LOCKED"
                transaction_repo.update_status(db, session.txn_id, "REJECTED")
                user_repo.increment_stats(db, session.user_hash, is_flagged=True)

                audit_repo.append_log(
                    db=db,
                    entity_type="OTP_SESSION",
                    entity_id=session_id,
                    action="LOCKED",
                    actor="AUTH_SERVICE",
                    details={"txn_id": session.txn_id, "attempts_exhausted": session.attempts},
                    timestamp=now,
                )
                audit_repo.append_log(
                    db=db,
                    entity_type="TRANSACTION",
                    entity_id=session.txn_id,
                    action="STATUS_CHANGE",
                    actor="AUTH_SERVICE",
                    details={"old_status": "PENDING_VERIFICATION", "new_status": "REJECTED"},
                    timestamp=now,
                )

                db.commit()
                return {
                    "success": False,
                    "status": "REJECTED",
                    "txn_id": session.txn_id,
                    "session_id": session_id,
                    "remaining_attempts": 0,
                    "message": "Maximum verification attempts exceeded. Session locked and transaction rejected.",
                }
            else:
                audit_repo.append_log(
                    db=db,
                    entity_type="OTP_SESSION",
                    entity_id=session_id,
                    action="FAILED_ATTEMPT",
                    actor="USER",
                    details={"attempt_number": session.attempts, "remaining": remaining},
                    timestamp=now,
                )
                db.commit()
                return {
                    "success": False,
                    "status": "PENDING_VERIFICATION",
                    "txn_id": session.txn_id,
                    "session_id": session_id,
                    "remaining_attempts": remaining,
                    "message": f"Incorrect verification code. {remaining} attempt(s) remaining.",
                }

    def resend_otp(self, db: Session, session_id: str) -> Dict[str, Any]:
        """Regenerate and redispatch Step-Up OTP with rate-limiting quota enforcement."""
        session = otp_repo.get_by_id(db, session_id)
        if not session:
            return {
                "success": False,
                "message": f"Verification session '{session_id}' not found.",
            }

        if session.status != "ACTIVE":
            return {
                "success": False,
                "message": f"Cannot resend OTP: session is in '{session.status}' state.",
            }

        if session.resends_used >= settings.OTP_RESEND_MAX:
            return {
                "success": False,
                "session_id": session_id,
                "resends_remaining": 0,
                "message": f"Maximum OTP resend limit ({settings.OTP_RESEND_MAX}) reached.",
            }

        # Generate fresh OTP
        raw_otp = generate_csprng_otp(length=6)
        session.otp_hash = hash_otp(raw_otp)
        session.resends_used += 1

        now = datetime.now(timezone.utc)
        session.expires_at = now + timedelta(seconds=settings.OTP_EXPIRY_SECONDS)

        # Dispatch via SMS Gateway
        txn = session.transaction
        amount = txn.amount if txn else 0.0
        vpa = txn.recipient_vpa_masked if txn else "merchant@upi"
        phone = session.phone_masked or "+91 98*** **210"

        sms_gateway.send_otp_sms(
            phone=phone,
            otp=raw_otp,
            amount=amount,
            recipient_vpa=vpa,
            session_id=session_id,
        )

        audit_repo.append_log(
            db=db,
            entity_type="OTP_SESSION",
            entity_id=session_id,
            action="OTP_RESENT",
            actor="USER",
            details={
                "resends_used": session.resends_used,
                "resends_remaining": settings.OTP_RESEND_MAX - session.resends_used,
            },
            timestamp=now,
        )

        db.commit()
        return {
            "success": True,
            "session_id": session_id,
            "expires_at": session.expires_at,
            "resends_remaining": settings.OTP_RESEND_MAX - session.resends_used,
            "message": "Fresh OTP generated and dispatched via SMS.",
        }

    def get_session_status(self, db: Session, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve diagnostic state of an OTP verification session."""
        session = otp_repo.get_by_id(db, session_id)
        if not session:
            return None

        now = datetime.now(timezone.utc)
        is_expired = now > _to_utc(session.expires_at)

        return {
            "session_id": session.session_id,
            "txn_id": session.txn_id,
            "status": "EXPIRED" if is_expired and session.status == "ACTIVE" else session.status,
            "attempts": session.attempts,
            "max_attempts": session.max_attempts,
            "resends_used": session.resends_used,
            "expires_at": session.expires_at,
            "phone_masked": session.phone_masked,
            "is_expired": is_expired,
        }


# Singleton instance for application runtime
otp_service = OTPService()
