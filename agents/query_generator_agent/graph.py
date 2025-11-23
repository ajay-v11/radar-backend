"""
LangGraph workflow definition for query generation.
"""

from typing import Dict
from langgraph.graph import StateGraph, END

from agents.query_generator_agent.models import QueryGeneratorState
from agents.query_generator_agent.nodes import (
    check_cache,
    calculate_distribution,
    generate_category_queries,
    cache_results,
    finalize
)


# Singleton graph instance
_graph = None


def should_skip_generation(state: QueryGeneratorState) -> str:
    """Conditional edge: Skip generation if cached."""
    if state.get("completed", False):
        return "finalize"
    return "calculate_distribution"


def create_query_generator_graph():
    """Create the LangGraph workflow for query generation."""
    from langgraph.graph import START
    
    workflow = StateGraph(QueryGeneratorState)
    
    # Add nodes
    workflow.add_node("check_cache", check_cache)
    workflow.add_node("calculate_distribution", calculate_distribution)
    workflow.add_node("generate_queries", generate_category_queries)
    workflow.add_node("cache_results", cache_results)
    workflow.add_node("finalize", finalize)
    
    # Define edges (workflow)
    workflow.add_edge(START, "check_cache")
    
    # Conditional: Skip if cached
    workflow.add_conditional_edges(
        "check_cache",
        should_skip_generation,
        {
            "calculate_distribution": "calculate_distribution",
            "finalize": "finalize"
        }
    )
    
    workflow.add_edge("calculate_distribution", "generate_queries")
    workflow.add_edge("generate_queries", "cache_results")
    workflow.add_edge("cache_results", "finalize")
    workflow.add_edge("finalize", END)
    
    return workflow.compile()


def get_query_generator_graph():
    """Get or create the query generator graph."""
    global _graph
    if _graph is None:
        _graph = create_query_generator_graph()
    return _graph


def run_query_generation_workflow(
    company_url: str,
    company_name: str,
    company_description: str,
    company_summary: str,
    industry: str,
    competitors: list,
    query_categories_template: Dict,
    num_queries: int = 20,
    llm_provider: str = "openai",
    progress_callback = None
):
    """
    Run the query generation workflow with optional progress streaming.
    
    Entry point for the query generator agent.
    
    Args:
        company_url: Company website URL
        company_name: Company name
        company_description: Brief description
        company_summary: Detailed summary
        industry: Industry classification
        competitors: List of competitor names
        query_categories_template: Dynamic query categories from industry detector
        num_queries: Number of queries to generate (20-100)
        llm_provider: LLM provider to use
        progress_callback: Optional callback function(step, status, message, data) for progress updates
        
    Returns:
        Dictionary with queries and query_categories
    """
    graph = get_query_generator_graph()
    
    # Enforce query limits
    MIN_QUERIES = 20
    MAX_QUERIES = 100
    if num_queries < MIN_QUERIES:
        num_queries = MIN_QUERIES
    elif num_queries > MAX_QUERIES:
        num_queries = MAX_QUERIES
    
    # Prepare initial state
    initial_state = {
        "company_url": company_url,
        "company_name": company_name,
        "company_description": company_description,
        "company_summary": company_summary,
        "industry": industry,
        "competitors": competitors,
        "query_categories_template": query_categories_template,
        "num_queries": num_queries,
        "llm_provider": llm_provider,
        "category_distribution": {},
        "queries": [],
        "query_categories": {},
        "errors": [],
        "completed": False
    }
    
    # Execute graph with streaming
    for step_output in graph.stream(initial_state):
        node_name = list(step_output.keys())[0]
        state = step_output[node_name]
        
        # Progress callbacks
        if progress_callback:
            if node_name == "check_cache":
                if state.get("completed"):
                    progress_callback("queries", "completed", "Using cached queries", None)
                else:
                    progress_callback("queries", "in_progress", "Generating queries...", None)
            elif node_name == "calculate_distribution":
                progress_callback("queries", "in_progress", "Calculating query distribution...", None)
            elif node_name == "generate_queries":
                num_generated = len(state.get("queries", []))
                progress_callback("queries", "in_progress", f"Generated {num_generated} queries", None)
            elif node_name == "cache_results":
                progress_callback("queries", "completed", "Queries generated", None)
            elif node_name == "finalize":
                progress_callback("queries", "completed", "Query generation complete", None)
    
    # Get final result
    result = state
    
    return {
        "queries": result.get("queries", []),
        "query_categories": result.get("query_categories", {}),
        "errors": result.get("errors", [])
    }
