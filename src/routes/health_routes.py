"""
Health Check Routes

System health and status endpoints.
"""

from fastapi import APIRouter
from models.schemas import HealthResponse
from config.settings import settings


router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.
    
    Returns the current status and version of the system.
    This endpoint can be used for monitoring and load balancer health checks.
    
    Returns:
        HealthResponse with status and version information
    """
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION
    )


@router.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "AI Visibility Scoring System",
        "version": settings.APP_VERSION,
        "endpoints": {
            "health": "/health",
            "industry_analysis": "/industry/analyze",
            "visibility_analysis": "/visibility/analyze"
        }
    }
