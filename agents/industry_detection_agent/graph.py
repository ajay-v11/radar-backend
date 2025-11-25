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
    classify_industry,
    generate_extraction_template,
    extract_with_template,
    generate_query_categories,
    enrich_competitors,
    finalize
)


# Singleton graph instance
_graph = None


def create_industry_detector_graph():
    """Create the LangGraph workflow for industry detection with dynamic classification and parallel scraping."""
    from langgraph.graph import START
    
    workflow = StateGraph(IndustryDetectorState)
    
    # Add nodes
    workflow.add_node("scrape_company", scrape_company_pages)
    workflow.add_node("scrape_competitors", scrape_competitor_pages)
    workflow.add_node("combine_content", combine_scraped_content)
    workflow.add_node("classify_industry", classify_industry)
    workflow.add_node("generate_template", generate_extraction_template)
    workflow.add_node("extract_data", extract_with_template)
    workflow.add_node("generate_query_categories", generate_query_categories)
    workflow.add_node("enrich_competitors", enrich_competitors)
    workflow.add_node("finalize", finalize)
    
    # Define edges (workflow) - PARALLEL scraping
    # Both scraping nodes start simultaneously
    workflow.add_edge(START, "scrape_company")
    workflow.add_edge(START, "scrape_competitors")
    
    # Both must complete before combining (fan-in)
    workflow.add_edge("scrape_company", "combine_content")
    workflow.add_edge("scrape_competitors", "combine_content")
    
    # Continue sequential flow
    workflow.add_edge("combine_content", "classify_industry")
    workflow.add_edge("classify_industry", "generate_template")
    workflow.add_edge("generate_template", "extract_data")
    workflow.add_edge("extract_data", "generate_query_categories")
    workflow.add_edge("generate_query_categories", "enrich_competitors")
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
    target_region: str,
    company_name: str = "",
    company_description: str = "",
    competitor_urls: Dict[str, str] = None,
    llm_provider: str = "claude",
    progress_callback = None
):
    """
    Run the industry detection workflow with optional progress streaming.
    
    Entry point for the industry detection agent.
    
    Args:
        company_url: Company website URL
        target_region: Target region/market (e.g., "India", "United States", "Global")
        company_name: Optional company name
        company_description: Optional company description
        competitor_urls: Optional dict of competitor names to URLs
        llm_provider: LLM provider to use
        progress_callback: Optional callback function(step, status, message, data) for progress updates
        
    Returns:
        Dictionary with all extracted information including target_region
    """
    graph = get_industry_detector_graph()
    
    # Prepare initial state
    initial_state = {
        "company_url": company_url,
        "target_region": target_region,
        "company_name": company_name,
        "company_description": company_description,
        "competitor_urls": competitor_urls or {},
        "llm_provider": llm_provider,
        "errors": [],
        "completed": False
    }
    
    # Execute graph with streaming
    for step_output in graph.stream(initial_state):
        # step_output is a dict with node name as key
        node_name = list(step_output.keys())[0]
        state = step_output[node_name]
        
        # Map node names to user-friendly progress messages
        if progress_callback:
            if node_name == "scrape_company":
                progress_callback("scraping", "in_progress", "Scraping company website...", None)
            elif node_name == "scrape_competitors":
                num_competitors = len(competitor_urls) if competitor_urls else 0
                if num_competitors > 0:
                    progress_callback("scraping", "in_progress", f"Scraping {num_competitors} competitor homepages...", None)
            elif node_name == "combine_content":
                progress_callback("scraping", "completed", "Website content retrieved", None)
            elif node_name == "classify_industry":
                progress_callback("analyzing", "in_progress", "Classifying industry...", None)
            elif node_name == "generate_template":
                progress_callback("analyzing", "in_progress", "Generating extraction template...", None)
            elif node_name == "extract_data":
                progress_callback("analyzing", "in_progress", "Extracting company data...", None)
            elif node_name == "generate_query_categories":
                progress_callback("analyzing", "in_progress", "Generating query categories...", None)
            elif node_name == "enrich_competitors":
                progress_callback("analyzing", "completed", "Company analysis complete", None)
            elif node_name == "finalize":
                progress_callback("finalizing", "completed", "Finalizing results...", None)
    
    # Get final result
    result = state
    
    # No caching at agent level - using route-level caching only
    
    # Return cleaned result with new dynamic fields
    return {
        "company_name": result.get("company_name", ""),
        "company_description": result.get("company_description", ""),
        "company_summary": result.get("company_description", ""),
        "target_region": result.get("target_region", ""),
        "industry": result.get("industry", "Unknown"),
        "broad_category": result.get("broad_category", "Other"),
        "industry_description": result.get("industry_description", ""),
        "extraction_template": result.get("extraction_template", {}),
        "query_categories_template": result.get("query_categories_template", {}),
        "product_category": result.get("product_category", ""),
        "market_keywords": result.get("market_keywords", []),
        "target_audience": result.get("target_audience", ""),
        "brand_positioning": result.get("brand_positioning", {}),
        "buyer_intent_signals": result.get("buyer_intent_signals", {}),
        "industry_specific": result.get("industry_specific", {}),
        "competitors": result.get("competitors", []),
        "competitors_data": result.get("competitors_data", []),
        "errors": result.get("errors", [])
    }
