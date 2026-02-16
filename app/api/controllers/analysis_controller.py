"""
Analysis Controller

Handles business logic for complete visibility flow.
"""

import json
import logging
import hashlib
from typing import Optional, List

from app.services.agents.visibility_orchestrator import run_visibility_orchestration

logger = logging.getLogger(__name__)


# ============================================================================
# Cache Management
# ============================================================================

def _get_complete_flow_cache_key(
    company_url: str,
    num_queries: int,
    models: List[str]
) -> str:
    """Generate cache key for complete flow results."""
    normalized_url = company_url.rstrip('/')
    models_str = ','.join(sorted(models))
    
    key = f"{normalized_url}:{num_queries}:{models_str}"
    cache_key = f"complete_flow:{hashlib.sha256(key.encode()).hexdigest()}"
    return cache_key


def get_cached_complete_flow(
    company_url: str,
    num_queries: int,
    models: List[str]
) -> Optional[dict]:
    """Get cached complete flow results if available."""
    try:
        from app.core.config.database import get_redis_client
        redis_client = get_redis_client()
        
        cache_key = _get_complete_flow_cache_key(
            company_url,
            num_queries,
            models
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
    ttl: int = 86400
) -> None:
    """Cache complete flow results (24 hour TTL by default)."""
    try:
        from app.core.config.database import get_redis_client
        redis_client = get_redis_client()
        
        cache_key = _get_complete_flow_cache_key(
            company_url,
            num_queries,
            models
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
    progress_callback = None
) -> dict:
    """
    Execute visibility analysis workflow using LangGraph orchestrator.
    
    Prerequisites: Company data from Phase 1 must be provided.
    
    Steps (orchestrated by LangGraph):
    1. Query generation (using dynamic query_categories_template)
    2. AI model testing (parallel batches)
    3. Scoring and analysis
    
    Args:
        company_data: Company data from Phase 1 (/analyze/company)
            Required fields: company_name, company_description, industry, 
                           competitors, query_categories_template, target_region
        company_url: Company URL
        num_queries: Number of queries to generate
        models: List of AI models to test
        llm_provider: LLM provider for query generation
        progress_callback: Optional callback for progress updates
    
    Returns:
        Complete analysis results with visibility score and detailed report
    
    Raises:
        ValueError: If required fields are missing from company_data
        Exception: For other errors during analysis (with user-friendly messages)
    """
    logger.info(f"Starting visibility analysis for {company_data.get('company_name')}")
    
    try:
        # Validate required fields from Phase 1
        required_fields = ["company_name", "industry", "competitors", "query_categories_template"]
        missing_fields = [f for f in required_fields if f not in company_data]
        if missing_fields:
            raise ValueError(f"Missing required fields from Phase 1: {', '.join(missing_fields)}")
        
        # Prepare company data for orchestrator
        orchestrator_input = {
            "company_url": company_url,
            "company_name": company_data["company_name"],
            "company_description": company_data.get("company_description", ""),
            "company_summary": company_data.get("company_summary", company_data.get("company_description", "")),
            "industry": company_data["industry"],
            "target_region": company_data.get("target_region", "United States"),  # Default to US if not provided
            "competitors": company_data["competitors"],
            "query_categories_template": company_data["query_categories_template"]
        }
        
        # Run the new LangGraph orchestrator with progress callback
        try:
            result = run_visibility_orchestration(
                company_data=orchestrator_input,
                num_queries=num_queries,
                models=models,
                llm_provider=llm_provider,
                progress_callback=progress_callback
            )
        except Exception as e:
            logger.error(f"Error in visibility orchestration: {str(e)}", exc_info=True)
            
            # Provide user-friendly error messages based on error type
            error_str = str(e).lower()
            if "api" in error_str or "rate limit" in error_str:
                raise Exception("AI service temporarily unavailable. Please try again in a few moments.")
            elif "timeout" in error_str:
                raise Exception("Request timed out. Please try with fewer queries or different models.")
            elif "connection" in error_str:
                raise Exception("Connection error. Please check your network and try again.")
            elif "quota" in error_str or "credit" in error_str:
                raise Exception("API quota exceeded. Please check your API keys or try again later.")
            else:
                raise Exception("Visibility analysis failed. Please try again.")
        
        # Validate result
        if not result:
            logger.error("No result returned from visibility orchestration")
            raise Exception("Analysis failed. No data returned. Please try again.")
        
        # Format result to match expected structure
        analysis_report = result.get("analysis_report", {})
        
        final_result = {
            "industry": company_data["industry"],
            "company_name": company_data["company_name"],
            "competitors": company_data["competitors"],
            "total_queries": len(result.get("queries", [])),
            "total_responses": sum(len(r) for r in result.get("model_responses", {}).values()),
            "visibility_score": result.get("visibility_score", 0),
            "analysis_report": analysis_report,
            "queries": result.get("queries", []),
            "query_categories": result.get("query_categories", {}),
            "model_responses": result.get("model_responses", {}),
            "errors": result.get("errors", [])
        }
        
        logger.info(f"✅ Visibility analysis complete: {final_result['visibility_score']:.1f}% visibility")
        
        return final_result
        
    except ValueError:
        # Re-raise validation errors as-is
        raise
    except Exception as e:
        # Log the full error but raise with user-friendly message
        logger.error(f"Visibility analysis failed for {company_data.get('company_name')}: {str(e)}", exc_info=True)
        # If it's already a user-friendly message, re-raise it
        if any(phrase in str(e) for phrase in ["temporarily unavailable", "timed out", "Connection error", "quota exceeded"]):
            raise
        # Otherwise, provide generic message
        raise Exception("Visibility analysis failed. Please try again.")

