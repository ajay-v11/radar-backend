"""
Analysis Routes

Two-phase analysis workflow with job-based system:
1. Company Analysis (Phase 1) - Scraping, industry detection, competitor identification
2. Visibility Analysis (Phase 2) - Query generation, model testing, scoring

Both phases support:
- Job-based async processing with queue management
- Idempotency (same request returns existing job)
- Quota enforcement
- SSE streaming for real-time progress
"""
import asyncio
import hashlib
import logging
import json
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, get_optional_user
from app.core.config.database import get_async_session
from app.core.rate_limit import check_user_quota, increment_quota
from app.core.queue import get_job_queue
from app.models.db import User, Job, JobStatus, JobType
from app.services import job_service

from app.api.controllers.industry_controller import analyze_company_stream
from app.api.controllers.analysis_controller import execute_visibility_analysis
from app.api.controllers.cache_manager import (
    generate_analysis_slug,
    generate_visibility_slug,
    get_cached_by_slug,
    cache_by_slug
)
from app.utils.report_generator import generate_csv_report

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
    llm_provider: str = "openai"
    
    class Config:
        extra = "forbid"


class JobCreatedResponse(BaseModel):
    """Response when a job is created."""
    job_id: int
    status: str
    message: str
    queue_position: Optional[int] = None
    existing: bool = False


# ============================================================================
# Helper Functions
# ============================================================================

def generate_idempotency_key(user_id: int, company_url: str, job_type: str, extra: str = "") -> str:
    """Generate idempotency key for job deduplication."""
    key = f"{user_id}:{company_url}:{job_type}:{extra}"
    return hashlib.sha256(key.encode()).hexdigest()


# ============================================================================
# Phase 1: Company Analysis (Job-Based)
# ============================================================================

@router.post("/company", response_model=JobCreatedResponse)
async def create_company_analysis_job(
    request: CompanyAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Phase 1: Create company analysis job.
    
    Creates a job for company analysis. If an identical job already exists
    (same user + URL), returns the existing job (idempotency).
    
    Parameters:
    - company_url: Company website URL (required)
    - company_name: Optional company name override
    - target_region: Target region for AI model context (default: "United States")
    
    Returns: Job ID and status
    """
    # Generate idempotency key
    idempotency_key = generate_idempotency_key(
        current_user.id,
        str(request.company_url),
        "company"
    )
    
    # Check for existing active job
    existing_job = await job_service.get_job_by_idempotency_key(db, idempotency_key)
    if existing_job and existing_job.status in [JobStatus.PENDING, JobStatus.QUEUED, JobStatus.RUNNING]:
        # Return existing job
        job_queue = get_job_queue()
        queue_position = await job_queue.get_position(existing_job.id) if existing_job.status == JobStatus.QUEUED else None
        
        return JobCreatedResponse(
            job_id=existing_job.id,
            status=existing_job.status.value,
            message="Job already exists. Connect to stream for updates.",
            queue_position=queue_position,
            existing=True
        )
    
    # Check quota
    await check_user_quota(db, current_user)
    
    # Create new job
    job = await job_service.create_job(
        db=db,
        user_id=current_user.id,
        idempotency_key=idempotency_key,
        job_type=JobType.COMPANY_ANALYSIS,
        params={
            "company_url": str(request.company_url),
            "company_name": request.company_name,
            "target_region": request.target_region
        },
        status=JobStatus.QUEUED
    )
    
    # Enqueue job
    job_queue = get_job_queue()
    try:
        queue_position = await job_queue.enqueue(job.id)
        await job_service.update_job_queue_position(db, job.id, queue_position)
    except ValueError as e:
        # Queue full - cancel job
        await job_service.update_job_status(db, job.id, JobStatus.CANCELLED)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    
    # Increment quota
    await increment_quota(db, current_user.id)
    
    logger.info(f"Created company analysis job {job.id} for user {current_user.id}")
    
    return JobCreatedResponse(
        job_id=job.id,
        status=JobStatus.QUEUED.value,
        message="Job created successfully. Connect to /jobs/{job_id}/stream for updates.",
        queue_position=queue_position,
        existing=False
    )


@router.post("/company/stream")
async def analyze_company_stream_legacy(
    request: CompanyAnalysisRequest,
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Phase 1: Company Analysis with direct SSE streaming (legacy).
    
    This endpoint provides backward compatibility with the old streaming API.
    For new integrations, use POST /analyze/company to create a job,
    then GET /jobs/{job_id}/stream for SSE updates.
    
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
# Phase 2: Visibility Analysis (Job-Based)
# ============================================================================

@router.post("/visibility", response_model=JobCreatedResponse)
async def create_visibility_analysis_job(
    request: VisibilityAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Phase 2: Create visibility analysis job.
    
    Creates a job for visibility analysis. If an identical job already exists
    (same user + slug + params), returns the existing job (idempotency).
    
    Parameters:
    - company_slug_id: Slug from company analysis (required)
    - num_queries: Total queries (20-100, default: 20)
    - models: AI models to test (default: ["llama", "gemini"])
    - llm_provider: LLM for query generation (default: "openai")
    
    Returns: Job ID and status
    """
    # Verify company data exists
    company_data = get_cached_by_slug(request.company_slug_id)
    if not company_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Company data not found for slug_id: {request.company_slug_id}. Please run company analysis first."
        )
    
    company_url = company_data.get("company_url", "")
    
    # Generate idempotency key (includes params for uniqueness)
    extra = f"{request.num_queries}:{','.join(sorted(request.models))}:{request.llm_provider}"
    idempotency_key = generate_idempotency_key(
        current_user.id,
        company_url,
        "visibility",
        extra
    )
    
    # Check for existing active job
    existing_job = await job_service.get_job_by_idempotency_key(db, idempotency_key)
    if existing_job and existing_job.status in [JobStatus.PENDING, JobStatus.QUEUED, JobStatus.RUNNING]:
        job_queue = get_job_queue()
        queue_position = await job_queue.get_position(existing_job.id) if existing_job.status == JobStatus.QUEUED else None
        
        return JobCreatedResponse(
            job_id=existing_job.id,
            status=existing_job.status.value,
            message="Job already exists. Connect to stream for updates.",
            queue_position=queue_position,
            existing=True
        )
    
    # Check quota
    await check_user_quota(db, current_user)
    
    # Create new job
    job = await job_service.create_job(
        db=db,
        user_id=current_user.id,
        idempotency_key=idempotency_key,
        job_type=JobType.VISIBILITY_ANALYSIS,
        params={
            "company_slug_id": request.company_slug_id,
            "company_url": company_url,
            "num_queries": request.num_queries,
            "models": request.models,
            "llm_provider": request.llm_provider
        },
        status=JobStatus.QUEUED
    )
    
    # Enqueue job
    job_queue = get_job_queue()
    try:
        queue_position = await job_queue.enqueue(job.id)
        await job_service.update_job_queue_position(db, job.id, queue_position)
    except ValueError as e:
        await job_service.update_job_status(db, job.id, JobStatus.CANCELLED)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    
    # Increment quota
    await increment_quota(db, current_user.id)
    
    logger.info(f"Created visibility analysis job {job.id} for user {current_user.id}")
    
    return JobCreatedResponse(
        job_id=job.id,
        status=JobStatus.QUEUED.value,
        message="Job created successfully. Connect to /jobs/{job_id}/stream for updates.",
        queue_position=queue_position,
        existing=False
    )


@router.post("/visibility/stream")
async def analyze_visibility_stream_legacy(
    request: VisibilityAnalysisRequest,
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Phase 2: Visibility analysis with direct SSE streaming (legacy).
    
    This endpoint provides backward compatibility with the old streaming API.
    For new integrations, use POST /analyze/visibility to create a job,
    then GET /jobs/{job_id}/stream for SSE updates.
    """
    try:
        company_data = get_cached_by_slug(request.company_slug_id)
        
        if not company_data:
            raise ValueError(f"Company data not found for slug_id: {request.company_slug_id}")
        
        company_url = company_data.get("company_url", "")
        if not company_url:
            raise ValueError("Company URL not found in cached data")
        
        visibility_slug = generate_visibility_slug(
            company_url,
            request.num_queries,
            request.models,
            request.llm_provider
        )
        
        cached_result = get_cached_by_slug(visibility_slug)
        
        async def _stream():
            if cached_result:
                # Stream cached data
                from app.services.agents.visibility_orchestrator.nodes import get_exact_model_name
                
                analysis_report = cached_result.get("analysis_report", {})
                by_model_raw = analysis_report.get("by_model", {})
                model_scores = {}
                
                for model_key, model_data in by_model_raw.items():
                    exact_name = get_exact_model_name(model_key)
                    mentions = model_data.get("mentions", 0)
                    total = model_data.get("total_responses", 0)
                    score = (mentions / total * 100) if total > 0 else 0.0
                    model_scores[exact_name] = round(score, 2)
                
                category_breakdown = []
                for cat in analysis_report.get("category_breakdown", []):
                    category_breakdown.append({
                        "category": cat.get("category"),
                        "score": cat.get("score", 0),
                        "queries": cat.get("queries", 0),
                        "mentions": cat.get("mentions", 0)
                    })
                
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
                        "slug_id": visibility_slug
                    },
                    "cached": True
                }
                yield f"data: {json.dumps(final_event)}\n\n"
            else:
                # Stream live analysis
                async for event in visibility_analysis_stream_internal(
                    request, visibility_slug, request.company_slug_id, company_data
                ):
                    yield event
        
        return StreamingResponse(
            _stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating stream: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def visibility_analysis_stream_internal(request, slug, company_slug, company_data):
    """Internal streaming function for visibility analysis."""
    from queue import Queue
    import concurrent.futures
    from app.services.agents.visibility_orchestrator.nodes import get_exact_model_name
    
    def emit(step: str, status: str, data: dict = None, message: str = ""):
        event = {"step": step, "status": status, "message": message, "data": data or {}}
        return f"data: {json.dumps(event)}\n\n"
    
    try:
        yield emit("step1", "completed", {
            "industry": company_data.get("industry"),
            "company_name": company_data.get("company_name"),
            "competitors": company_data.get("competitors", [])[:5],
            "target_region": company_data.get("target_region", "United States")
        }, "Using cached company data")
        
        event_queue = Queue()
        result_container = {}
        
        def progress_callback(step, status, message, data):
            event_queue.put((step, status, message, data))
        
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
                event_queue.put(None)
        
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = executor.submit(run_analysis)
        
        while True:
            try:
                event = event_queue.get(timeout=0.1)
                if event is None:
                    break
                step, status, message, data = event
                yield emit(step, status, data, message)
            except:
                if future.done():
                    while not event_queue.empty():
                        event = event_queue.get_nowait()
                        if event is not None:
                            step, status, message, data = event
                            yield emit(step, status, data, message)
                    break
                await asyncio.sleep(0.05)
        
        future.result(timeout=1)
        final_result = result_container.get('result')
        
        cache_by_slug(slug, final_result)
        
        analysis_report = final_result.get("analysis_report", {})
        by_model_raw = analysis_report.get("by_model", {})
        model_scores = {}
        
        for model_key, model_data in by_model_raw.items():
            exact_name = get_exact_model_name(model_key)
            mentions = model_data.get("mentions", 0)
            total = model_data.get("total_responses", 0)
            score = (mentions / total * 100) if total > 0 else 0.0
            model_scores[exact_name] = round(score, 2)
        
        category_breakdown = []
        for cat in analysis_report.get("category_breakdown", []):
            category_breakdown.append({
                "category": cat.get("category"),
                "score": cat.get("score", 0),
                "queries": cat.get("queries", 0),
                "mentions": cat.get("mentions", 0)
            })
        
        final_event_data = {
            "visibility_score": final_result.get("visibility_score", 0),
            "model_scores": model_scores,
            "total_queries": final_result.get("total_queries", 0),
            "total_mentions": analysis_report.get("total_mentions", 0),
            "categories_processed": len(category_breakdown),
            "category_breakdown": category_breakdown,
            "slug_id": slug
        }
        
        yield emit("complete", "success", final_event_data, "Visibility analysis completed!")
        
    except Exception as e:
        logger.error(f"Error in visibility analysis: {str(e)}", exc_info=True)
        yield emit("error", "failed", {"error": str(e)}, f"Error: {str(e)}")


# ============================================================================
# Report Endpoints
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
    """Get complete analysis report by slug_id."""
    try:
        cached_result = get_cached_by_slug(slug_id)
        
        if not cached_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No analysis found for slug_id: {slug_id}"
            )
        
        analysis_report = cached_result.get("analysis_report", {})
        
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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@report_router.post("/{slug_id}/query-log")
async def get_query_log(slug_id: str, request: QueryLogRequest):
    """Get paginated query log by slug_id."""
    try:
        if request.limit > 100:
            raise ValueError("Limit cannot exceed 100")
        if request.page < 1:
            raise ValueError("Page must be >= 1")
        
        cached_result = get_cached_by_slug(slug_id)
        
        if not cached_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No analysis found for slug_id: {slug_id}"
            )
        
        analysis_report = cached_result.get("analysis_report", {})
        query_log = []
        category_breakdown = analysis_report.get("category_breakdown", [])
        
        for category_data in category_breakdown:
            category_analysis = category_data.get("analysis", {})
            category_queries = category_analysis.get("query_log", [])
            query_log.extend(category_queries)
        
        filtered_queries = query_log
        
        if request.category:
            filtered_queries = [q for q in filtered_queries if q.get("category") == request.category]
        
        if request.model:
            filtered_queries = [q for q in filtered_queries if request.model in q.get("results", {})]
        
        if request.mentioned is not None:
            filtered_queries = [
                q for q in filtered_queries
                if any(result.get("mentioned") == request.mentioned for result in q.get("results", {}).values())
            ]
        
        total = len(filtered_queries)
        total_pages = (total + request.limit - 1) // request.limit
        start_idx = (request.page - 1) * request.limit
        end_idx = start_idx + request.limit
        
        return {
            "total": total,
            "page": request.page,
            "limit": request.limit,
            "total_pages": total_pages,
            "queries": filtered_queries[start_idx:end_idx],
            "filters": {"category": request.category, "model": request.model, "mentioned": request.mentioned}
        }
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching query log: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@report_router.get("/{slug_id}/export/csv")
async def export_csv_report(slug_id: str):
    """Export complete visibility analysis as CSV file."""
    try:
        cached_result = get_cached_by_slug(slug_id)
        
        if not cached_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No analysis found for slug_id: {slug_id}"
            )
        
        csv_content = generate_csv_report(cached_result)
        company_name = cached_result.get("company_name", "company")
        safe_company_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in company_name)
        filename = f"{safe_company_name}_visibility_report.csv"
        
        from fastapi.responses import Response
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating CSV report: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
