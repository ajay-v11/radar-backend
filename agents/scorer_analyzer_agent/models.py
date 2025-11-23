"""
Pydantic models and state for scorer analyzer.
"""

from typing import Dict, List, TypedDict, Any


class ScorerAnalyzerState(TypedDict):
    """State for the scorer analyzer graph."""
    # Input
    company_name: str
    queries: List[str]
    model_responses: Dict[str, List[str]]
    query_categories: Dict[str, Dict]
    competitors: List[str]
    
    # Processing
    query_to_category: Dict[int, str]
    category_stats: Dict[str, Dict[str, Any]]
    competitor_stats: Dict[str, Dict[str, Any]]
    query_log: List[Dict[str, Any]]
    total_mentions: int
    total_responses: int
    sample_mentions: List[str]
    
    # Output
    visibility_score: float
    analysis_report: Dict[str, Any]
    
    # Metadata
    errors: List[str]
    completed: bool
