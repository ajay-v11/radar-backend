"""
LangGraph workflow definition for visibility orchestration.

Category-based batching workflow:
  For each category: generate → test → analyze → aggregate → (loop or finalize)
"""

from typing import Dict, List
from langgraph.graph import StateGraph, END

from agents.visibility_orchestrator.models import VisibilityOrchestrationState
from agents.visibility_orchestrator.nodes import (
    initialize_categories,
    select_next_category,
    generate_category_queries,
    test_category_models,
    analyze_category_results,
    aggregate_category_results,
    finalize_results
)

import logging

logger = logging.getLogger(__name__)


# Singleton graph instance
_graph = None


def should_continue_processing(state: VisibilityOrchestrationState) -> str:
    """
    Conditional edge: Determine if we should process another category or finalize.
    """
    categories_to_process = state.get("categories_to_process", [])
    
    if categories_to_process:
        return "continue"  # Loop back to select_next_category
    else:
        return "finalize"  # All categories processed, finalize results


def create_visibility_orchestration_graph():
    """
    Create the LangGraph workflow for category-based visibility orchestration.
    
    Workflow:
    START → initialize_categories → select_next_category → generate_category_queries 
         → test_category_models → analyze_category_results → aggregate_category_results
         → [conditional: more categories?]
              YES → loop back to select_next_category
              NO → finalize_results → END
    """
    from langgraph.graph import START
    
    workflow = StateGraph(VisibilityOrchestrationState)
    
    # Add nodes
    workflow.add_node("initialize_categories", initialize_categories)
    workflow.add_node("select_next_category", select_next_category)
    workflow.add_node("generate_category_queries", generate_category_queries)
    workflow.add_node("test_category_models", test_category_models)
    workflow.add_node("analyze_category_results", analyze_category_results)
    workflow.add_node("aggregate_category_results", aggregate_category_results)
    workflow.add_node("finalize_results", finalize_results)
    
    # Define edges
    workflow.add_edge(START, "initialize_categories")
    workflow.add_edge("initialize_categories", "select_next_category")
    workflow.add_edge("select_next_category", "generate_category_queries")
    workflow.add_edge("generate_category_queries", "test_category_models")
    workflow.add_edge("test_category_models", "analyze_category_results")
    workflow.add_edge("analyze_category_results", "aggregate_category_results")
    
    # Conditional edge: Loop or finalize
    workflow.add_conditional_edges(
        "aggregate_category_results",
        should_continue_processing,
        {
            "continue": "select_next_category",  # Process next category
            "finalize": "finalize_results"  # All done
        }
    )
    
    workflow.add_edge("finalize_results", END)
    
    # Compile with higher recursion limit for category looping
    return workflow.compile(checkpointer=None, debug=False)


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
    Run the category-based visibility orchestration workflow.
    
    This processes categories one at a time with progressive results:
    For each category:
    1. Generate queries for this category
    2. Test queries across all models (parallel)
    3. Analyze results for this category
    4. Aggregate into running totals
    5. Stream progress to user
    
    Args:
        company_data: Company data from Phase 1 (industry detection)
            Required fields:
            - company_url
            - company_name
            - company_description
            - company_summary (optional, falls back to description)
            - industry
            - target_region
            - competitors
            - query_categories_template (dynamic template from industry detector)
        num_queries: Total number of queries to generate (distributed across categories)
        models: List of AI models to test (default: ["llama", "gemini"])
        llm_provider: LLM provider for query generation (default: "claude")
        progress_callback: Optional callback function(step, status, message, data)
            Called after each category completes with partial results
        
    Returns:
        Dictionary with complete visibility analysis results:
        {
            "queries": [...],  # All queries combined
            "query_categories": {...},  # Queries organized by category
            "model_responses": {...},  # All responses combined
            "visibility_score": 85.5,  # Final score
            "analysis_report": {
                "category_breakdown": [...],  # Per-category results
                "by_category": {...},
                "by_model": {...}
            },
            "errors": [...]
        }
    """
    if models is None:
        models = ["llama", "gemini"]
    
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
        "errors": [],
        "completed": False
    }
    
    logger.info(f"🚀 Starting category-based visibility orchestration for {company_data['company_name']}")
    logger.info(f"   Industry: {company_data['industry']}")
    logger.info(f"   Total Queries: {num_queries}")
    logger.info(f"   Models: {', '.join(models)}")
    
    num_categories = len(company_data['query_categories_template'].get('categories', []))
    logger.info(f"   Categories: {num_categories}")
    
    # Execute graph with streaming (increase recursion limit for category looping)
    config = {"recursion_limit": 100}  # Allow up to 100 steps (plenty for category processing)
    for step_output in graph.stream(initial_state, config=config):
        node_name = list(step_output.keys())[0]
        state = step_output[node_name]
        
        # Progress callbacks for category-based workflow
        if progress_callback:
            current_category = state.get("current_category")
            completed_categories = state.get("completed_categories", [])
            total_categories = len(state.get("category_distribution", {}))
            
            if node_name == "initialize_categories":
                progress_callback(
                    "initialization",
                    "completed",
                    f"Initialized {total_categories} categories",
                    {
                        "total_categories": total_categories,
                        "categories": list(state.get("category_distribution", {}).keys())
                    }
                )
            
            elif node_name == "generate_category_queries":
                num_queries_generated = len(state.get("current_queries", []))
                progress_callback(
                    "category_queries",
                    "in_progress",
                    f"Category '{current_category}': Generated {num_queries_generated} queries",
                    {
                        "category": current_category,
                        "queries_generated": num_queries_generated,
                        "progress": f"{len(completed_categories)}/{total_categories}"
                    }
                )
            
            elif node_name == "test_category_models":
                num_responses = sum(len(r) for r in state.get("current_responses", {}).values())
                progress_callback(
                    "category_testing",
                    "in_progress",
                    f"Category '{current_category}': Tested {num_responses} responses",
                    {
                        "category": current_category,
                        "responses_tested": num_responses,
                        "progress": f"{len(completed_categories)}/{total_categories}"
                    }
                )
            
            elif node_name == "analyze_category_results":
                category_score = state.get("current_score", 0)
                category_mentions = state.get("current_mentions", 0)
                progress_callback(
                    "category_analysis",
                    "in_progress",
                    f"Category '{current_category}': {category_score:.1f}% visibility ({category_mentions} mentions)",
                    {
                        "category": current_category,
                        "category_score": category_score,
                        "category_mentions": category_mentions,
                        "progress": f"{len(completed_categories)}/{total_categories}"
                    }
                )
            
            elif node_name == "aggregate_category_results":
                # This is the key streaming point - category completed!
                from agents.visibility_orchestrator.nodes import get_exact_model_name
                
                partial_score = state.get("partial_visibility_score", 0)
                total_queries = state.get("total_queries", 0)
                total_mentions = state.get("total_mentions", 0)
                
                # Get per-model breakdown for current category
                current_model_scores = state.get("current_model_scores", {})
                model_breakdown = {}
                for model_key, model_data in current_model_scores.items():
                    exact_name = get_exact_model_name(model_key)
                    model_breakdown[exact_name] = {
                        "visibility": model_data.get("score", 0),
                        "mentions": model_data.get("mentions", 0),
                        "queries": len(state.get("current_queries", []))
                    }
                
                # Get running per-model scores
                partial_model_scores = state.get("partial_model_scores", {})
                partial_model_scores_exact = {}
                for model_key, score in partial_model_scores.items():
                    exact_name = get_exact_model_name(model_key)
                    partial_model_scores_exact[exact_name] = score
                
                progress_callback(
                    "category_complete",
                    "completed",
                    f"Category '{current_category}' complete! Partial score: {partial_score:.1f}%",
                    {
                        "category": current_category,
                        "category_score": state.get("category_scores", {}).get(current_category, 0),
                        "model_breakdown": model_breakdown,
                        "completed_categories": len(completed_categories),
                        "total_categories": total_categories,
                        "progress": f"{len(completed_categories)}/{total_categories}",
                        "partial_visibility_score": partial_score,
                        "partial_model_scores": partial_model_scores_exact,
                        "total_queries": total_queries,
                        "total_mentions": total_mentions,
                        "category_breakdown": [
                            {
                                "category": cat,
                                "score": state.get("category_scores", {}).get(cat, 0),
                                "queries": len(state.get("category_queries", {}).get(cat, [])),
                                "mentions": state.get("category_mentions", {}).get(cat, 0)
                            }
                            for cat in completed_categories
                        ]
                    }
                )
            
            elif node_name == "finalize_results":
                from agents.visibility_orchestrator.nodes import get_exact_model_name
                
                final_score = state.get("visibility_score", 0)
                analysis_report = state.get("analysis_report", {})
                
                # Get final per-model scores with exact names
                by_model = analysis_report.get("by_model", {})
                model_scores = {}
                for model_key, model_data in by_model.items():
                    exact_name = get_exact_model_name(model_key)
                    mentions = model_data.get("mentions", 0)
                    total = model_data.get("total_responses", 0)
                    score = (mentions / total * 100) if total > 0 else 0.0
                    model_scores[exact_name] = round(score, 2)
                
                # Build model-category matrix with exact names
                model_category_matrix = {}
                for cat_key, cat_data in analysis_report.get("by_category", {}).items():
                    by_model_cat = cat_data.get("by_model", {})
                    for model_key, model_cat_data in by_model_cat.items():
                        exact_name = get_exact_model_name(model_key)
                        if exact_name not in model_category_matrix:
                            model_category_matrix[exact_name] = {}
                        
                        mentions = model_cat_data.get("mentions", 0)
                        total = model_cat_data.get("total", 0)
                        score = (mentions / total * 100) if total > 0 else 0.0
                        model_category_matrix[exact_name][cat_key] = round(score, 2)
                
                progress_callback(
                    "complete",
                    "success",
                    f"Visibility analysis complete! Final score: {final_score:.1f}%",
                    {
                        "visibility_score": final_score,
                        "model_scores": model_scores,
                        "total_queries": state.get("total_queries", 0),
                        "total_mentions": state.get("total_mentions", 0),
                        "categories_processed": len(completed_categories),
                        "model_category_matrix": model_category_matrix
                    }
                )
    
    # Get final result
    result = state
    
    logger.info(f"✅ Category-based orchestration complete: {result['visibility_score']:.1f}% visibility")
    logger.info(f"✅ Processed {len(result.get('completed_categories', []))} categories")
    
    return {
        "queries": result.get("queries", []),
        "query_categories": result.get("query_categories", {}),
        "model_responses": result.get("model_responses", {}),
        "visibility_score": result.get("visibility_score", 0.0),
        "analysis_report": result.get("analysis_report", {}),
        "errors": result.get("errors", [])
    }
