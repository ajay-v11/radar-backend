"""
Node functions for visibility orchestration workflow.

Each node wraps a sub-agent and manages state transformation.
"""

import logging
from agents.visibility_orchestrator.models import VisibilityOrchestrationState

logger = logging.getLogger(__name__)


def generate_queries_node(state: VisibilityOrchestrationState) -> VisibilityOrchestrationState:
    """
    Node: Generate queries using Query Generator Agent.
    
    Uses the dynamic query_categories_template from industry detector.
    """
    from agents.query_generator_agent import run_query_generation_workflow
    
    logger.info("🎯 Starting Query Generation...")
    
    try:
        result = run_query_generation_workflow(
            company_url=state["company_url"],
            company_name=state["company_name"],
            company_description=state["company_description"],
            company_summary=state["company_summary"],
            industry=state["industry"],
            competitors=state["competitors"],
            query_categories_template=state["query_categories_template"],
            num_queries=state["num_queries"],
            llm_provider=state.get("llm_provider", "openai")
        )
        
        state["queries"] = result.get("queries", [])
        state["query_categories"] = result.get("query_categories", {})
        
        if result.get("errors"):
            state["errors"].extend(result["errors"])
        
        logger.info(f"✓ Generated {len(state['queries'])} queries")
        
    except Exception as e:
        error_msg = f"Query generation failed: {str(e)}"
        logger.error(error_msg)
        state["errors"].append(error_msg)
        state["queries"] = []
        state["query_categories"] = {}
    
    return state


def test_models_node(state: VisibilityOrchestrationState) -> VisibilityOrchestrationState:
    """
    Node: Test queries across AI models using AI Model Tester Agent.
    """
    from agents.ai_model_tester_agent import run_ai_model_testing_workflow
    
    logger.info("🧪 Starting AI Model Testing...")
    
    queries = state.get("queries", [])
    models = state.get("models", ["chatgpt", "gemini"])
    
    if not queries:
        error_msg = "No queries available for testing"
        logger.error(error_msg)
        state["errors"].append(error_msg)
        state["model_responses"] = {}
        return state
    
    try:
        result = run_ai_model_testing_workflow(
            queries=queries,
            models=models,
            target_region=state.get("target_region", "Global")
        )
        
        state["model_responses"] = result.get("model_responses", {})
        
        if result.get("errors"):
            state["errors"].extend(result["errors"])
        
        total_responses = sum(len(r) for r in state["model_responses"].values())
        logger.info(f"✓ Tested {total_responses} responses across {len(models)} models")
        
    except Exception as e:
        error_msg = f"Model testing failed: {str(e)}"
        logger.error(error_msg)
        state["errors"].append(error_msg)
        state["model_responses"] = {}
    
    return state


def analyze_score_node(state: VisibilityOrchestrationState) -> VisibilityOrchestrationState:
    """
    Node: Calculate visibility score using Scorer Analyzer Agent.
    """
    from agents.scorer_analyzer_agent import run_scorer_analysis_workflow
    
    logger.info("📊 Starting Score Analysis...")
    
    queries = state.get("queries", [])
    model_responses = state.get("model_responses", {})
    
    if not queries or not model_responses:
        error_msg = "No queries or responses available for scoring"
        logger.error(error_msg)
        state["errors"].append(error_msg)
        state["visibility_score"] = 0.0
        state["analysis_report"] = {}
        return state
    
    try:
        result = run_scorer_analysis_workflow(
            company_name=state["company_name"],
            queries=queries,
            model_responses=model_responses,
            query_categories=state.get("query_categories", {}),
            competitors=state.get("competitors", [])
        )
        
        state["visibility_score"] = result.get("visibility_score", 0.0)
        state["analysis_report"] = result.get("analysis_report", {})
        
        if result.get("errors"):
            state["errors"].extend(result["errors"])
        
        logger.info(f"✓ Visibility Score: {state['visibility_score']}%")
        
    except Exception as e:
        error_msg = f"Score analysis failed: {str(e)}"
        logger.error(error_msg)
        state["errors"].append(error_msg)
        state["visibility_score"] = 0.0
        state["analysis_report"] = {}
    
    return state


def finalize_node(state: VisibilityOrchestrationState) -> VisibilityOrchestrationState:
    """
    Node: Finalize the workflow.
    """
    logger.info("✅ Visibility orchestration complete")
    state["completed"] = True
    return state
