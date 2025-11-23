"""
Industry Detection Controller

Handles business logic for company analysis and industry detection.
"""
import hashlib
from typing import Optional, Dict, AsyncGenerator
import asyncio
import json
from openai import OpenAI
from config.settings import settings
import logging
from agents.industry_detection_agent.utils import get_cached_industry_analysis
from agents.industry_detection_agent import run_industry_detection_workflow


async def analyze_company_stream(
    company_url: str,
    company_name: Optional[str] = None,
    target_region: str = "India"
) -> AsyncGenerator[str, None]:
    """
    Stream company analysis with step-by-step updates using the new modular agent.
    
    Args:
        company_url: Company website URL
        company_name: Optional company name
        target_region: Target region for AI model context (default: "United States")
        
    Yields:
        JSON string events with step, status, message, and optional data
    """
   
    logger = logging.getLogger(__name__)
    
    try:
        # Step 1: Initialize
        yield json.dumps({
            "step": "initialize",
            "status": "started",
            "message": f"Starting analysis for {company_url}",
            "data": None
        })
        await asyncio.sleep(0.1)
        
        # Check cache first using the new agent's cache
    
        
        cached_analysis = await asyncio.to_thread(
            get_cached_industry_analysis,
            company_url,
            "claude",  # Default LLM provider
            {}  # No competitor URLs for now
        )
        
        if cached_analysis:
            logger.info(f"⚡ Cache HIT for {company_url}")
            
            # Format response with data/additional structure (including new dynamic fields)
            data = {
                "industry": cached_analysis.get("industry"),
                "broad_category": cached_analysis.get("broad_category"),
                "industry_description": cached_analysis.get("industry_description"),
                "company_name": cached_analysis.get("company_name"),
                "company_description": cached_analysis.get("company_description"),
                "competitors": cached_analysis.get("competitors", []),
                "target_region": cached_analysis.get("target_region", "United States")
            }
            
            additional = {
                "extraction_template": cached_analysis.get("extraction_template", {}),
                "query_categories_template": cached_analysis.get("query_categories_template", {}),
                "product_category": cached_analysis.get("product_category"),
                "market_keywords": cached_analysis.get("market_keywords", []),
                "target_audience": cached_analysis.get("target_audience"),
                "brand_positioning": cached_analysis.get("brand_positioning", {}),
                "buyer_intent_signals": cached_analysis.get("buyer_intent_signals", {}),
                "industry_specific": cached_analysis.get("industry_specific", {}),
                "competitors_data": cached_analysis.get("competitors_data", [])
            }
            
            yield json.dumps({
                "step": "complete",
                "status": "success",
                "message": "Analysis completed (from cache)",
                "data": data,
                "additional": additional,
                "cached": True
            })
            return
        
        # Step 2: Scraping
        yield json.dumps({
            "step": "scraping",
            "status": "in_progress",
            "message": "Scraping website...",
            "data": None
        })
        
        # Step 3: Analyzing
        yield json.dumps({
            "step": "analyzing",
            "status": "in_progress",
            "message": "Analyzing company with AI...",
            "data": None
        })
        
        # Run the new modular industry detection workflow
       
        
        # Create a queue to collect progress events
        progress_events = []
        
        def progress_callback(step, status, message, data):
            """Callback to capture progress events."""
            progress_events.append({
                "step": step,
                "status": status,
                "message": message,
                "data": data
            })
        
        # Run workflow in thread with progress callback
        result = await asyncio.to_thread(
            run_industry_detection_workflow,
            company_url=company_url,
            company_name=company_name or "",
            company_description="",
            competitor_urls={},
            llm_provider="claude",
            target_region=target_region,
            progress_callback=progress_callback
        )
        
        # Yield all collected progress events
        for event in progress_events:
            yield json.dumps(event)
            await asyncio.sleep(0.05)  # Small delay for smooth streaming
        
        logger.info(f"✅ Analysis complete for {company_url}")
        
        # Format response with data/additional structure (including new dynamic fields)
        data = {
            "industry": result.get("industry"),
            "broad_category": result.get("broad_category"),
            "industry_description": result.get("industry_description"),
            "company_name": result.get("company_name"),
            "company_description": result.get("company_description"),
            "competitors": result.get("competitors", []),
            "target_region": result.get("target_region", "United States")
        }
        
        additional = {
            "extraction_template": result.get("extraction_template", {}),
            "query_categories_template": result.get("query_categories_template", {}),
            "product_category": result.get("product_category"),
            "market_keywords": result.get("market_keywords", []),
            "target_audience": result.get("target_audience"),
            "brand_positioning": result.get("brand_positioning", {}),
            "buyer_intent_signals": result.get("buyer_intent_signals", {}),
            "industry_specific": result.get("industry_specific", {}),
            "competitors_data": result.get("competitors_data", [])
        }
        
        yield json.dumps({
            "step": "complete",
            "status": "success",
            "message": "Company analysis completed successfully",
            "data": data,
            "additional": additional,
            "cached": False
        })
        
    except Exception as e:
        yield json.dumps({
            "step": "error",
            "status": "failed",
            "message": f"Unexpected error: {str(e)}",
            "data": None
        })


# Legacy cache functions - kept for backward compatibility with routes
def _get_analysis_cache_key(url: str) -> str:
    """Generate cache key for complete analysis (legacy)."""
 
    normalized_url = url.rstrip('/').lower()
    return f"analysis:{hashlib.md5(normalized_url.encode()).hexdigest()}"


def _get_cached_analysis(url: str, target_region: str = "United States") -> Optional[Dict]:
    """
    Get cached complete analysis (legacy wrapper).
    
    This wraps the new agent's cache for backward compatibility.
    """
    try:
        # Use the new agent's cache
        cached = get_cached_industry_analysis(url, "claude", {})
        
        if cached:
            # Return in the format expected by routes (including new dynamic fields)
            return {
                "industry": cached.get("industry"),
                "broad_category": cached.get("broad_category", "Other"),
                "industry_description": cached.get("industry_description", ""),
                "extraction_template": cached.get("extraction_template", {}),
                "query_categories_template": cached.get("query_categories_template", {}),
                "company_name": cached.get("company_name"),
                "company_description": cached.get("company_description"),
                "company_summary": cached.get("company_summary", cached.get("company_description", "")),
                "competitors": cached.get("competitors", []),
                "product_category": cached.get("product_category", ""),
                "market_keywords": cached.get("market_keywords", []),
                "target_audience": cached.get("target_audience", ""),
                "brand_positioning": cached.get("brand_positioning", {}),
                "buyer_intent_signals": cached.get("buyer_intent_signals", {}),
                "industry_specific": cached.get("industry_specific", {}),
                "competitors_data": cached.get("competitors_data", []),
                "target_region": cached.get("target_region", target_region)
            }
        return None
    except Exception as e:
        print(f"Cache retrieval failed: {e}")
        return None
