"""Transaction API routes."""
from fastapi import APIRouter

router = APIRouter()


@router.get("", summary="List evaluated transactions")
async def list_transactions():
    """Retrieve recent transaction evaluations (placeholder for Phase 6/7)."""
    return {
        "status": "ready",
        "message": "Transaction evaluation engine initialized.",
        "data": [],
    }

