"""Tamper-Evident Cryptographic Audit Ledger Repository."""
from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.security.hashing import calculate_audit_hash, canonical_iso_timestamp

GENESIS_HASH = "GENESIS_FRAUD_SHIELD_V1_2026"


class AuditRepository:
    """Operations for appending and validating the tamper-evident audit ledger."""

    @staticmethod
    def append_log(
        db: Session,
        entity_type: str,
        entity_id: str,
        action: str,
        actor: str = "SYSTEM",
        details: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ) -> AuditLog:
        """Append a new record to the sequential cryptographic audit hash chain."""
        # 1. Fetch record_hash of the latest record
        last_hash_stmt = select(AuditLog.record_hash).order_by(desc(AuditLog.id)).limit(1)
        prev_hash = db.scalar(last_hash_stmt) or GENESIS_HASH

        # 2. Canonical JSON serialization of details
        ts = timestamp or datetime.now(timezone.utc)
        ts_str = canonical_iso_timestamp(ts)
        details_dict = details or {}
        details_json = json.dumps(details_dict, sort_keys=True, separators=(",", ":"))

        # 3. Calculate SHA-256 digest
        record_hash = calculate_audit_hash(
            prev_hash=prev_hash,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            timestamp_str=ts_str,
            details_json=details_json,
        )

        # 4. Construct and persist ledger entry
        log_entry = AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            actor=actor,
            details_json=details_json,
            prev_hash=prev_hash,
            record_hash=record_hash,
            timestamp=ts,
        )
        db.add(log_entry)
        db.flush()
        return log_entry

    @staticmethod
    def verify_chain_integrity(db: Session) -> Dict[str, Any]:
        """Verify complete sequential hash-chain integrity across all audit records.

        Validates both:
          1. Linkage: row[i].prev_hash == row[i-1].record_hash
          2. Content: row[i].record_hash == SHA256(row[i] contents)

        Returns diagnostic verification report.
        """
        stmt = select(AuditLog).order_by(AuditLog.id.asc())
        records = list(db.scalars(stmt).all())

        if not records:
            return {
                "valid": True,
                "total_records": 0,
                "message": "Audit ledger is empty (valid state).",
                "failed_record_id": None,
            }

        expected_prev = GENESIS_HASH
        for idx, rec in enumerate(records):
            # Check linkage to previous block
            if rec.prev_hash != expected_prev:
                return {
                    "valid": False,
                    "total_records": len(records),
                    "failed_record_id": rec.id,
                    "index": idx,
                    "reason": (
                        f"Chain breakage at ID {rec.id}: expected prev_hash '{expected_prev}', "
                        f"found '{rec.prev_hash}'."
                    ),
                }

            # Check content integrity hash
            computed_hash = calculate_audit_hash(
                prev_hash=rec.prev_hash,
                entity_type=rec.entity_type,
                entity_id=rec.entity_id,
                action=rec.action,
                timestamp_str=canonical_iso_timestamp(rec.timestamp),
                details_json=rec.details_json,
            )
            if rec.record_hash != computed_hash:
                return {
                    "valid": False,
                    "total_records": len(records),
                    "failed_record_id": rec.id,
                    "index": idx,
                    "reason": (
                        f"Data tampering at ID {rec.id}: computed hash '{computed_hash}' "
                        f"does not match stored record_hash '{rec.record_hash}'."
                    ),
                }

            expected_prev = rec.record_hash

        return {
            "valid": True,
            "total_records": len(records),
            "message": "Cryptographic audit chain fully verified. Zero tampering detected.",
            "head_hash": expected_prev,
            "failed_record_id": None,
        }

    @staticmethod
    def list_logs(
        db: Session,
        limit: int = 50,
        entity_id: Optional[str] = None,
    ) -> List[AuditLog]:
        """Fetch audit log entries in reverse chronological order."""
        stmt = select(AuditLog).order_by(desc(AuditLog.id))
        if entity_id:
            stmt = stmt.where(AuditLog.entity_id == entity_id)
        stmt = stmt.limit(limit)
        return list(db.scalars(stmt).all())


audit_repo = AuditRepository()
