"""
LangGraph workflow definition for scorer analysis.
"""

from typing import Dict, List
from langgraph.graph import StateGraph, END

from agents.scorer_analyzer_agent.models import ScorerAnalyzerState
from agents.scorer_analyzer_agent.nodes import (
    initialize_analysis,
    analyze_responses,
    calculate_score,
    finalize
)


# Singleton graph instance
_graph = None


def create_scorer_analyzer_graph():
    """Create the LangGraph workflow for scorer analysis."""
    from langgraph.graph import START
    
    workflow = StateGraph(ScorerAnalyzerState)
    
    # Add nodes
    workflow.add_node("initialize", initialize_analysis)
    workflow.add_node("analyze", analyze_responses)
    workflow.add_node("calculate", calculate_score)
    workflow.add_node("finalize", finalize)
    
    # Define edges (workflow)
    workflow.add_edge(START, "initialize")
    workflow.add_edge("initialize", "analyze")
    workflow.add_edge("analyze", "calculate")
    workflow.add_edge("calculate", "finalize")
    workflow.add_edge("finalize", END)
    
    return workflow.compile()


def get_scorer_analyzer_graph():
    """Get or create the scorer analyzer graph."""
    global _graph
    if _graph is None:
        _graph = create_scorer_analyzer_graph()
    return _graph


def run_scorer_analysis_workflow(
    company_name: str,
    queries: List[str],
    model_responses: Dict[str, List[str]],
    query_categories: Dict[str, Dict],
    competitors: List[str],
    progress_callback = None
):
    """
    Run the scorer analysis workflow with optional progress streaming.
    
    Entry point for the scorer analyzer agent.
    
    Args:
        company_name: Company name to analyze
        queries: List of queries tested
        model_responses: Dict of model responses
        query_categories: Dict of query categories
        competitors: List of competitor names
        progress_callback: Optional callback function(step, status, message, data) for progress updates
        
    Returns:
        Dictionary with visibility_score and analysis_report
    """
    graph = get_scorer_analyzer_graph()
    
    # Prepare initial state
    initial_state = {
        "company_name": company_name,
        "queries": queries,
        "model_responses": model_responses,
        "query_categories": query_categories,
        "competitors": competitors,
        "query_to_category": {},
        "category_stats": {},
        "competitor_stats": {},
        "query_log": [],
        "total_mentions": 0,
        "total_responses": 0,
        "sample_mentions": [],
        "visibility_score": 0.0,
        "analysis_report": {},
        "errors": [],
        "completed": False
    }
    
    # Execute graph with streaming
    for step_output in graph.stream(initial_state):
        node_name = list(step_output.keys())[0]
        state = step_output[node_name]
        
        # Progress callbacks
        if progress_callback:
            if node_name == "initialize":
                progress_callback("scoring", "in_progress", "Initializing analysis...", None)
            elif node_name == "analyze":
                progress_callback("scoring", "in_progress", "Analyzing responses for mentions...", None)
            elif node_name == "calculate":
                score = state.get("visibility_score", 0)
                progress_callback("scoring", "in_progress", f"Calculating score: {score}%", None)
            elif node_name == "finalize":
                progress_callback("scoring", "completed", "Scoring complete", None)
    
    # Get final result
    result = state
    
    return {
        "visibility_score": result.get("visibility_score", 0.0),
        "analysis_report": result.get("analysis_report", {}),
        "errors": result.get("errors", [])
    }
