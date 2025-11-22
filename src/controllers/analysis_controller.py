"""
Analysis Controller

Handles business logic for complete visibility flow.
"""

import json
import logging
import hashlib
from typing import Optional, Dict, List

from agents.industry_detector import detect_industry
from agents.query_generator import generate_queries
from agents.ai_model_tester import test_ai_models
from agents.scorer_analyzer import analyze_score

logger = logging.getLogger(__name__)


# ============================================================================
# Cache Management
# ============================================================================

def _get_complete_flow_cache_key(
    company_url: str,
    num_queries: int,
    models: List[str],
    query_weights: Optional[dict] = None
) -> str:
    """Generate cache key for complete flow results."""
    normalized_url = company_url.rstrip('/')
    models_str = ','.join(sorted(models))
    weights_str = json.dumps(query_weights, sort_keys=True) if query_weights else ""
    
    key = f"{normalized_url}:{num_queries}:{models_str}:{weights_str}"
    cache_key = f"complete_flow:{hashlib.sha256(key.encode()).hexdigest()}"
    return cache_key


def get_cached_complete_flow(
    company_url: str,
    num_queries: int,
    models: List[str],
    query_weights: Optional[dict] = None
) -> Optional[dict]:
    """Get cached complete flow results if available."""
    try:
        from config.database import get_redis_client
        redis_client = get_redis_client()
        
        cache_key = _get_complete_flow_cache_key(
            company_url,
            num_queries,
            models,
            query_weights
        )
        
        cached = redis_client.get(cache_key)
        if cached:
            logger.info(f"Complete flow cache HIT: {company_url}")
            if isinstance(cached, bytes):
                cached = cached.decode('utf-8')
            return json.loads(cached)
        
        logger.debug(f"Complete flow cache MISS: {company_url}")
        return None
    except Exception as e:
        logger.warning(f"Complete flow cache retrieval failed: {e}")
        return None


def cache_complete_flow(
    company_url: str,
    num_queries: int,
    models: List[str],
    result: dict,
    query_weights: Optional[dict] = None,
    ttl: int = 86400
) -> None:
    """Cache complete flow results (24 hour TTL by default)."""
    try:
        from config.database import get_redis_client
        redis_client = get_redis_client()
        
        cache_key = _get_complete_flow_cache_key(
            company_url,
            num_queries,
            models,
            query_weights
        )
        
        redis_client.setex(cache_key, ttl, json.dumps(result))
        logger.info(f"Cached complete flow results: {company_url}")
    except Exception as e:
        logger.warning(f"Complete flow cache storage failed: {e}")


# ============================================================================
# Visibility Analysis Execution (Phase 2 Only)
# ============================================================================

def execute_visibility_analysis(
    company_data: dict,
    company_url: str,
    num_queries: int,
    models: List[str],
    llm_provider: str,
    batch_size: int,
    query_weights: Optional[dict] = None
) -> dict:
    """
    Execute visibility analysis workflow (Phase 2 only).
    
    Prerequisites: Company data from Phase 1 must be provided.
    
    Steps:
    1. Query generation (using company data from Phase 1)
    2. Parallel batch testing
    3. Final aggregation
    
    Args:
        company_data: Company data from Phase 1 (/analyze/company)
        company_url: Company URL
        num_queries: Number of queries to generate
        models: List of AI models to test
        llm_provider: LLM provider for query generation
        batch_size: Batch size for parallel testing
        query_weights: Optional category weights
    
    Returns:
        Complete analysis results
    """
    # Initialize state with company data from Phase 1
    state = {
        "company_url": company_url,
        "company_name": company_data.get("company_name", ""),
        "company_description": company_data.get("company_description", ""),
        "company_summary": company_data.get("company_summary", ""),
        "industry": company_data.get("industry", "other"),
        "competitors": company_data.get("competitors", []),
        "competitors_data": company_data.get("competitors_data", []),
        "errors": []
    }
    
    logger.info(f"Starting visibility analysis for {company_data.get('company_name')}")
    
    # Step 1: Query Generation
    logger.info(f"Step 1: Generating {num_queries} queries")
    state["num_queries"] = num_queries
    state = generate_queries(state, num_queries=num_queries, llm_provider=llm_provider)
    
    queries = state.get("queries", [])
    
    # Step 2: Parallel Batch Testing + Analysis
    logger.info(f"Step 2: Testing {len(queries)} queries across {len(models)} models")
    all_batch_responses = {model: [] for model in models}
    all_analysis_results = []
    
    for batch_num, i in enumerate(range(0, len(queries), batch_size), 1):
        batch_queries = queries[i:i+batch_size]
        
        # Test batch
        batch_state = {
            "queries": batch_queries,
            "models": models,
            "model_responses": {},
            "errors": []
        }
        
        batch_state = test_ai_models(batch_state)
        batch_responses = batch_state.get("model_responses", {})
        
        # Store responses
        for model in models:
            if model in batch_responses:
                all_batch_responses[model].extend(batch_responses[model])
        
        # Analyze batch
        analysis_state = {
            "company_name": state.get("company_name"),
            "competitors": state.get("competitors", []),
            "queries": batch_queries,
            "model_responses": batch_responses,
            "errors": []
        }
        
        analysis_state = analyze_score(analysis_state)
        
        batch_analysis = {
            "batch_num": batch_num,
            "visibility_score": analysis_state.get("visibility_score", 0),
            "total_mentions": analysis_state.get("analysis_report", {}).get("total_mentions", 0),
            "by_model": analysis_state.get("analysis_report", {}).get("by_model", {}),
        }
        
        all_analysis_results.append(batch_analysis)
        logger.info(f"Batch {batch_num}: score={batch_analysis['visibility_score']:.1f}%")
    
    # Step 3: Final Aggregation
    logger.info("Step 3: Aggregating results")
    final_state = {
        "company_name": state.get("company_name"),
        "competitors": state.get("competitors", []),
        "queries": queries,
        "model_responses": all_batch_responses,
        "errors": []
    }
    
    final_state = analyze_score(final_state)
    final_report = final_state.get("analysis_report", {})
    
    # Build final result
    final_result = {
        "industry": state.get("industry"),
        "company_name": state.get("company_name"),
        "competitors": state.get("competitors", []),
        "total_queries": len(queries),
        "total_responses": sum(len(r) for r in all_batch_responses.values()),
        "visibility_score": final_state.get("visibility_score", 0),
        "analysis_report": final_report,
        "batch_results": all_analysis_results
    }
    
    return final_result
