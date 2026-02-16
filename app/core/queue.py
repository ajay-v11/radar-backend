"""
Redis Job Queue for sequential job processing.

This module provides a FIFO queue backed by Redis for managing
analysis jobs. Only one job runs at a time to respect API rate limits.
"""
import asyncio
import json
import logging
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from app.core.config.database import get_redis_client

logger = logging.getLogger(__name__)

QUEUE_KEY = "radar:job_queue"
PROCESSING_KEY = "radar:job_processing"
MAX_QUEUE_DEPTH = 20


class JobQueue:
    """Redis-backed FIFO job queue."""
    
    def __init__(self):
        self._redis = None
    
    @property
    def redis(self):
        if self._redis is None:
            self._redis = get_redis_client()
        return self._redis
    
    async def enqueue(self, job_id: int) -> int:
        """
        Add job to queue.
        
        Args:
            job_id: Job ID to enqueue
            
        Returns:
            Queue position (1-indexed)
            
        Raises:
            ValueError: If queue is full
        """
        current_length = self.redis.llen(QUEUE_KEY)
        if current_length >= MAX_QUEUE_DEPTH:
            raise ValueError(f"Queue is full. Maximum {MAX_QUEUE_DEPTH} pending jobs allowed.")
        
        self.redis.rpush(QUEUE_KEY, str(job_id))
        position = self.redis.llen(QUEUE_KEY)
        logger.info(f"Job {job_id} enqueued at position {position}")
        return position
    
    async def dequeue(self, timeout: int = 0) -> Optional[int]:
        """
        Get next job from queue (blocking).
        
        Args:
            timeout: Timeout in seconds (0 = block forever)
            
        Returns:
            Job ID or None if timeout
        """
        result = self.redis.blpop(QUEUE_KEY, timeout=timeout)
        if result:
            job_id = int(result[1])
            # Mark as processing
            self.redis.set(PROCESSING_KEY, str(job_id))
            logger.info(f"Job {job_id} dequeued for processing")
            return job_id
        return None
    
    async def dequeue_nonblocking(self) -> Optional[int]:
        """
        Get next job from queue (non-blocking).
        
        Returns:
            Job ID or None if queue is empty
        """
        result = self.redis.lpop(QUEUE_KEY)
        if result:
            job_id = int(result)
            self.redis.set(PROCESSING_KEY, str(job_id))
            logger.info(f"Job {job_id} dequeued for processing")
            return job_id
        return None
    
    async def get_position(self, job_id: int) -> int:
        """
        Get queue position for a job.
        
        Args:
            job_id: Job ID to find
            
        Returns:
            Position (1-indexed) or 0 if not in queue
        """
        queue = self.redis.lrange(QUEUE_KEY, 0, -1)
        try:
            return queue.index(str(job_id)) + 1
        except ValueError:
            return 0
    
    async def get_length(self) -> int:
        """Get total queue length."""
        return self.redis.llen(QUEUE_KEY)
    
    async def remove(self, job_id: int) -> bool:
        """
        Remove job from queue (for cancellation).
        
        Args:
            job_id: Job ID to remove
            
        Returns:
            True if removed, False if not found
        """
        removed = self.redis.lrem(QUEUE_KEY, 1, str(job_id))
        if removed > 0:
            logger.info(f"Job {job_id} removed from queue")
            return True
        return False
    
    async def get_processing_job(self) -> Optional[int]:
        """Get the currently processing job ID."""
        result = self.redis.get(PROCESSING_KEY)
        if result:
            return int(result)
        return None
    
    async def clear_processing(self):
        """Clear the processing job marker."""
        self.redis.delete(PROCESSING_KEY)
    
    async def get_all_queued(self) -> List[int]:
        """Get all job IDs in queue."""
        queue = self.redis.lrange(QUEUE_KEY, 0, -1)
        return [int(job_id) for job_id in queue]
    
    async def update_positions(self) -> dict:
        """
        Get current positions for all queued jobs.
        
        Returns:
            Dict mapping job_id to position
        """
        queue = self.redis.lrange(QUEUE_KEY, 0, -1)
        return {int(job_id): idx + 1 for idx, job_id in enumerate(queue)}


# Singleton instance
_job_queue: Optional[JobQueue] = None


def get_job_queue() -> JobQueue:
    """Get the singleton job queue instance."""
    global _job_queue
    if _job_queue is None:
        _job_queue = JobQueue()
    return _job_queue
