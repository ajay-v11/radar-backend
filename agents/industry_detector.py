"""
Industry Detector Agent - Entry Point

Thin wrapper that provides the main entry point for industry detection.
All logic is in the industry_detection_agent/ folder.
"""

import logging
from typing import Dict
from models.schemas import WorkflowState

logger = logging.getLogger(__name__)


def detect_industry(state: WorkflowState, llm_provider: str = "openai") -> WorkflowState:
    """
    Enhanced industry detection using LangGraph workflow.
    
    Entry point that delegates to the modular LangGraph agent.
    
    Args:
        state: WorkflowState containing company_url and optionally company_name
        llm_provider: LLM provider to use ("openai", "gemini", "llama", "claude")
        
    Returns:
        Updated WorkflowState with all extracted information
    """
    from agents.industry_detection_agent.utils import (
        get_cached_industry_analysis,
        cache_industry_analysis,
        store_company_data,
        scrape_website,
        fallback_keyword_detection,
        MAX_FALLBACK_CONTENT_LENGTH
    )
    from agents.industry_detection_agent import run_industry_detection_workflow
    
    company_url = state.get("company_url", "")
    errors = state.get("errors", [])
    
    if not company_url:
        errors.append("No company URL provided")
        state["errors"] = errors
        state["industry"] = "other"
        return state
    
    # Check cache first (includes LLM provider and competitors in key)
    competitor_urls = state.get("competitor_urls", {})
    cached_analysis = get_cached_industry_analysis(company_url, llm_provider, competitor_urls)
    if cached_analysis:
        logger.info(f"Cache HIT for industry analysis: {company_url}")
        state.update(cached_analysis)
        return state
    
    # Delegate to LangGraph workflow
    logger.info("🚀 Starting LangGraph industry detection workflow...")
    
    try:
        result = run_industry_detection_workflow(
            company_url=company_url,
            company_name=state.get("company_name", ""),
            company_description=state.get("company_description", ""),
            competitor_urls=competitor_urls,
            llm_provider=llm_provider
        )
        
        # Update state with results
        state.update(result)
        
        # Store in vector database
        if state.get("scraped_content"):
            storage_errors = store_company_data(state, state["scraped_content"])
            if storage_errors:
                state["errors"].extend(storage_errors)
        
        # Cache the results
        cache_industry_analysis(company_url, llm_provider, competitor_urls, state)
        
        logger.info("✅ LangGraph workflow completed successfully")
        
    except Exception as e:
        error_msg = f"LangGraph workflow failed: {str(e)}"
        logger.error(error_msg)
        errors.append(error_msg)
        
        # Fallback
        scraped_content = scrape_website(company_url, errors)
        state["scraped_content"] = scraped_content
        state["industry"] = fallback_keyword_detection(
            state.get("company_name", ""),
            scraped_content[:MAX_FALLBACK_CONTENT_LENGTH]
        )
        state["competitors"] = []
        state["errors"] = errors
    
    return state
