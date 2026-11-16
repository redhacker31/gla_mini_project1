"""API endpoints package."""
from fastapi import APIRouter
from app.api.transactions import router as transactions_router
from app.api.authentication import router as auth_router
from app.api.dashboard import router as dashboard_router
from app.api.simulation import router as simulation_router
from app.api.explainability import router as explainability_router
from app.api.benchmark import router as benchmark_router
from app.api.security import router as security_router

api_router = APIRouter()

api_router.include_router(transactions_router, prefix="/transactions", tags=["Transactions"])
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication & OTP"])
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard & Telemetry"])
api_router.include_router(simulation_router, prefix="/simulation", tags=["Simulation & Adversarial Generator"])
api_router.include_router(explainability_router, prefix="/explainability", tags=["Explainability & What-If Simulation"])
api_router.include_router(benchmark_router, prefix="/system/benchmark", tags=["Performance & SLA Benchmarking"])
api_router.include_router(security_router, prefix="/system/security", tags=["Security & Rate Limiting Controls"])
