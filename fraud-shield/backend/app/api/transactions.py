"""Transaction Ingestion and Evaluation API Endpoints.

Provides real-time risk assessment for digital micro-transactions.
Implements POST /evaluate, GET /transactions, and GET /transactions/{txn_id}.
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status

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
        "and returns an operational 3-tier risk decision (ALLOW / CHALLENGE_OTP / FREEZE_REVIEW) within sub-50ms."
    ),
    responses={
        200: {"description": "Transaction evaluated successfully."},
        400: {"description": "Invalid transaction data or business rule violation."},
        422: {"description": "Unprocessable entity / schema validation failure."},
    },
)
async def evaluate_transaction(payload: TransactionEvaluateRequest) -> TransactionEvaluateResponse:
    """Ingest and evaluate a single digital micro-transaction."""
    try:
        response = transaction_service.evaluate_transaction(payload)
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
    description="Retrieve a reverse-chronological list of recently evaluated transactions.",
)
async def list_transactions(
    limit: int = Query(default=50, ge=1, le=200, description="Maximum number of transactions to return"),
    user_id: Optional[str] = Query(default=None, description="Optional filter by user identifier"),
):
    """Retrieve evaluated transactions."""
    txns = transaction_service.list_transactions(limit=limit, user_id=user_id)
    return {
        "status": "success",
        "count": len(txns),
        "data": txns,
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
async def get_transaction(txn_id: str):
    """Fetch single transaction by ID."""
    txn = transaction_service.get_transaction(txn_id)
    if not txn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with ID '{txn_id}' not found.",
        )
    return {
        "status": "success",
        "data": txn,
    }
