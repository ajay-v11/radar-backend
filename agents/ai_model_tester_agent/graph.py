"""
LangGraph workflow definition for AI model testing.
"""

from typing import List
from langgraph.graph import StateGraph, END

from agents.ai_model_tester_agent.models import AIModelTesterState
from agents.ai_model_tester_agent.nodes import (
    initialize_responses,
    test_queries_batch,
    finalize
)


# Singleton graph instance
_graph = None


def create_ai_model_tester_graph():
    """Create the LangGraph workflow for AI model testing."""
    from langgraph.graph import START
    
    workflow = StateGraph(AIModelTesterState)
    
    # Add nodes
    workflow.add_node("initialize", initialize_responses)
    workflow.add_node("test_queries", test_queries_batch)
    workflow.add_node("finalize", finalize)
    
    # Define edges (workflow)
    workflow.add_edge(START, "initialize")
    workflow.add_edge("initialize", "test_queries")
    workflow.add_edge("test_queries", "finalize")
    workflow.add_edge("finalize", END)
    
    return workflow.compile()


def get_ai_model_tester_graph():
    """Get or create the AI model tester graph."""
    global _graph
    if _graph is None:
        _graph = create_ai_model_tester_graph()
    return _graph


def run_ai_model_testing_workflow(
    queries: List[str],
    models: List[str],
    target_region: str = "Global",
    progress_callback = None
):
    """
    Run the AI model testing workflow with optional progress streaming.
    
    Entry point for the AI model tester agent.
    
    Args:
        queries: List of queries to test
        models: List of model names to test against
        target_region: Target region for context (e.g., "India", "United States", "Global")
        progress_callback: Optional callback function(step, status, message, data) for progress updates
        
    Returns:
        Dictionary with model_responses and errors
    """
    graph = get_ai_model_tester_graph()
    
    # Prepare initial state
    initial_state = {
        "queries": queries,
        "models": models,
        "target_region": target_region,
        "current_query_index": 0,
        "model_responses": {},
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
                progress_callback("testing", "in_progress", f"Initializing tests for {len(models)} models...", None)
            elif node_name == "test_queries":
                total_responses = sum(len(r) for r in state.get("model_responses", {}).values())
                expected = len(queries) * len(models)
                progress_callback("testing", "in_progress", f"Testing queries ({total_responses}/{expected} responses)", None)
            elif node_name == "finalize":
                progress_callback("testing", "completed", "Model testing complete", None)
    
    # Get final result
    result = state
    
    return {
        "model_responses": result.get("model_responses", {}),
        "errors": result.get("errors", [])
    }
