"""Transaction Ingestion, Evaluation, and Audit API Endpoints.

Provides real-time risk assessment for digital micro-transactions.
Implements:
  - POST /evaluate: Real-time ML + rule scoring and persistence
  - GET /transactions: List evaluated transactions
  - GET /transactions/{txn_id}: Transaction risk inspection
  - GET /transactions/audit/verify: Cryptographic hash-chain integrity verification
  - GET /transactions/audit/logs: Audit ledger inspection
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.repositories.audit_repo import audit_repo
from app.schemas.transaction import (
    TransactionDetail,
    TransactionEvaluateRequest,
    TransactionEvaluateResponse,
)
from app.services.transaction_service import transaction_service

router = APIRouter()


@router.post(
    "/evaluate",
    response_model=TransactionEvaluateResponse,
    status_code=status.HTTP_200_OK,
    summary="Ingest and score transaction risk",
    description=(
        "Ingests streaming digital micro-transaction payload, evaluates sliding-window velocity features, "
        "runs unsupervised Isolation Forest anomaly scoring paired with deterministic security rules, "
        "persists the evaluation to SQLite, and returns an operational 3-tier risk decision within sub-50ms."
    ),
    responses={
        200: {"description": "Transaction evaluated and persisted successfully."},
        400: {"description": "Invalid transaction data or business rule violation."},
        422: {"description": "Unprocessable entity / schema validation failure."},
    },
)
async def evaluate_transaction(
    payload: TransactionEvaluateRequest,
    db: Session = Depends(get_db),
) -> TransactionEvaluateResponse:
    """Ingest, evaluate, and persist a single digital micro-transaction."""
    try:
        response = transaction_service.evaluate_transaction(payload, db=db)
        return response
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transaction evaluation failed: {str(e)}",
        )


@router.get(
    "",
    summary="List recently evaluated transactions",
    description="Retrieve a reverse-chronological list of evaluated transactions from persistent storage.",
)
async def list_transactions(
    limit: int = Query(default=50, ge=1, le=200, description="Maximum number of transactions to return"),
    user_id: Optional[str] = Query(default=None, description="Optional filter by user identifier"),
    db: Session = Depends(get_db),
):
    """Retrieve evaluated transactions."""
    txns = transaction_service.list_transactions(limit=limit, user_id=user_id, db=db)
    return {
        "status": "success",
        "count": len(txns),
        "data": txns,
    }


@router.get(
    "/audit/verify",
    summary="Verify cryptographic audit hash chain integrity",
    description=(
        "Traverses the sequential audit ledger, verifies prev_hash linkage and content hashes "
        "across all entries, and reports any data tampering or unauthorized row modifications."
    ),
)
async def verify_audit_ledger(db: Session = Depends(get_db)):
    """Validate tamper-evident audit ledger integrity."""
    report = audit_repo.verify_chain_integrity(db)
    return {
        "status": "success",
        "audit_verification": report,
    }


@router.get(
    "/audit/logs",
    summary="List tamper-evident audit log entries",
    description="Retrieve immutable audit log records with sequential cryptographic hashes.",
)
async def list_audit_logs(
    limit: int = Query(default=50, ge=1, le=200, description="Maximum records to return"),
    entity_id: Optional[str] = Query(default=None, description="Filter by entity identifier"),
    db: Session = Depends(get_db),
):
    """Retrieve audit log entries."""
    logs = audit_repo.list_logs(db=db, limit=limit, entity_id=entity_id)
    return {
        "status": "success",
        "count": len(logs),
        "data": [
            {
                "id": log.id,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "action": log.action,
                "actor": log.actor,
                "details": log.details_json,
                "prev_hash": log.prev_hash,
                "record_hash": log.record_hash,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            }
            for log in logs
        ],
    }


@router.get(
    "/{txn_id}",
    summary="Retrieve transaction evaluation by ID",
    description="Fetch complete risk assessment, feature telemetry, and operational status for a specific transaction.",
    responses={
        200: {"description": "Transaction found."},
        404: {"description": "Transaction ID not found."},
    },
)
async def get_transaction(
    txn_id: str,
    db: Session = Depends(get_db),
):
    """Fetch single transaction by ID."""
    txn = transaction_service.get_transaction(txn_id, db=db)
    if not txn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with ID '{txn_id}' not found.",
        )
    return {
        "status": "success",
        "data": txn,
    }
