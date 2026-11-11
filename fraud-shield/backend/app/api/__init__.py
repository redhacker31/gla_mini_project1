"""API endpoints package."""
from fastapi import APIRouter
from app.api.transactions import router as transactions_router
from app.api.authentication import router as auth_router
from app.api.dashboard import router as dashboard_router

api_router = APIRouter()

api_router.include_router(transactions_router, prefix="/transactions", tags=["Transactions"])
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication & OTP"])
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard & Telemetry"])

