"""
Analysis Routes

Two-phase analysis workflow:
1. Company Analysis (Phase 1) - Scraping, industry detection, competitor identification
2. Visibility Analysis (Phase 2) - Query generation, model testing, scoring
"""

import logging
import json
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, HttpUrl

from src.controllers.industry_controller import analyze_company_stream, _get_cached_analysis
from src.controllers.analysis_controller import (
    get_cached_complete_flow,
    cache_complete_flow,
    execute_visibility_analysis
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analyze", tags=["Analysis"])


# ============================================================================
# Request Models
# ============================================================================

class CompanyAnalysisRequest(BaseModel):
    """Request model for company analysis (Phase 1)."""
    company_url: HttpUrl
    company_name: Optional[str] = None
    
    class Config:
        extra = "forbid"


class VisibilityAnalysisRequest(BaseModel):
    """Request model for visibility analysis (Phase 2)."""
    company_url: HttpUrl
    num_queries: int = 20
    models: List[str] = ["llama", "gemini"]
    llm_provider: str = "llama"
    batch_size: int = 5
    query_weights: Optional[dict] = None
    
    class Config:
        extra = "forbid"


# ============================================================================
# Phase 1: Company Analysis
# ============================================================================

@router.post("/company")
async def analyze_company_smart(request: CompanyAnalysisRequest):
    """
    Phase 1: Company Analysis with automatic caching.
    
    This endpoint:
    - Scrapes company website
    - Detects industry category
    - Identifies competitors
    - Generates company summary
    - Stores data for reuse
    
    Cache behavior:
    - Cache HIT: Returns JSON immediately (~10-50ms)
    - Cache MISS: Streams SSE with real-time progress
    
    This step is isolated because:
    - Higher chance of failure (broken URLs, scraping issues)
    - Can be enhanced independently (user-provided competitors)
    - Results are reusable across multiple visibility analyses
    
    Example:
        POST /analyze/company
        {
            "company_url": "https://hellofresh.com",
            "company_name": "HelloFresh"
        }
    
    Returns (cached):
        {
            "cached": true,
            "data": {
                "industry": "food_services",
                "company_name": "HelloFresh",
                "company_description": "...",
                "competitors": ["Blue Apron", "Home Chef", ...]
            }
        }
    
    Returns (streaming): Server-Sent Events with progress updates
    """
    # Check cache first
    cached = _get_cached_analysis(str(request.company_url))
    
    if cached:
        return {
            "cached": True,
            "data": cached
        }
    
    # Cache miss - stream the analysis
    async def _stream_events():
        async for event_json in analyze_company_stream(
            str(request.company_url),
            request.company_name
        ):
            yield f"data: {event_json}\n\n"
    
    return StreamingResponse(
        _stream_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ============================================================================
# Phase 2: Visibility Analysis
# ============================================================================

async def visibility_analysis_stream(request: VisibilityAnalysisRequest):
    """
    Stream visibility analysis workflow.
    
    Requires Phase 1 (/analyze/company) to have been run first.
    
    Steps:
    1. Load company data from Phase 1 cache
    2. Generate queries
    3. Test queries across AI models
    4. Calculate visibility score
    """
    
    def emit(step: str, status: str, data: dict = None, message: str = ""):
        event = {
            "step": step,
            "status": status,
            "message": message,
            "data": data or {}
        }
        return f"data: {json.dumps(event)}\n\n"
    
    try:
        # Get company data from Phase 1 cache
        cached_company = _get_cached_analysis(str(request.company_url))
        
        if not cached_company:
            yield emit("error", "failed", {
                "error": "Company analysis not found. Please run POST /analyze/company first."
            }, "Company data required")
            return
        
        yield emit("step1", "completed", {
            "industry": cached_company.get("industry"),
            "company_name": cached_company.get("company_name"),
            "competitors": cached_company.get("competitors", [])
        }, "Using cached company data")
        
        # Run visibility analysis
        import asyncio
        
        final_result = await asyncio.to_thread(
            execute_visibility_analysis,
            company_data=cached_company,
            company_url=str(request.company_url),
            num_queries=request.num_queries,
            models=request.models,
            llm_provider=request.llm_provider,
            batch_size=request.batch_size,
            query_weights=request.query_weights
        )
        
        # Stream progress events
        yield emit("step2", "completed", {
            "total_queries": final_result.get("total_queries"),
        }, f"Generated {final_result.get('total_queries')} queries")
        
        yield emit("step3", "completed", message="Model testing completed")
        
        yield emit("step4", "completed", {
            "visibility_score": final_result.get("visibility_score", 0),
            "total_mentions": final_result.get("analysis_report", {}).get("total_mentions", 0),
        }, "Scoring completed")
        
        # Cache the results
        cache_complete_flow(
            str(request.company_url),
            request.num_queries,
            request.models,
            final_result,
            request.query_weights
        )
        
        yield emit("complete", "success", final_result, "Visibility analysis completed!")
        
    except Exception as e:
        logger.error(f"Error in visibility analysis: {str(e)}", exc_info=True)
        yield emit("error", "failed", {"error": str(e)}, f"Error: {str(e)}")


@router.post("/visibility")
async def analyze_visibility(request: VisibilityAnalysisRequest):
    """
    Phase 2: Visibility analysis workflow with smart caching.
    
    **Prerequisites**: Must run POST /analyze/company first to get company data.
    
    This endpoint:
    1. Loads company data from Phase 1 cache
    2. Generates industry-specific queries
    3. Tests queries across selected AI models (parallel batches)
    4. Calculates visibility score with hybrid mention detection
    5. Returns detailed analysis report
    
    User inputs:
    - company_url: Company website (required, must match Phase 1)
    - num_queries: Number of queries to generate (default: 20)
    - models: AI models to test (default: ["llama", "gemini"])
    - llm_provider: LLM for query generation (default: "gemini")
    - batch_size: Queries per batch (default: 5)
    - query_weights: Category weights for query generation (optional, future)
    
    Smart Caching Strategy:
    
    1. **Visibility Analysis Cache** (24hr TTL):
       - Cache key: company_url + num_queries + models + query_weights
       - If ALL parameters match → return cached results instantly
       - If ANY parameter changes → re-run affected steps
    
    2. **Granular Caching**:
       - Company data: Uses Phase 1 cache (24hr TTL)
       - Query generation: Cached per company+industry+num_queries (24hr TTL)
       - Model responses: Cached per query+model (1hr TTL)
    
    3. **Cache Behavior Examples**:
       - Same everything → Instant cached results
       - Only models changed → Reuse queries, re-run tests
       - Only num_queries changed → Reuse company data, regenerate queries
       - query_weights changed → Re-run everything (future)
    
    Returns:
    - Cached: JSON response with complete results
    - Not cached: Server-Sent Events stream with real-time progress
    
    Example:
        POST /analyze/visibility
        {
            "company_url": "https://hellofresh.com",
            "num_queries": 20,
            "models": ["chatgpt", "gemini"],
            "llm_provider": "gemini",
            "batch_size": 5
        }
    """
    try:
        if not request.company_url:
            raise ValueError("company_url is required")
        
        # Check visibility analysis cache first
        cached_result = get_cached_complete_flow(
            str(request.company_url),
            request.num_queries,
            request.models,
            request.query_weights
        )
        if cached_result:
            return {
                "cached": True,
                "data": cached_result
            }
        
        # Cache miss - stream the analysis
        return StreamingResponse(
            visibility_analysis_stream(request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error creating stream: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )
