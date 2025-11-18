"""
Query Generator Agent

This agent generates industry-specific search queries for AI model testing
by retrieving templates from the RAG Store and customizing them with
company-specific information.
"""

import random
from typing import List
from models.schemas import WorkflowState
from storage.rag_store import get_rag_store


def generate_queries(state: WorkflowState) -> WorkflowState:
    """
    Generates 20 industry-specific queries using templates from RAG store.
    
    Retrieves query templates based on the detected industry, customizes them
    with company name and context, and generates exactly 20 unique queries
    for AI model testing.
    
    Args:
        state: WorkflowState containing industry and company_name
        
    Returns:
        Updated WorkflowState with queries list populated
        
    Requirements:
        - 4.1: Create a minimum of 20 search queries based on detected industry
        - 4.2: Retrieve industry-specific query templates from RAG Store
        - 4.3: Customize query templates with company name and relevant context
        - 4.4: Return list of generated queries to workflow state
    """
    # Get industry and company information from state
    industry = state.get("industry", "other")
    company_name = state.get("company_name", "")
    
    # Initialize errors list if not present
    if "errors" not in state:
        state["errors"] = []
    
    # Get RAG Store instance
    rag_store = get_rag_store()
    
    # Retrieve query templates for the detected industry
    templates = rag_store.get_query_templates(industry)
    
    if not templates:
        # Fallback to "other" industry if no templates found
        templates = rag_store.get_query_templates("other")
        state["errors"].append(f"No templates found for industry '{industry}', using default templates")
    
    # Generate queries by customizing templates
    queries: List[str] = []
    
    # We need exactly 20 queries
    num_queries_needed = 20
    
    if len(templates) < num_queries_needed:
        # If we don't have enough templates, use all and log a warning
        state["errors"].append(
            f"Only {len(templates)} templates available for industry '{industry}', "
            f"expected at least {num_queries_needed}"
        )
        queries = templates[:num_queries_needed]
    else:
        # Randomly select 20 unique templates to ensure variety
        selected_templates = random.sample(templates, num_queries_needed)
        queries = selected_templates
    
    # Customize queries with company name where appropriate
    # Some queries are generic and work as-is, others can be enhanced
    customized_queries: List[str] = []
    
    for query in queries:
        # Check if query could benefit from company name insertion
        customized_query = _customize_query(query, company_name, industry)
        customized_queries.append(customized_query)
    
    # Update state with generated queries
    state["queries"] = customized_queries
    
    return state


def _customize_query(query: str, company_name: str, industry: str) -> str:
    """
    Customize a query template with company-specific information.
    
    This helper function attempts to make queries more specific by incorporating
    the company name where it makes sense contextually.
    
    Args:
        query: Original query template
        company_name: Name of the company being analyzed
        industry: Industry category
        
    Returns:
        Customized query string
    """
    # For some queries, we can add company name as a comparison point
    # This makes the query more likely to elicit responses that mention the company
    
    # Patterns that work well with company name insertion
    comparison_keywords = ["best", "top", "leading", "compare", "recommend"]
    
    # Check if query contains comparison keywords
    query_lower = query.lower()
    has_comparison = any(keyword in query_lower for keyword in comparison_keywords)
    
    if has_comparison and company_name:
        # Add company name as a reference point in some queries
        # Use this sparingly to maintain query variety
        if random.random() < 0.3:  # 30% chance to add company name
            # Add company name as a comparison reference
            if "?" in query:
                # Insert before the question mark
                query = query.replace("?", f" like {company_name}?")
            else:
                # Append to the end
                query = f"{query} similar to {company_name}"
    
    return query
