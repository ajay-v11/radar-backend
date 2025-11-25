"""
State model for visibility orchestration workflow.

Category-based batching: Process one category at a time with streaming results.
"""

from typing import Dict, List, TypedDict, Any, Optional


class VisibilityOrchestrationState(TypedDict):
    """
    State for category-based batching workflow.
    
    Flow: For each category → generate queries → test models → analyze → aggregate → stream
    """
    # Input (from Phase 1 - Industry Detection)
    company_url: str
    company_name: str
    company_description: str
    company_summary: str
    industry: str
    target_region: str
    competitors: List[str]
    query_categories_template: Dict  # Dynamic template from industry detector
    
    # Configuration
    num_queries: int
    models: List[str]
    llm_provider: str
    
    # Category tracking
    categories_to_process: List[str]  # Queue of categories to process
    current_category: Optional[str]  # Currently processing category
    completed_categories: List[str]  # Categories already processed
    category_distribution: Dict[str, int]  # How many queries per category
    
    # Per-category results (accumulated as we go)
    category_queries: Dict[str, List[str]]  # category -> queries
    category_responses: Dict[str, Dict[str, List[str]]]  # category -> model -> responses
    category_scores: Dict[str, float]  # category -> visibility score
    category_mentions: Dict[str, int]  # category -> mention count
    category_analysis: Dict[str, Dict[str, Any]]  # category -> detailed analysis
    
    # Current category working data
    current_queries: List[str]  # Queries for current category
    current_responses: Dict[str, List[str]]  # Responses for current category
    current_mentions: int  # Mentions in current category
    current_score: float  # Score for current category
    current_model_scores: Dict[str, Dict[str, Any]]  # Per-model scores for current category
    
    # Aggregated results (running totals)
    total_queries: int
    total_mentions: int
    total_responses: int
    partial_visibility_score: float
    model_mentions: Dict[str, int]  # Running total mentions per model
    model_totals: Dict[str, int]  # Running total responses per model
    partial_model_scores: Dict[str, float]  # Running per-model scores
    
    # Final output (same as before for compatibility)
    queries: List[str]  # All queries combined
    query_categories: Dict[str, Dict]  # All categories with their queries
    model_responses: Dict[str, List[str]]  # All responses combined
    visibility_score: float  # Final score
    analysis_report: Dict[str, Any]  # Final report
    
    # Metadata
    errors: List[str]
    completed: bool
