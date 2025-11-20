"""
Industry Detection Routes

Endpoints for company analysis and industry detection.
"""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, Any

from src.controllers.industry_controller import analyze_company_stream
from agents.industry_detector import detect_industry
from models.schemas import WorkflowState


router = APIRouter(prefix="/industry", tags=["Industry Detection"])


class CompanyAnalysisRequest(BaseModel):
    """Request model for company analysis."""
    company_url: HttpUrl
    company_name: Optional[str] = None


async def _stream_events(company_url: str, company_name: Optional[str] = None):
    """Format events as Server-Sent Events."""
    async for event_json in analyze_company_stream(company_url, company_name):
        yield f"data: {event_json}\n\n"


@router.post("/analyze-smart")
async def analyze_company_smart(request: CompanyAnalysisRequest):
    """
    Smart endpoint: Returns cached data instantly or streams if cache miss.
    
    This endpoint checks cache first:
    - Cache HIT: Returns JSON immediately (~10-50ms)
    - Cache MISS: Streams SSE with real-time progress
    
    Example:
        POST /industry/analyze-smart
        {
            "company_url": "https://hellofresh.com",
            "company_name": "HelloFresh"
        }
    """
    from src.controllers.industry_controller import _get_cached_analysis
    
    # Check cache first
    cached = _get_cached_analysis(str(request.company_url))
    
    if cached:
        # INSTANT return with cached data
        return {
            "cached": True,
            "data": cached
        }
    
    # Cache miss - use streaming
    return StreamingResponse(
        _stream_events(
            company_url=str(request.company_url),
            company_name=request.company_name
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/analyze")
async def analyze_company(request: CompanyAnalysisRequest):
    """
    Analyze a company and detect its industry with streaming updates.
    
    This endpoint always streams Server-Sent Events (SSE) with real-time progress.
    Use /analyze-smart for automatic cache detection.
    
    Steps:
    1. Initialize analysis
    2. Scrape website content
    3. Analyze with AI
    4. Identify competitors
    5. Return complete results
    
    Example:
        POST /industry/analyze
        {
            "company_url": "https://hellofresh.com",
            "company_name": "HelloFresh"
        }
    """
    return StreamingResponse(
        _stream_events(
            company_url=str(request.company_url),
            company_name=request.company_name
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
