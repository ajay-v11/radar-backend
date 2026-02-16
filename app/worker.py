"""
Background Worker for Job Processing

This worker processes jobs sequentially from the Redis queue.
Only one job runs at a time to respect free-tier API rate limits.

Usage:
    python -m app.worker
"""
import asyncio
import logging
import signal
import sys
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.database import async_session_maker, get_redis_client
from app.core.queue import get_job_queue
from app.models.db import Job, JobStatus, JobType
from app.services import job_service, user_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Graceful shutdown flag
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_requested = True


async def process_company_analysis(job: Job, db: AsyncSession) -> dict:
    """
    Process a company analysis job.
    
    Args:
        job: Job object with params
        db: Database session
        
    Returns:
        Analysis result dict
    """
    from app.services.agents.industry_detection_agent import run_industry_detection_workflow
    from app.core.config.settings import settings
    
    params = job.params
    company_url = params.get("company_url")
    company_name = params.get("company_name", "")
    target_region = params.get("target_region", "United States")
    
    logger.info(f"Processing company analysis for {company_url}")
    
    # Create progress callback to store events
    async def store_event(step: str, status: str, message: str, data: dict = None):
        async with async_session_maker() as event_db:
            await job_service.create_job_event(
                db=event_db,
                job_id=job.id,
                step=step,
                status=status,
                message=message,
                data=data
            )
    
    def progress_callback(step, status, message, data):
        """Sync callback that schedules async event storage."""
        asyncio.create_task(store_event(step, status, message, data))
    
    # Store initialization event
    await store_event("initialize", "started", f"Starting analysis for {company_url}")
    
    # Run the workflow
    result = await asyncio.to_thread(
        run_industry_detection_workflow,
        company_url=company_url,
        company_name=company_name,
        company_description="",
        competitor_urls={},
        llm_provider=settings.INDUSTRY_ANALYSIS_PROVIDER,
        target_region=target_region,
        progress_callback=progress_callback
    )
    
    # Store completion event
    await store_event("complete", "success", "Company analysis completed", result)
    
    return result


async def process_visibility_analysis(job: Job, db: AsyncSession) -> dict:
    """
    Process a visibility analysis job.
    
    Args:
        job: Job object with params
        db: Database session
        
    Returns:
        Analysis result dict
    """
    from app.api.controllers.analysis_controller import execute_visibility_analysis
    from app.api.controllers.cache_manager import get_cached_by_slug
    
    params = job.params
    company_slug_id = params.get("company_slug_id")
    num_queries = params.get("num_queries", 20)
    models = params.get("models", ["llama", "gemini"])
    llm_provider = params.get("llm_provider", "openai")
    
    logger.info(f"Processing visibility analysis for slug {company_slug_id}")
    
    # Get company data from cache
    company_data = get_cached_by_slug(company_slug_id)
    if not company_data:
        raise ValueError(f"Company data not found for slug_id: {company_slug_id}")
    
    company_url = company_data.get("company_url", "")
    
    # Create progress callback to store events
    async def store_event(step: str, status: str, message: str, data: dict = None):
        async with async_session_maker() as event_db:
            await job_service.create_job_event(
                db=event_db,
                job_id=job.id,
                step=step,
                status=status,
                message=message,
                data=data
            )
    
    def progress_callback(step, status, message, data):
        """Sync callback that schedules async event storage."""
        # Run in event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    store_event(step, status, message, data),
                    loop
                )
            else:
                asyncio.run(store_event(step, status, message, data))
        except Exception as e:
            logger.warning(f"Failed to store event: {e}")
    
    # Store initialization event
    await store_event("initialization", "started", "Starting visibility analysis", {
        "company_name": company_data.get("company_name"),
        "num_queries": num_queries,
        "models": models
    })
    
    # Run the analysis
    result = execute_visibility_analysis(
        company_data=company_data,
        company_url=company_url,
        num_queries=num_queries,
        models=models,
        llm_provider=llm_provider,
        progress_callback=progress_callback
    )
    
    # Store completion event
    await store_event("complete", "success", "Visibility analysis completed", {
        "visibility_score": result.get("visibility_score", 0),
        "total_queries": result.get("total_queries", 0)
    })
    
    return result


async def process_job(job_id: int) -> bool:
    """
    Process a single job.
    
    Args:
        job_id: Job ID to process
        
    Returns:
        True if successful, False if failed
    """
    async with async_session_maker() as db:
        try:
            # Get job
            job = await job_service.get_job_by_id(db, job_id)
            if not job:
                logger.error(f"Job {job_id} not found")
                return False
            
            # Update status to RUNNING
            await job_service.update_job_status(db, job_id, JobStatus.RUNNING)
            logger.info(f"Job {job_id} ({job.type.value}) started")
            
            # Process based on job type
            result = None
            if job.type == JobType.COMPANY_ANALYSIS:
                result = await process_company_analysis(job, db)
            elif job.type == JobType.VISIBILITY_ANALYSIS:
                result = await process_visibility_analysis(job, db)
            else:
                raise ValueError(f"Unknown job type: {job.type}")
            
            # Update job with result
            await job_service.update_job_status(
                db=db,
                job_id=job_id,
                status=JobStatus.COMPLETED,
                result=result
            )
            
            logger.info(f"Job {job_id} completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Job {job_id} failed: {str(e)}", exc_info=True)
            
            # Update job with error
            await job_service.update_job_status(
                db=db,
                job_id=job_id,
                status=JobStatus.FAILED,
                error=str(e)
            )
            
            # Refund quota
            try:
                job = await job_service.get_job_by_id(db, job_id)
                if job:
                    await user_service.update_user_quota(db, job.user_id, increment=-1)
                    logger.info(f"Quota refunded for user {job.user_id}")
            except Exception as refund_error:
                logger.error(f"Failed to refund quota: {refund_error}")
            
            return False


async def worker_loop():
    """
    Main worker loop that processes jobs sequentially.
    """
    global shutdown_requested
    
    job_queue = get_job_queue()
    logger.info("Worker started, waiting for jobs...")
    
    while not shutdown_requested:
        try:
            # Try to dequeue a job (with 5 second timeout)
            job_id = await job_queue.dequeue(timeout=5)
            
            if job_id:
                # Process the job
                success = await process_job(job_id)
                
                # Clear processing marker
                await job_queue.clear_processing()
                
                # Update queue positions for remaining jobs
                positions = await job_queue.update_positions()
                if positions:
                    async with async_session_maker() as db:
                        for jid, pos in positions.items():
                            await job_service.update_job_queue_position(db, jid, pos)
                
                if success:
                    logger.info(f"Job {job_id} processed successfully")
                else:
                    logger.warning(f"Job {job_id} failed")
            
        except Exception as e:
            logger.error(f"Worker error: {e}", exc_info=True)
            await asyncio.sleep(5)  # Backoff on error
    
    logger.info("Worker shutting down...")


async def main():
    """Main entry point for the worker."""
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("=" * 50)
    logger.info("RADAR Job Worker")
    logger.info("=" * 50)
    
    # Test database connections
    try:
        from app.core.config.database import test_connections
        status = test_connections()
        
        if status["postgres"]["connected"]:
            logger.info("✅ Postgres: Connected")
        else:
            logger.error(f"❌ Postgres: {status['postgres']['error']}")
            sys.exit(1)
        
        if status["redis"]["connected"]:
            logger.info("✅ Redis: Connected")
        else:
            logger.error(f"❌ Redis: {status['redis']['error']}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Failed to connect to databases: {e}")
        sys.exit(1)
    
    # Start worker loop
    await worker_loop()


if __name__ == "__main__":
    asyncio.run(main())
