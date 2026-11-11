"""Fraud Shield - Main FastAPI Application Entrypoint.

Real-Time Anomaly Detection for Digital Micro-Transactions.
B.Tech AIML Capstone Project.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api import api_router


def create_application() -> FastAPI:
    """Factory function to build and configure the FastAPI application."""
    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "Fraud Shield: Edge-compatible, real-time AI/ML behavioral anomaly detection "
            "and adaptive risk-based authentication system for digital micro-transactions."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Configure CORS middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check endpoint at /api/v1/health
    @application.get(
        f"{settings.API_V1_STR}/health",
        tags=["System Health"],
        summary="Service Health Check",
    )
    async def health_check():
        """Verify that the FastAPI service and submodules are alive."""
        return {
            "status": "healthy",
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "risk_thresholds": {
                "low": settings.RISK_THRESHOLD_LOW,
                "high": settings.RISK_THRESHOLD_HIGH,
            },
        }

    # Root welcome route
    @application.get("/", tags=["Root"])
    async def root():
        return {
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "health": f"{settings.API_V1_STR}/health",
            "docs": "/docs",
        }

    # Mount versioned API routes (/api/v1)
    application.include_router(api_router, prefix=settings.API_V1_STR)

    return application


app = create_application()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)

