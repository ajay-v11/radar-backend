"""
State model for visibility orchestration workflow.
"""

from typing import Dict, List, TypedDict, Any


class VisibilityOrchestrationState(TypedDict):
    """
    Unified state for the complete visibility analysis workflow.
    
    This state flows through all 3 agents:
    1. Query Generator
    2. AI Model Tester
    3. Scorer Analyzer
    """
    # Input (from Phase 1 - Industry Detection)
    company_url: str
    company_name: str
    company_description: str
    company_summary: str
    industry: str
    target_region: str  # Target region for AI model context
    competitors: List[str]
    query_categories_template: Dict  # Dynamic template from industry detector
    
    # Configuration
    num_queries: int
    models: List[str]
    llm_provider: str
    
    # Query Generator Output
    queries: List[str]
    query_categories: Dict[str, Dict]
    
    # AI Model Tester Output
    model_responses: Dict[str, List[str]]
    
    # Scorer Analyzer Output
    visibility_score: float
    analysis_report: Dict[str, Any]
    
    # Metadata
    errors: List[str]
    completed: bool
