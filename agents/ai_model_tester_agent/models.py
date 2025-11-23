"""
Pydantic models and state for AI model tester.
"""

from typing import Dict, List, TypedDict


class AIModelTesterState(TypedDict):
    """State for the AI model tester graph."""
    # Input
    queries: List[str]
    models: List[str]
    target_region: str  # Region context for AI models
    
    # Processing
    current_query_index: int
    
    # Output
    model_responses: Dict[str, List[str]]  # model_name -> list of responses
    
    # Metadata
    errors: List[str]
    completed: bool
