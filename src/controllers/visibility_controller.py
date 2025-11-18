"""
Visibility Analysis Controller

Handles business logic for full visibility scoring workflow.
"""

from typing import Dict, Any
from graph_orchestrator import run_analysis
from config.settings import settings
from utils.helpers import generate_job_id


def analyze_visibility(
    company_url: str,
    company_name: str = "",
    company_description: str = "",
    models: list = None
) -> Dict[str, Any]:
    """
    Execute full visibility analysis workflow.
    
    Args:
        company_url: Company website URL
        company_name: Optional company name
        company_description: Optional company description
        models: List of AI models to test
        
    Returns:
        Dictionary with job_id, status, and analysis results
    """
    # Generate unique job ID
    job_id = generate_job_id()
    
    # Get models to test
    models_to_test = models or settings.DEFAULT_MODELS
    
    # Execute workflow
    workflow_result = run_analysis(
        company_url=company_url,
        company_name=company_name,
        company_description=company_description,
        models=models_to_test
    )
    
    # Map to response format
    return _map_workflow_to_response(job_id, workflow_result)


def _map_workflow_to_response(
    job_id: str,
    workflow_state: Dict[str, Any]
) -> Dict[str, Any]:
    """Map workflow state to API response format."""
    status_value = "completed" if not workflow_state.get("errors") else "completed_with_errors"
    
    analysis_report = workflow_state.get("analysis_report", {})
    
    model_results = {
        "by_model": analysis_report.get("by_model", {}),
        "sample_mentions": analysis_report.get("sample_mentions", []),
        "total_responses": analysis_report.get("total_responses", 0),
        "mention_rate": analysis_report.get("mention_rate", 0.0)
    }
    
    if workflow_state.get("errors"):
        model_results["errors"] = workflow_state["errors"]
    
    return {
        "job_id": job_id,
        "status": status_value,
        "industry": workflow_state.get("industry", "unknown"),
        "visibility_score": workflow_state.get("visibility_score", 0.0),
        "total_queries": len(workflow_state.get("queries", [])),
        "total_mentions": analysis_report.get("total_mentions", 0),
        "model_results": model_results
    }
