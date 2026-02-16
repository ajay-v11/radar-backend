"""
Job Management Routes

Endpoints for job status, history, streaming, and cancellation.
"""
import asyncio
import json
import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.core.config.database import get_async_session
from app.core.queue import get_job_queue
from app.models.db import User, Job, JobStatus, JobType
from app.services import job_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["Jobs"])


# ============================================================================
# Response Models
# ============================================================================

class JobResponse(BaseModel):
    """Job status response."""
    id: int
    status: str
    type: str
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    queue_position: Optional[int] = None
    result: Optional[dict] = None
    error: Optional[str] = None
    params: Optional[dict] = None


class JobListResponse(BaseModel):
    """Paginated job list response."""
    jobs: List[JobResponse]
    total: int
    page: int
    limit: int
    total_pages: int


class JobEventResponse(BaseModel):
    """Job event response."""
    id: int
    step: str
    status: str
    message: Optional[str] = None
    data: Optional[dict] = None
    created_at: str


# ============================================================================
# Job Status Endpoints
# ============================================================================

@router.get("/{job_id}", response_model=JobResponse)
async def get_job_status(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get job status by ID.
    
    Returns job status, timestamps, result (if completed), or error (if failed).
    """
    job = await job_service.get_job_by_id(db, job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Verify user owns the job
    if job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this job"
        )
    
    # Get queue position if job is queued
    queue_position = None
    if job.status == JobStatus.QUEUED:
        job_queue = get_job_queue()
        queue_position = await job_queue.get_position(job.id)
    
    return JobResponse(
        id=job.id,
        status=job.status.value,
        type=job.type.value,
        created_at=job.created_at.isoformat(),
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        queue_position=queue_position,
        result=job.result if job.status == JobStatus.COMPLETED else None,
        error=job.error if job.status == JobStatus.FAILED else None,
        params=job.params
    )


@router.get("", response_model=JobListResponse)
async def get_user_jobs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    type_filter: Optional[str] = Query(None, alias="type"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get user's job history with pagination and filtering.
    
    Parameters:
    - page: Page number (default: 1)
    - limit: Jobs per page (default: 20, max: 100)
    - status: Filter by status (PENDING, QUEUED, RUNNING, COMPLETED, FAILED, CANCELLED)
    - type: Filter by type (company_analysis, visibility_analysis)
    """
    # Parse filters
    job_status = None
    if status_filter:
        try:
            job_status = JobStatus(status_filter)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}"
            )
    
    job_type = None
    if type_filter:
        try:
            job_type = JobType(type_filter)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid type: {type_filter}"
            )
    
    # Get jobs
    offset = (page - 1) * limit
    jobs = await job_service.get_user_jobs(
        db=db,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
        status=job_status,
        job_type=job_type
    )
    
    # Get total count for pagination
    all_jobs = await job_service.get_user_jobs(
        db=db,
        user_id=current_user.id,
        limit=1000,  # Get all for count
        offset=0,
        status=job_status,
        job_type=job_type
    )
    total = len(all_jobs)
    total_pages = (total + limit - 1) // limit
    
    # Get queue positions for queued jobs
    job_queue = get_job_queue()
    
    job_responses = []
    for job in jobs:
        queue_position = None
        if job.status == JobStatus.QUEUED:
            queue_position = await job_queue.get_position(job.id)
        
        job_responses.append(JobResponse(
            id=job.id,
            status=job.status.value,
            type=job.type.value,
            created_at=job.created_at.isoformat(),
            started_at=job.started_at.isoformat() if job.started_at else None,
            completed_at=job.completed_at.isoformat() if job.completed_at else None,
            queue_position=queue_position,
            result=job.result if job.status == JobStatus.COMPLETED else None,
            error=job.error if job.status == JobStatus.FAILED else None,
            params=job.params
        ))
    
    return JobListResponse(
        jobs=job_responses,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages
    )


# ============================================================================
# Job Events Endpoint
# ============================================================================

@router.get("/{job_id}/events", response_model=List[JobEventResponse])
async def get_job_events(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get all events for a job.
    
    Returns list of events in chronological order.
    """
    job = await job_service.get_job_by_id(db, job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    if job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this job"
        )
    
    events = await job_service.get_job_events(db, job_id)
    
    return [
        JobEventResponse(
            id=event.id,
            step=event.step,
            status=event.status,
            message=event.message,
            data=event.data,
            created_at=event.created_at.isoformat()
        )
        for event in events
    ]


# ============================================================================
# Job Stream Endpoint (SSE with Replay)
# ============================================================================

@router.get("/{job_id}/stream")
async def stream_job_events(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Stream job events via SSE with replay capability.
    
    1. Replays past events from database (for reconnections)
    2. Streams live events if job is still running
    3. Sends final completion event when job completes
    """
    job = await job_service.get_job_by_id(db, job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    if job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this job"
        )
    
    async def event_generator():
        # 1. Replay past events from database
        events = await job_service.get_job_events(db, job_id)
        for event in events:
            event_data = {
                "step": event.step,
                "status": event.status,
                "message": event.message,
                "data": event.data
            }
            yield f"data: {json.dumps(event_data)}\n\n"
        
        # 2. Check current job status
        current_job = await job_service.get_job_by_id(db, job_id)
        
        # 3. If job is still running, poll for new events
        if current_job and current_job.status in [JobStatus.PENDING, JobStatus.QUEUED, JobStatus.RUNNING]:
            last_event_id = events[-1].id if events else 0
            
            while True:
                await asyncio.sleep(0.5)  # Poll every 500ms
                
                # Get new events
                all_events = await job_service.get_job_events(db, job_id)
                new_events = [e for e in all_events if e.id > last_event_id]
                
                for event in new_events:
                    event_data = {
                        "step": event.step,
                        "status": event.status,
                        "message": event.message,
                        "data": event.data
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"
                    last_event_id = event.id
                
                # Check if job completed
                current_job = await job_service.get_job_by_id(db, job_id)
                if current_job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                    break
        
        # 4. Send final completion event
        final_job = await job_service.get_job_by_id(db, job_id)
        if final_job.status == JobStatus.COMPLETED:
            final_event = {
                "step": "complete",
                "status": "success",
                "message": "Job completed successfully",
                "data": final_job.result
            }
            yield f"data: {json.dumps(final_event)}\n\n"
        elif final_job.status == JobStatus.FAILED:
            error_event = {
                "step": "error",
                "status": "failed",
                "message": final_job.error or "Job failed",
                "data": {"error": final_job.error}
            }
            yield f"data: {json.dumps(error_event)}\n\n"
        elif final_job.status == JobStatus.CANCELLED:
            cancel_event = {
                "step": "cancelled",
                "status": "cancelled",
                "message": "Job was cancelled",
                "data": None
            }
            yield f"data: {json.dumps(cancel_event)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ============================================================================
# Job Cancellation Endpoint
# ============================================================================

@router.delete("/{job_id}")
async def cancel_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Cancel a job.
    
    Only PENDING or QUEUED jobs can be cancelled.
    Running jobs cannot be cancelled.
    Quota is refunded on cancellation.
    """
    job = await job_service.get_job_by_id(db, job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    if job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to cancel this job"
        )
    
    # Check if job can be cancelled
    if job.status == JobStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel a running job"
        )
    
    if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job is already {job.status.value.lower()}"
        )
    
    # Remove from queue if queued
    if job.status == JobStatus.QUEUED:
        job_queue = get_job_queue()
        await job_queue.remove(job.id)
    
    # Update job status
    await job_service.update_job_status(db, job.id, JobStatus.CANCELLED)
    
    # Refund quota
    from app.core.rate_limit import decrement_quota
    await decrement_quota(db, current_user.id)
    
    return {
        "message": "Job cancelled successfully",
        "job_id": job.id,
        "quota_refunded": True
    }
