"""
Pydantic models and state for query generator.
"""

from typing import Dict, List, TypedDict, Optional
from pydantic import BaseModel, Field


class CategoryQueries(BaseModel):
    """Queries generated for a specific category."""
    queries: List[str] = Field(description="List of search queries for this category")


class QueryGeneratorState(TypedDict):
    """State for the query generator graph."""
    # Input
    company_url: str
    company_name: str
    company_description: str
    company_summary: str
    industry: str
    competitors: List[str]
    query_categories_template: Dict  # Dynamic categories from industry detector
    num_queries: int
    llm_provider: str
    
    # Processing
    category_distribution: Dict[str, int]  # How many queries per category
    
    # Output
    queries: List[str]
    query_categories: Dict[str, Dict]  # Organized by category
    
    # Metadata
    errors: List[str]
    completed: bool
