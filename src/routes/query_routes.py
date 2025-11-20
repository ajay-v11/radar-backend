"""
Query Generation Routes

Endpoints for generating industry-specific search queries.
"""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, HttpUrl
from typing import Optional

from src.controllers.query_controller import generate_queries_stream


router = APIRouter(prefix="/queries", tags=["Query Generation"])


class QueryGenerationRequest(BaseModel):
    """Request model for query generation."""
    company_url: HttpUrl
    company_name: Optional[str] = None
    num_queries: Optional[int] = 50


async def _stream_events(
    company_url: str,
    company_name: Optional[str] = None,
    num_queries: int = 50
):
    """Format events as Server-Sent Events with immediate flushing."""
    import asyncio
    async for event_json in generate_queries_stream(company_url, company_name, num_queries):
        yield f"data: {event_json}\n\n"
        # Force flush by yielding control
        await asyncio.sleep(0)


@router.post("/generate")
async def generate_queries(request: QueryGenerationRequest):
    """
    Generate industry-specific queries with streaming updates.
    
    This endpoint:
    1. Detects company industry (if not cached)
    2. Generates 50-100 queries organized by category
    3. Streams queries as they're generated
    
    Categories:
    - Product Selection
    - Comparison
    - How-to & Educational
    - Best-of Lists
    - Problem-solving
    
    Example:
        POST /queries/generate
        {
            "company_url": "https://hellofresh.com",
            "company_name": "HelloFresh",
            "num_queries": 50
        }
    """
    return StreamingResponse(
        _stream_events(
            company_url=str(request.company_url),
            company_name=request.company_name,
            num_queries=request.num_queries or 50
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
