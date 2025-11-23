"""
Industry Detector Agent - Legacy Wrapper

This file exists only for backward compatibility with unit tests.
All production code should use agents.industry_detection_agent directly.
"""

import logging
from models.schemas import WorkflowState
from agents.industry_detection_agent import run_industry_detection_workflow


logger = logging.getLogger(__name__)


def detect_industry(state: WorkflowState, llm_provider: str = "openai") -> WorkflowState:
    """
    Legacy wrapper for unit tests.
    
    Delegates to the new modular industry_detection_agent.
    
    Args:
        state: WorkflowState containing company_url and optionally company_name
        llm_provider: LLM provider to use ("openai", "gemini", "llama", "claude")
        
    Returns:
        Updated WorkflowState with all extracted information
    """
    
    
    company_url = state.get("company_url", "")
    
    if not company_url:
        state["errors"] = state.get("errors", []) + ["No company URL provided"]
        state["industry"] = "other"
        return state
    
    try:
        result = run_industry_detection_workflow(
            company_url=company_url,
            company_name=state.get("company_name", ""),
            company_description=state.get("company_description", ""),
            competitor_urls=state.get("competitor_urls", {}),
            llm_provider=llm_provider
        )
        
        # Update state with results
        state.update(result)
        
    except Exception as e:
        logger.error(f"Industry detection failed: {str(e)}")
        state["errors"] = state.get("errors", []) + [f"Workflow failed: {str(e)}"]
        state["industry"] = "other"
    
    return state
