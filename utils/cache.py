"""
Redis caching utilities for AI model responses and rate limiting.
"""

import json
import hashlib
from typing import Optional, Any
from datetime import datetime
import logging

from config.database import get_redis_client
from config.settings import settings

logger = logging.getLogger(__name__)


def get_cache_key(prefix: str, *args) -> str:
    """
    Generate a cache key from prefix and arguments.
    
    Args:
        prefix: Key prefix (e.g., 'model', 'job', 'rate_limit')
        *args: Additional arguments to include in key
        
    Returns:
        str: Generated cache key
    """
    key_parts = [prefix] + [str(arg) for arg in args]
    return ":".join(key_parts)


def hash_query(query: str) -> str:
    """
    Generate a hash for a query string.
    
    Args:
        query: Query string to hash
        
    Returns:
        str: MD5 hash of the query
    """
    return hashlib.md5(query.encode()).hexdigest()


def get_cached_model_response(model_name: str, query: str) -> Optional[str]:
    """
    Get cached AI model response for a query.
    
    Args:
        model_name: Name of the AI model
        query: Query string
        
    Returns:
        Cached response string or None if not found
    """
    try:
        redis_client = get_redis_client()
        cache_key = get_cache_key("model", model_name, hash_query(query))
        
        cached = redis_client.get(cache_key)
        if cached:
            logger.debug(f"Cache HIT for {model_name}: {query[:50]}...")
            return cached
        
        logger.debug(f"Cache MISS for {model_name}: {query[:50]}...")
        return None
        
    except Exception as e:
        logger.error(f"Error getting cached response: {e}")
        return None


def cache_model_response(
    model_name: str,
    query: str,
    response: str,
    ttl: Optional[int] = None
) -> bool:
    """
    Cache an AI model response.
    
    Args:
        model_name: Name of the AI model
        query: Query string
        response: Model response to cache
        ttl: Time to live in seconds (default: from settings)
        
    Returns:
        bool: True if cached successfully
    """
    try:
        redis_client = get_redis_client()
        cache_key = get_cache_key("model", model_name, hash_query(query))
        ttl = ttl or settings.REDIS_CACHE_TTL
        
        redis_client.setex(cache_key, ttl, response)
        logger.debug(f"Cached response for {model_name}: {query[:50]}...")
        return True
        
    except Exception as e:
        logger.error(f"Error caching response: {e}")
        return False


def check_rate_limit(
    model_name: str,
    max_calls: int = 60,
    window_seconds: int = 60
) -> bool:
    """
    Check if rate limit allows another API call.
    
    Args:
        model_name: Name of the AI model
        max_calls: Maximum calls allowed in window
        window_seconds: Time window in seconds
        
    Returns:
        bool: True if call is allowed, False if rate limited
    """
    try:
        redis_client = get_redis_client()
        
        # Create time-based key (e.g., rate_limit:chatgpt:202411191430)
        timestamp = datetime.now().strftime("%Y%m%d%H%M")
        rate_key = get_cache_key("rate_limit", model_name, timestamp)
        
        # Increment counter
        current = redis_client.incr(rate_key)
        
        # Set expiry on first increment
        if current == 1:
            redis_client.expire(rate_key, window_seconds)
        
        allowed = current <= max_calls
        
        if not allowed:
            logger.warning(f"Rate limit exceeded for {model_name}: {current}/{max_calls}")
        
        return allowed
        
    except Exception as e:
        logger.error(f"Error checking rate limit: {e}")
        return True  # Allow on error to avoid blocking


def store_job_status(job_id: str, status: str, data: Optional[dict] = None) -> bool:
    """
    Store job status and metadata.
    
    Args:
        job_id: Unique job identifier
        status: Job status (e.g., 'pending', 'running', 'completed', 'failed')
        data: Additional job data to store
        
    Returns:
        bool: True if stored successfully
    """
    try:
        redis_client = get_redis_client()
        job_key = get_cache_key("job", job_id)
        
        job_data = {
            "status": status,
            "updated_at": datetime.now().isoformat(),
            **(data or {})
        }
        
        # Store for 1 hour
        redis_client.setex(job_key, 3600, json.dumps(job_data))
        logger.info(f"Stored job status: {job_id} -> {status}")
        return True
        
    except Exception as e:
        logger.error(f"Error storing job status: {e}")
        return False


def get_job_status(job_id: str) -> Optional[dict]:
    """
    Get job status and metadata.
    
    Args:
        job_id: Unique job identifier
        
    Returns:
        dict: Job data or None if not found
    """
    try:
        redis_client = get_redis_client()
        job_key = get_cache_key("job", job_id)
        
        data = redis_client.get(job_key)
        if data:
            return json.loads(data)
        return None
        
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        return None


def clear_cache(pattern: Optional[str] = None) -> int:
    """
    Clear cached data matching a pattern.
    
    Args:
        pattern: Redis key pattern (e.g., 'model:*', 'job:*')
                 If None, clears all keys
        
    Returns:
        int: Number of keys deleted
    """
    try:
        redis_client = get_redis_client()
        
        if pattern:
            keys = redis_client.keys(pattern)
        else:
            keys = redis_client.keys("*")
        
        if keys:
            deleted = redis_client.delete(*keys)
            logger.info(f"Cleared {deleted} cache keys matching: {pattern or '*'}")
            return deleted
        
        return 0
        
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return 0


def get_cache_stats() -> dict:
    """
    Get cache statistics.
    
    Returns:
        dict: Cache statistics including hit rate, memory usage, etc.
    """
    try:
        redis_client = get_redis_client()
        info = redis_client.info("stats")
        
        return {
            "total_keys": redis_client.dbsize(),
            "hits": info.get("keyspace_hits", 0),
            "misses": info.get("keyspace_misses", 0),
            "hit_rate": (
                info.get("keyspace_hits", 0) / 
                (info.get("keyspace_hits", 0) + info.get("keyspace_misses", 1))
            ) * 100,
            "memory_used": info.get("used_memory_human", "unknown")
        }
        
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return {}
