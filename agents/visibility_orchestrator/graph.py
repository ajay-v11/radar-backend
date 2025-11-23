"""
LangGraph workflow definition for visibility orchestration.

Simple linear flow:
  Query Generator → AI Model Tester → Scorer Analyzer → Finalize
"""

from typing import Dict, List
from langgraph.graph import StateGraph, END

from agents.visibility_orchestrator.models import VisibilityOrchestrationState
from agents.visibility_orchestrator.nodes import (
    generate_queries_node,
    test_models_node,
    analyze_score_node,
    finalize_node
)

import logging

logger = logging.getLogger(__name__)


# Singleton graph instance
_graph = None


def create_visibility_orchestration_graph():
    """
    Create the LangGraph workflow for visibility orchestration.
    
    Linear workflow:
    START → generate_queries → test_models → analyze_score → finalize → END
    """
    from langgraph.graph import START
    
    workflow = StateGraph(VisibilityOrchestrationState)
    
    # Add nodes
    workflow.add_node("generate_queries", generate_queries_node)
    workflow.add_node("test_models", test_models_node)
    workflow.add_node("analyze_score", analyze_score_node)
    workflow.add_node("finalize", finalize_node)
    
    # Define linear edges
    workflow.add_edge(START, "generate_queries")
    workflow.add_edge("generate_queries", "test_models")
    workflow.add_edge("test_models", "analyze_score")
    workflow.add_edge("analyze_score", "finalize")
    workflow.add_edge("finalize", END)
    
    return workflow.compile()


def get_visibility_orchestration_graph():
    """Get or create the visibility orchestration graph."""
    global _graph
    if _graph is None:
        _graph = create_visibility_orchestration_graph()
    return _graph


def run_visibility_orchestration(
    company_data: Dict,
    num_queries: int = 20,
    models: List[str] = None,
    llm_provider: str = "openai",
    progress_callback = None
):
    """
    Run the complete visibility orchestration workflow.
    
    This orchestrates 3 agents in sequence:
    1. Query Generator (uses dynamic query_categories_template)
    2. AI Model Tester (tests queries across models)
    3. Scorer Analyzer (calculates visibility score)
    
    Args:
        company_data: Company data from Phase 1 (industry detection)
            Required fields:
            - company_url
            - company_name
            - company_description
            - company_summary (optional, falls back to description)
            - industry
            - competitors
            - query_categories_template (dynamic template from industry detector)
        num_queries: Number of queries to generate (default: 20)
        models: List of AI models to test (default: ["chatgpt", "gemini"])
        llm_provider: LLM provider for query generation (default: "openai")
        progress_callback: Optional callback function(step, status, message, data)
        
    Returns:
        Dictionary with complete visibility analysis results:
        {
            "queries": [...],
            "query_categories": {...},
            "model_responses": {...},
            "visibility_score": 85.5,
            "analysis_report": {...},
            "errors": [...]
        }
    """
    if models is None:
        models = ["chatgpt", "gemini"]
    
    graph = get_visibility_orchestration_graph()
    
    # Validate required fields
    required_fields = [
        "company_url", "company_name", "industry", 
        "target_region", "competitors", "query_categories_template"
    ]
    
    for field in required_fields:
        if field not in company_data:
            raise ValueError(f"Missing required field in company_data: {field}")
    
    # Prepare initial state
    initial_state = {
        "company_url": company_data["company_url"],
        "company_name": company_data["company_name"],
        "company_description": company_data.get("company_description", ""),
        "company_summary": company_data.get("company_summary", company_data.get("company_description", "")),
        "industry": company_data["industry"],
        "target_region": company_data["target_region"],
        "competitors": company_data["competitors"],
        "query_categories_template": company_data["query_categories_template"],
        "num_queries": num_queries,
        "models": models,
        "llm_provider": llm_provider,
        "queries": [],
        "query_categories": {},
        "model_responses": {},
        "visibility_score": 0.0,
        "analysis_report": {},
        "errors": [],
        "completed": False
    }
    
    logger.info(f"🚀 Starting visibility orchestration for {company_data['company_name']}")
    logger.info(f"   Industry: {company_data['industry']}")
    logger.info(f"   Queries: {num_queries}")
    logger.info(f"   Models: {', '.join(models)}")
    logger.info(f"   Query Categories: {len(company_data['query_categories_template'])} categories")
    
    # Execute graph with streaming
    for step_output in graph.stream(initial_state):
        node_name = list(step_output.keys())[0]
        state = step_output[node_name]
        
        # Progress callbacks
        if progress_callback:
            if node_name == "generate_queries":
                num_generated = len(state.get("queries", []))
                progress_callback(
                    "queries", 
                    "completed" if num_generated > 0 else "in_progress",
                    f"Generated {num_generated} queries",
                    {"queries": num_generated}
                )
            elif node_name == "test_models":
                total_responses = sum(len(r) for r in state.get("model_responses", {}).values())
                progress_callback(
                    "testing",
                    "completed" if total_responses > 0 else "in_progress",
                    f"Tested {total_responses} responses",
                    {"responses": total_responses}
                )
            elif node_name == "analyze_score":
                score = state.get("visibility_score", 0)
                progress_callback(
                    "scoring",
                    "completed",
                    f"Visibility score: {score}%",
                    {"score": score}
                )
            elif node_name == "finalize":
                progress_callback(
                    "complete",
                    "success",
                    "Visibility analysis complete",
                    None
                )
    
    # Get final result
    result = state
    
    logger.info(f"✅ Orchestration complete: {result['visibility_score']}% visibility")
    
    return {
        "queries": result.get("queries", []),
        "query_categories": result.get("query_categories", {}),
        "model_responses": result.get("model_responses", {}),
        "visibility_score": result.get("visibility_score", 0.0),
        "analysis_report": result.get("analysis_report", {}),
        "errors": result.get("errors", [])
    }
