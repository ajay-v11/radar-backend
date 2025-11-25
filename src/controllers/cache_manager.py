"""
Simple cache manager with slug-based keys.

No complex multi-level caching - just simple slug matching.
"""
import hashlib
import json
import logging
from typing import Optional, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


def generate_analysis_slug(company_url: str, target_region: str = "United States") -> str:
    """
    Generate a simple slug for company analysis.
    
    Format: company_url + target_region + date
    """
    normalized_url = company_url.rstrip('/').lower()
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    # Create slug from url + region + date
    slug_input = f"{normalized_url}:{target_region}:{date_str}"
    slug = hashlib.md5(slug_input.encode()).hexdigest()[:12]
    
    return f"company_{slug}"


def generate_visibility_slug(
    company_url: str,
    num_queries: int,
    models: List[str],
    llm_provider: str
) -> str:
    """
    Generate a simple slug for visibility analysis.
    
    Format: company_url + num_queries + models + llm_provider + date
    """
    normalized_url = company_url.rstrip('/').lower()
    models_str = ','.join(sorted(models))
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    # Create slug from all params + date
    slug_input = f"{normalized_url}:{num_queries}:{models_str}:{llm_provider}:{date_str}"
    slug = hashlib.md5(slug_input.encode()).hexdigest()[:12]
    
    return f"visibility_{slug}"


def get_cached_by_slug(slug: str) -> Optional[Dict]:
    """Get cached data by slug."""
    try:
        from config.database import get_redis_client
        redis_client = get_redis_client()
        
        cached = redis_client.get(slug)
        if cached:
            logger.info(f"Cache HIT: {slug}")
            if isinstance(cached, bytes):
                cached = cached.decode('utf-8')
            return json.loads(cached)
        
        logger.debug(f"Cache MISS: {slug}")
        return None
    except Exception as e:
        logger.warning(f"Cache retrieval failed for {slug}: {e}")
        return None


def cache_by_slug(slug: str, data: Dict, ttl: int = 86400) -> None:
    """Cache data by slug (24 hour TTL by default)."""
    try:
        from config.database import get_redis_client
        redis_client = get_redis_client()
        
        redis_client.setex(slug, ttl, json.dumps(data))
        logger.info(f"Cached data: {slug}")
    except Exception as e:
        logger.warning(f"Cache storage failed for {slug}: {e}")
