"""
LangGraph Orchestrator

This module defines and executes the sequential workflow that connects all agents
in the AI Visibility Scoring System. It uses LangGraph's StateGraph to manage
state transitions between agents.
"""

from typing import Dict, Any
from langgraph.graph import StateGraph, END
from models.schemas import WorkflowState
from agents.industry_detector import detect_industry
from agents.query_generator import generate_queries
from agents.ai_model_tester import test_ai_models
from agents.scorer_analyzer import analyze_score


def create_workflow_graph() -> StateGraph:
    """
    Build the LangGraph StateGraph for the analysis workflow.
    
    Creates a sequential workflow with four agents:
    1. Industry Detector - Classifies company industry
    2. Query Generator - Creates industry-specific queries
    3. AI Model Tester - Executes queries against AI models
    4. Scorer Analyzer - Calculates visibility score
    
    Returns:
        Compiled StateGraph ready for execution
        
    Requirements:
        - 2.1: Execute Industry Detector Agent as first step
        - 2.2: Pass industry classification to Query Generator
        - 2.3: Pass generated queries to AI Model Tester
        - 2.4: Pass test results to Scorer Analyzer
        - 2.5: Maintain state data throughout workflow
    """
    # Initialize the StateGraph with WorkflowState schema
    workflow = StateGraph(WorkflowState)
    
    # Add nodes for each agent
    workflow.add_node("industry_detector", detect_industry)
    workflow.add_node("query_generator", generate_queries)
    workflow.add_node("ai_model_tester", test_ai_models)
    workflow.add_node("scorer_analyzer", analyze_score)
    
    # Connect nodes in sequential order
    # Set industry_detector as entry point
    workflow.set_entry_point("industry_detector")
    
    # Define edges connecting the workflow
    workflow.add_edge("industry_detector", "query_generator")
    workflow.add_edge("query_generator", "ai_model_tester")
    workflow.add_edge("ai_model_tester", "scorer_analyzer")
    
    # Set scorer_analyzer as finish point
    workflow.add_edge("scorer_analyzer", END)
    
    # Compile and return the workflow
    return workflow.compile()


def run_analysis(
    company_url: str,
    company_name: str = "",
    company_description: str = "",
    models: list = None
) -> WorkflowState:
    """
    Execute the complete analysis workflow for a company.
    
    Initializes the workflow state with company information and executes
    all agents in sequence. Returns the final state containing all results
    including industry classification, visibility score, and detailed analysis.
    
    Args:
        company_url: The company's website URL
        company_name: The company name (optional)
        company_description: Brief description of the company (optional)
        models: List of AI models to test (optional, defaults to chatgpt and gemini)
        
    Returns:
        Final WorkflowState with all analysis results
        
    Example:
        >>> result = run_analysis(
        ...     company_url="https://hellofresh.com",
        ...     company_name="HelloFresh",
        ...     company_description="Meal kit delivery service",
        ...     models=["chatgpt", "gemini", "llama"]
        ... )
        >>> print(result["visibility_score"])
        75.5
    """
    from config.settings import settings
    
    # Initialize workflow state
    initial_state: WorkflowState = {
        "company_url": company_url,
        "company_name": company_name or "",
        "company_description": company_description or "",
        "industry": "",
        "queries": [],
        "model_responses": {},
        "visibility_score": 0.0,
        "analysis_report": {},
        "errors": [],
        "models": models or settings.DEFAULT_MODELS
    }
    
    # Create and execute the workflow
    workflow = create_workflow_graph()
    final_state = workflow.invoke(initial_state)
    
    return final_state
