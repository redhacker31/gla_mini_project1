"""Mock SMS Gateway Service for Step-Up OTP Delivery.

Simulates telecom SMS gateway integration for digital micro-transactions.
Logs dispatched messages and provides in-memory retrieval hooks for automated testing
and developer verification in academic sandbox environments.
"""
from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional
import uuid

logger = logging.getLogger(__name__)


class MockSMSGateway:
    """Simulates out-of-band telecom SMS dispatch."""

    def __init__(self):
        # In-memory dispatch ledger: list of message payloads
        self._dispatches: List[Dict] = []
        self._by_session: Dict[str, Dict] = {}

    def send_otp_sms(
        self,
        phone: str,
        otp: str,
        amount: float,
        recipient_vpa: str,
        session_id: str,
    ) -> Dict:
        """Simulate sending an out-of-band Step-Up OTP SMS."""
        delivery_id = f"sms_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)

        # Standard Indian Banking / UPI Step-Up OTP SMS template
        message_body = (
            f"[Fraud Shield] OTP is {otp} for verification of INR {amount:.2f} "
            f"to {recipient_vpa}. Valid for 3 mins. Do NOT share OTP with anyone."
        )

        dispatch_record = {
            "delivery_id": delivery_id,
            "session_id": session_id,
            "phone_masked": self._mask_phone(phone),
            "raw_phone": phone,
            "otp": otp,  # Kept in mock gateway memory solely for testing / simulation
            "amount": amount,
            "recipient_vpa": recipient_vpa,
            "message": message_body,
            "status": "DELIVERED",
            "timestamp": now.isoformat(),
        }

        self._dispatches.append(dispatch_record)
        self._by_session[session_id] = dispatch_record

        logger.info(
            "SMS Gateway dispatched OTP to %s for session %s (Delivery ID: %s)",
            dispatch_record["phone_masked"],
            session_id,
            delivery_id,
        )

        return {
            "delivery_id": delivery_id,
            "status": "DELIVERED",
            "phone_masked": dispatch_record["phone_masked"],
            "timestamp": now.isoformat(),
        }

    def get_latest_dispatch(self, session_id: str) -> Optional[Dict]:
        """Fetch latest dispatch record for a specific challenge session (used in tests)."""
        return self._by_session.get(session_id)

    def get_all_dispatches(self) -> List[Dict]:
        """Retrieve complete dispatch ledger."""
        return list(self._dispatches)

    def clear_logs(self):
        """Reset internal dispatch ledger (for test suite hygiene)."""
        self._dispatches.clear()
        self._by_session.clear()

    @staticmethod
    def _mask_phone(phone: str) -> str:
        """Mask mobile number (e.g. +91 98*** **412)."""
        clean = phone.strip()
        if len(clean) >= 10:
            return f"{clean[:3]}****{clean[-4:]}"
        return "****"


# Singleton instance for application runtime
sms_gateway = MockSMSGateway()
