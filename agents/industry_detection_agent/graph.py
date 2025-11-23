"""
LangGraph workflow definition for industry detection.
"""

from typing import Dict
from langgraph.graph import StateGraph, END

from agents.industry_detection_agent.models import IndustryDetectorState
from agents.industry_detection_agent.nodes import (
    scrape_company_pages,
    scrape_competitor_pages,
    combine_scraped_content,
    analyze_with_llm,
    enrich_competitors,
    finalize
)


# Singleton graph instance
_graph = None


def create_industry_detector_graph():
    """Create the LangGraph workflow for industry detection."""
    workflow = StateGraph(IndustryDetectorState)
    
    # Add nodes
    workflow.add_node("scrape_company", scrape_company_pages)
    workflow.add_node("scrape_competitors", scrape_competitor_pages)
    workflow.add_node("combine_content", combine_scraped_content)
    workflow.add_node("analyze", analyze_with_llm)
    workflow.add_node("enrich_competitors", enrich_competitors)
    workflow.add_node("finalize", finalize)
    
    # Define edges (workflow)
    workflow.set_entry_point("scrape_company")
    workflow.add_edge("scrape_company", "scrape_competitors")
    workflow.add_edge("scrape_competitors", "combine_content")
    workflow.add_edge("combine_content", "analyze")
    workflow.add_edge("analyze", "enrich_competitors")
    workflow.add_edge("enrich_competitors", "finalize")
    workflow.add_edge("finalize", END)
    
    return workflow.compile()


def get_industry_detector_graph():
    """Get or create the industry detector graph."""
    global _graph
    if _graph is None:
        _graph = create_industry_detector_graph()
    return _graph


def run_industry_detection_workflow(
    company_url: str,
    company_name: str = "",
    company_description: str = "",
    competitor_urls: Dict[str, str] = None,
    llm_provider: str = "openai"
) -> Dict:
    """
    Run the complete industry detection workflow using LangGraph.
    
    Entry point for the industry detection agent.
    
    Args:
        company_url: Company website URL
        company_name: Optional company name
        company_description: Optional company description
        competitor_urls: Optional dict of competitor names to URLs
        llm_provider: LLM provider to use
        
    Returns:
        Dictionary with all extracted information
    """
    graph = get_industry_detector_graph()
    
    # Prepare initial state
    initial_state = {
        "company_url": company_url,
        "company_name": company_name,
        "company_description": company_description,
        "competitor_urls": competitor_urls or {},
        "llm_provider": llm_provider,
        "errors": [],
        "completed": False
    }
    
    # Execute graph
    result = graph.invoke(initial_state)
    
    # Return cleaned result
    return {
        "company_name": result.get("company_name", ""),
        "company_description": result.get("company_description", ""),
        "company_summary": result.get("company_description", ""),  # Use description as summary fallback
        "industry": result.get("industry", "other"),
        "product_category": result.get("product_category", ""),
        "market_keywords": result.get("market_keywords", []),
        "target_audience": result.get("target_audience", ""),
        "brand_positioning": result.get("brand_positioning", {}),
        "buyer_intent_signals": result.get("buyer_intent_signals", {}),
        "industry_specific": result.get("industry_specific", {}),
        "competitors": result.get("competitors", []),
        "competitors_data": result.get("competitors_data", []),
        "scraped_content": result.get("combined_content", ""),
        "errors": result.get("errors", [])
    }
