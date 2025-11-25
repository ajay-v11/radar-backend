"""
Analysis Routes

Two-phase analysis workflow:
1. Company Analysis (Phase 1) - Scraping, industry detection, competitor identification
2. Visibility Analysis (Phase 2) - Query generation, model testing, scoring
"""
import asyncio
import logging
import json
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, HttpUrl

from src.controllers.industry_controller import analyze_company_stream
from src.controllers.analysis_controller import execute_visibility_analysis
from src.controllers.cache_manager import (
    generate_analysis_slug,
    generate_visibility_slug,
    get_cached_by_slug,
    cache_by_slug
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analyze", tags=["Analysis"])
report_router = APIRouter(prefix="/report", tags=["Reports"])


# ============================================================================
# Request Models
# ============================================================================

class CompanyAnalysisRequest(BaseModel):
    """Request model for company analysis (Phase 1)."""
    company_url: HttpUrl
    company_name: Optional[str] = None
    target_region: str = "United States"
    
    class Config:
        extra = "forbid"


class VisibilityAnalysisRequest(BaseModel):
    """Request model for visibility analysis (Phase 2)."""
    company_slug_id: str  # Slug from company analysis
    num_queries: int = 20
    models: List[str] = ["llama", "gemini"]
    llm_provider: str = "llama"
    
    class Config:
        extra = "forbid"


# ============================================================================
# Phase 1: Company Analysis
# ============================================================================

@router.post("/company")
async def analyze_company_smart(request: CompanyAnalysisRequest):
    """
    Phase 1: Company Analysis with slug-based caching.
    
    Always streams SSE (even for cache hits) - simpler for frontend.
    
    Parameters:
    - company_url: Company website URL (required)
    - company_name: Optional company name override
    - target_region: Target region for AI model context (default: "United States")
    
    Returns: SSE stream with slug_id in final event
    """
    # Generate slug
    slug = generate_analysis_slug(str(request.company_url), request.target_region)
    
    # Check cache
    cached = get_cached_by_slug(slug)
    
    async def _stream_events():
        if cached:
            # Stream cached data instantly
            yield f"data: {json.dumps({'step': 'complete', 'status': 'success', 'message': 'Analysis completed (from cache)', 'slug_id': slug, 'data': cached, 'cached': True})}\n\n"
        else:
            # Stream live analysis
            final_data = None
            
            async for event_json in analyze_company_stream(
                str(request.company_url),
                request.company_name,
                request.target_region
            ):
                event = json.loads(event_json)
                if event.get("step") == "complete" and event.get("status") == "success":
                    final_data = event.get("data", {})
                    # Add company_url to cached data
                    final_data["company_url"] = str(request.company_url)
                    event["slug_id"] = slug
                    event["cached"] = False
                    event_json = json.dumps(event)
                
                yield f"data: {event_json}\n\n"
            
            # Cache the result
            if final_data:
                cache_by_slug(slug, final_data)
    
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

def build_competitor_summary(analysis_report: dict, top_n: int = 5) -> list:
    """Build simple competitor summary for dashboard display."""
    competitor_rankings = analysis_report.get("competitor_rankings", {})
    overall_rankings = competitor_rankings.get("overall", [])
    
    # Return top N competitors with simplified data
    summary = []
    for comp in overall_rankings[:top_n]:
        summary.append({
            "name": comp.get("name"),
            "mention_count": comp.get("total_mentions", 0),
            "visibility_score": comp.get("percentage", 0)
        })
    
    return summary


def clean_query_log(query_log: list) -> list:
    """Remove response_preview from query log entries."""
    cleaned = []
    for entry in query_log:
        cleaned_entry = {
            "query": entry.get("query"),
            "category": entry.get("category"),
            "results": {}
        }
        for model_name, result in entry.get("results", {}).items():
            cleaned_entry["results"][model_name] = {
                "mentioned": result.get("mentioned"),
                "rank": result.get("rank"),
                "competitors_mentioned": result.get("competitors_mentioned")
            }
        cleaned.append(cleaned_entry)
    return cleaned


def clean_category_analysis(analysis: dict) -> dict:
    """Remove sample_mentions and response_preview from category analysis."""
    cleaned = analysis.copy()
    # Remove sample_mentions if present
    cleaned.pop("sample_mentions", None)
    # Clean query_log if present
    if "query_log" in cleaned:
        cleaned["query_log"] = clean_query_log(cleaned["query_log"])
    return cleaned


async def visibility_analysis_stream(request: VisibilityAnalysisRequest, slug: str, company_slug: str, company_data: dict):
    """
    Stream visibility analysis workflow with category-based batching.
    
    Simple caching: If slug matches, stream cached data instantly.
    If not, run full analysis and cache with slug.
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
        yield emit("step1", "completed", {
            "industry": company_data.get("industry"),
            "company_name": company_data.get("company_name"),
            "competitors": company_data.get("competitors", [])[:5],
            "target_region": company_data.get("target_region", "United States")
        }, "Using cached company data")
        
        # Create thread-safe queue for real-time streaming
        from queue import Queue
        event_queue = Queue()
        result_container = {}
        
        def progress_callback(step, status, message, data):
            """Thread-safe callback to stream progress in real-time."""
            event_queue.put((step, status, message, data))
            logger.info(f"Progress: {step} - {message}")
        
        # Run visibility analysis in thread
        import concurrent.futures
        
        def run_analysis():
            try:
                result = execute_visibility_analysis(
                    company_data=company_data,
                    company_url=company_data.get("company_url", ""),
                    num_queries=request.num_queries,
                    models=request.models,
                    llm_provider=request.llm_provider,
                    progress_callback=progress_callback
                )
                result_container['result'] = result
            finally:
                # Signal completion
                event_queue.put(None)
        
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = executor.submit(run_analysis)
        
        # Stream progress updates in real-time as they arrive
        while True:
            try:
                event = event_queue.get(timeout=0.1)
                if event is None:  # Analysis completed
                    break
                step, status, message, data = event
                yield emit(step, status, data, message)
            except:
                # Queue empty, check if analysis is done
                if future.done():
                    # Drain any remaining events
                    while not event_queue.empty():
                        event = event_queue.get_nowait()
                        if event is not None:
                            step, status, message, data = event
                            yield emit(step, status, data, message)
                    break
                await asyncio.sleep(0.05)
        
        # Get final result
        future.result(timeout=1)  # Should be instant since it's done
        final_result = result_container.get('result')
        
        # Cache the complete results with slug
        cache_by_slug(slug, final_result)
        
        # Build complete response with all required fields
        analysis_report = final_result.get("analysis_report", {})
        
        # Get per-model scores with exact names and full breakdown
        from agents.visibility_orchestrator.nodes import get_exact_model_name
        by_model_raw = analysis_report.get("by_model", {})
        
        # Build model_scores (simple scores) and by_model (detailed breakdown)
        model_scores = {}
        by_model = {}
        for model_key, model_data in by_model_raw.items():
            exact_name = get_exact_model_name(model_key)
            mentions = model_data.get("mentions", 0)
            total = model_data.get("total_responses", 0)
            mention_rate = model_data.get("mention_rate", 0)
            score = (mentions / total * 100) if total > 0 else 0.0
            
            model_scores[exact_name] = round(score, 2)
            by_model[exact_name] = {
                "mentions": mentions,
                "total_responses": total,
                "mention_rate": round(mention_rate, 4),
                "score": round(score, 2)
            }
        
        # Build model-category matrix BEFORE cleaning (needs original data)
        model_category_matrix = {}
        for cat_data in analysis_report.get("category_breakdown", []):
            cat_key = cat_data.get("category")
            cat_analysis = cat_data.get("analysis", {})
            by_model_cat = cat_analysis.get("by_model", {})
            
            for model_key, model_cat_data in by_model_cat.items():
                exact_name = get_exact_model_name(model_key)
                if exact_name not in model_category_matrix:
                    model_category_matrix[exact_name] = {}
                
                mentions = model_cat_data.get("mentions", 0)
                total = model_cat_data.get("total_responses", 0)
                score = (mentions / total * 100) if total > 0 else 0.0
                model_category_matrix[exact_name][cat_key] = round(score, 2)
        
        # Build category breakdown with full details (cleaned)
        category_breakdown = []
        for cat in analysis_report.get("category_breakdown", []):
            category_breakdown.append({
                "category": cat.get("category"),
                "score": cat.get("score", 0),
                "queries": cat.get("queries", 0),
                "mentions": cat.get("mentions", 0),
                "analysis": clean_category_analysis(cat.get("analysis", {}))
            })
        
        # Build competitor summary for dashboard
        top_competitors = build_competitor_summary(analysis_report, top_n=5)
        
        # Send final event with complete data structure
        final_event_data = {
            "visibility_score": final_result.get("visibility_score", 0),
            "model_scores": model_scores,
            "total_queries": final_result.get("total_queries", 0),
            "total_mentions": analysis_report.get("total_mentions", 0),
            "categories_processed": len(category_breakdown),
            "category_breakdown": category_breakdown,
            "model_category_matrix": model_category_matrix,
            "top_competitors": top_competitors,
            "slug_id": slug,
            "analysis_report": {
                "total_mentions": analysis_report.get("total_mentions", 0),
                "total_responses": analysis_report.get("total_responses", 0),
                "mention_rate": analysis_report.get("mention_rate", 0),
                "by_model": by_model,
                "by_category": analysis_report.get("by_category", {}),
                "category_breakdown": category_breakdown
            }
        }
        
        yield emit("complete", "success", final_event_data, "Visibility analysis completed!")
        
    except Exception as e:
        logger.error(f"Error in visibility analysis: {str(e)}", exc_info=True)
        yield emit("error", "failed", {"error": str(e)}, f"Error: {str(e)}")


@router.post("/visibility")
async def analyze_visibility(request: VisibilityAnalysisRequest):
    """
    Phase 2: Visibility analysis with slug-based caching.
    
    Always streams SSE (even for cache hits) - simpler for frontend.
    
    Parameters:
    - company_slug_id: Slug from company analysis (required)
    - num_queries: Total queries (20-100, default: 20)
    - models: AI models to test (default: ["llama", "gemini"])
    - llm_provider: LLM for query generation (default: "llama")
    
    Returns: SSE stream with slug_id in final event
    """
    try:
        # Get company data using slug
        company_data = get_cached_by_slug(request.company_slug_id)
        
        if not company_data:
            raise ValueError(f"Company data not found for slug_id: {request.company_slug_id}. Please run POST /analyze/company first.")
        
        # Generate visibility slug
        company_url = company_data.get("company_url", "")
        if not company_url:
            raise ValueError("Company URL not found in cached data")
        
        visibility_slug = generate_visibility_slug(
            company_url,
            request.num_queries,
            request.models,
            request.llm_provider
        )
        
        # Check cache
        cached_result = get_cached_by_slug(visibility_slug)
        
        async def _stream_cached():
            if cached_result:
                # Stream cached data instantly - same format as live analysis
                from agents.visibility_orchestrator.nodes import get_exact_model_name
                
                analysis_report = cached_result.get("analysis_report", {})
                
                # Get per-model scores with exact names and full breakdown
                by_model_raw = analysis_report.get("by_model", {})
                model_scores = {}
                by_model = {}
                for model_key, model_data in by_model_raw.items():
                    exact_name = get_exact_model_name(model_key)
                    mentions = model_data.get("mentions", 0)
                    total = model_data.get("total_responses", 0)
                    mention_rate = model_data.get("mention_rate", 0)
                    score = (mentions / total * 100) if total > 0 else 0.0
                    
                    model_scores[exact_name] = round(score, 2)
                    by_model[exact_name] = {
                        "mentions": mentions,
                        "total_responses": total,
                        "mention_rate": round(mention_rate, 4),
                        "score": round(score, 2)
                    }
                
                # Build model-category matrix BEFORE cleaning (needs original data)
                model_category_matrix = {}
                for cat_data in analysis_report.get("category_breakdown", []):
                    cat_key = cat_data.get("category")
                    cat_analysis = cat_data.get("analysis", {})
                    by_model_cat = cat_analysis.get("by_model", {})
                    
                    for model_key, model_cat_data in by_model_cat.items():
                        exact_name = get_exact_model_name(model_key)
                        if exact_name not in model_category_matrix:
                            model_category_matrix[exact_name] = {}
                        
                        mentions = model_cat_data.get("mentions", 0)
                        total = model_cat_data.get("total_responses", 0)
                        score = (mentions / total * 100) if total > 0 else 0.0
                        model_category_matrix[exact_name][cat_key] = round(score, 2)
                
                # Build category breakdown with full details (cleaned)
                category_breakdown = []
                for cat in analysis_report.get("category_breakdown", []):
                    category_breakdown.append({
                        "category": cat.get("category"),
                        "score": cat.get("score", 0),
                        "queries": cat.get("queries", 0),
                        "mentions": cat.get("mentions", 0),
                        "analysis": clean_category_analysis(cat.get("analysis", {}))
                    })
                
                # Build competitor summary for dashboard
                top_competitors = build_competitor_summary(analysis_report, top_n=5)
                
                # Emit identical structure to live analysis
                final_event = {
                    "step": "complete",
                    "status": "success",
                    "message": "Visibility analysis completed!",
                    "data": {
                        "visibility_score": cached_result.get("visibility_score", 0),
                        "model_scores": model_scores,
                        "total_queries": cached_result.get("total_queries", 0),
                        "total_mentions": analysis_report.get("total_mentions", 0),
                        "categories_processed": len(category_breakdown),
                        "category_breakdown": category_breakdown,
                        "model_category_matrix": model_category_matrix,
                        "top_competitors": top_competitors,
                        "slug_id": visibility_slug,
                        # "analysis_report": {
                        #     "total_mentions": analysis_report.get("total_mentions", 0),
                        #     "total_responses": analysis_report.get("total_responses", 0),
                        #     "mention_rate": analysis_report.get("mention_rate", 0),
                        #     "by_model": by_model,
                        #     "by_category": analysis_report.get("by_category", {}),
                        #     "category_breakdown": category_breakdown
                        # }
                    },
                    "cached": True
                }
                
                yield f"data: {json.dumps(final_event)}\n\n"
            else:
                # Stream live analysis
                async for event in visibility_analysis_stream(request, visibility_slug, request.company_slug_id, company_data):
                    yield event
        
        return StreamingResponse(
            _stream_cached(),
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


# ============================================================================
# Report Endpoints - Detailed Analysis Data
# ============================================================================

class QueryLogRequest(BaseModel):
    """Request model for query log with pagination."""
    page: int = 1
    limit: int = 50
    category: Optional[str] = None
    model: Optional[str] = None
    mentioned: Optional[bool] = None
    
    class Config:
        extra = "forbid"


@report_router.get("/{slug_id}")
async def get_full_report(slug_id: str):
    """
    Get complete analysis report by slug_id.
    
    Use the slug_id returned from POST /analyze/visibility.
    
    Parameters:
    - slug_id: The slug returned from visibility analysis
    
    Example:
    ```
    GET /report/visibility_abc123def456
    ```
    
    Returns: Complete analysis with all detailed data
    """
    try:
        cached_result = get_cached_by_slug(slug_id)
        
        if not cached_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No analysis found for slug_id: {slug_id}"
            )
        
        analysis_report = cached_result.get("analysis_report", {})
        
        # Build comprehensive report
        report = {
            "slug_id": slug_id,
            "summary": {
                "visibility_score": cached_result.get("visibility_score", 0),
                "total_queries": cached_result.get("total_queries", 0),
                "total_mentions": analysis_report.get("total_mentions", 0),
                "total_responses": analysis_report.get("total_responses", 0),
                "mention_rate": analysis_report.get("mention_rate", 0)
            },
            "category_breakdown": analysis_report.get("category_breakdown", []),
            "competitor_rankings": analysis_report.get("competitor_rankings", []),
            "by_model": analysis_report.get("by_model", {}),
            "by_category": analysis_report.get("by_category", {}),
            "sample_mentions": analysis_report.get("sample_mentions", []),
            "company_info": {
                "name": cached_result.get("company_name", ""),
                "industry": cached_result.get("industry", ""),
                "competitors": cached_result.get("competitors", [])
            }
        }
        
        return report
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching report: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching report: {str(e)}"
        )


@report_router.post("/{slug_id}/query-log")
async def get_query_log(slug_id: str, request: QueryLogRequest):
    """
    Get paginated query log by slug_id.
    
    Use the slug_id returned from POST /analyze/visibility.
    
    Filtering:
    - category: Filter by category
    - model: Filter by model
    - mentioned: Filter by mentioned status
    
    Pagination:
    - page: Page number (default: 1)
    - limit: Per page (default: 50, max: 100)
    
    Example:
    ```
    POST /report/visibility_abc123def456/query-log
    {
        "page": 1,
        "limit": 50,
        "model": "chatgpt"
    }
    ```
    """
    try:
        # Validate pagination
        if request.limit > 100:
            raise ValueError("Limit cannot exceed 100")
        if request.page < 1:
            raise ValueError("Page must be >= 1")
        
        # Get cached analysis by slug
        cached_result = get_cached_by_slug(slug_id)
        
        if not cached_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No analysis found for slug_id: {slug_id}"
            )
        
        analysis_report = cached_result.get("analysis_report", {})
        
        # Query log is nested in category_breakdown -> analysis -> query_log
        # We need to aggregate from all categories
        query_log = []
        category_breakdown = analysis_report.get("category_breakdown", [])
        
        for category_data in category_breakdown:
            category_analysis = category_data.get("analysis", {})
            category_queries = category_analysis.get("query_log", [])
            query_log.extend(category_queries)
        
        logger.info(f"Query log has {len(query_log)} total queries from {len(category_breakdown)} categories")
        
        # Apply filters
        filtered_queries = query_log
        
        if request.category:
            filtered_queries = [q for q in filtered_queries if q.get("category") == request.category]
            logger.info(f"After category filter '{request.category}': {len(filtered_queries)} queries")
        
        if request.model:
            filtered_queries = [
                q for q in filtered_queries 
                if request.model in q.get("results", {})
            ]
            logger.info(f"After model filter '{request.model}': {len(filtered_queries)} queries")
        
        if request.mentioned is not None:
            filtered_queries = [
                q for q in filtered_queries
                if any(
                    result.get("mentioned") == request.mentioned
                    for result in q.get("results", {}).values()
                )
            ]
            logger.info(f"After mentioned filter '{request.mentioned}': {len(filtered_queries)} queries")
        
        # Pagination
        total = len(filtered_queries)
        total_pages = (total + request.limit - 1) // request.limit
        start_idx = (request.page - 1) * request.limit
        end_idx = start_idx + request.limit
        
        paginated_queries = filtered_queries[start_idx:end_idx]
        
        return {
            "total": total,
            "page": request.page,
            "limit": request.limit,
            "total_pages": total_pages,
            "queries": paginated_queries,
            "filters": {
                "category": request.category,
                "model": request.model,
                "mentioned": request.mentioned
            }
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching query log: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching query log: {str(e)}"
        )
