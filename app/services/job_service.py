"""
Job service for CRUD operations on Job and JobEvent models.
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime

from app.models.db import Job, JobEvent, JobStatus, JobType


async def create_job(
    db: AsyncSession,
    user_id: int,
    idempotency_key: str,
    job_type: JobType,
    params: Dict[str, Any],
    status: JobStatus = JobStatus.PENDING
) -> Job:
    """Create a new job."""
    job = Job(
        user_id=user_id,
        idempotency_key=idempotency_key,
        type=job_type,
        status=status,
        params=params
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def get_job_by_id(db: AsyncSession, job_id: int) -> Optional[Job]:
    """Get job by ID."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    return result.scalar_one_or_none()


async def get_job_by_idempotency_key(
    db: AsyncSession,
    idempotency_key: str
) -> Optional[Job]:
    """Get job by idempotency key."""
    result = await db.execute(
        select(Job).where(Job.idempotency_key == idempotency_key)
    )
    return result.scalar_one_or_none()


async def update_job_status(
    db: AsyncSession,
    job_id: int,
    status: JobStatus,
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None
) -> Optional[Job]:
    """Update job status and optionally result/error."""
    job = await get_job_by_id(db, job_id)
    if not job:
        return None
    
    job.status = status
    job.updated_at = datetime.utcnow()
    
    if status == JobStatus.RUNNING and not job.started_at:
        job.started_at = datetime.utcnow()
    
    if status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
        job.completed_at = datetime.utcnow()
    
    if result is not None:
        job.result = result
    
    if error is not None:
        job.error = error
    
    await db.commit()
    await db.refresh(job)
    return job


async def update_job_queue_position(
    db: AsyncSession,
    job_id: int,
    queue_position: int
) -> Optional[Job]:
    """Update job queue position."""
    job = await get_job_by_id(db, job_id)
    if not job:
        return None
    
    job.queue_position = queue_position
    job.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(job)
    return job


async def get_user_jobs(
    db: AsyncSession,
    user_id: int,
    limit: int = 50,
    offset: int = 0,
    status: Optional[JobStatus] = None,
    job_type: Optional[JobType] = None
) -> List[Job]:
    """
    Get user's jobs with optional filtering.
    
    Args:
        db: Database session
        user_id: User ID
        limit: Maximum number of jobs to return
        offset: Number of jobs to skip
        status: Optional status filter
        job_type: Optional job type filter
    
    Returns:
        List of jobs
    """
    query = select(Job).where(Job.user_id == user_id)
    
    if status:
        query = query.where(Job.status == status)
    
    if job_type:
        query = query.where(Job.type == job_type)
    
    query = query.order_by(desc(Job.created_at)).limit(limit).offset(offset)
    
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_job_event(
    db: AsyncSession,
    job_id: int,
    step: str,
    status: str,
    message: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None
) -> JobEvent:
    """Create a new job event."""
    event = JobEvent(
        job_id=job_id,
        step=step,
        status=status,
        message=message,
        data=data
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def get_job_events(
    db: AsyncSession,
    job_id: int,
    limit: Optional[int] = None
) -> List[JobEvent]:
    """Get all events for a job, ordered by creation time."""
    query = select(JobEvent).where(JobEvent.job_id == job_id).order_by(JobEvent.created_at)
    
    if limit:
        query = query.limit(limit)
    
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_active_jobs(
    db: AsyncSession,
    statuses: List[JobStatus] = None
) -> List[Job]:
    """
    Get all active jobs (PENDING, QUEUED, RUNNING).
    
    Args:
        db: Database session
        statuses: Optional list of statuses to filter by
    
    Returns:
        List of active jobs
    """
    if statuses is None:
        statuses = [JobStatus.PENDING, JobStatus.QUEUED, JobStatus.RUNNING]
    
    query = select(Job).where(Job.status.in_(statuses)).order_by(Job.created_at)
    result = await db.execute(query)
    return list(result.scalars().all())
