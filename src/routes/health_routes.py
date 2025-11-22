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
        "description": "Two-phase analysis workflow for company visibility scoring",
        "endpoints": {
            "health": "/health",
            "phase_1_company_analysis": "/analyze/company",
            "phase_2_complete_flow": "/analyze/complete-flow"
        },
        "workflow": {
            "step_1": "POST /analyze/company - Analyze company, detect industry, identify competitors",
            "step_2": "POST /analyze/complete-flow - Generate queries, test AI models, calculate visibility score"
        }
    }
