"""
Simple test for query generator agent.

This script tests the query generator directly without needing the API server.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.query_generator import generate_queries, INDUSTRY_CATEGORIES
from models.schemas import WorkflowState


def test_query_generator():
    """Test the query generator with a sample company."""
    
    print("=" * 80)
    print("QUERY GENERATOR TEST")
    print("=" * 80)
    print()
    
    # Create a sample state (as if industry detector already ran)
    state: WorkflowState = {
        "company_url": "https://hellofresh.com",
        "company_name": "HelloFresh",
        "company_description": "Meal kit delivery service providing fresh ingredients and recipes",
        "company_summary": "HelloFresh is a meal kit delivery service that provides customers with pre-portioned ingredients and easy-to-follow recipes delivered to their door.",
        "industry": "food_services",
        "competitors": ["Blue Apron", "Home Chef", "EveryPlate", "Dinnerly", "Factor"],
        "errors": [],
        "num_queries": 50  # Test with 50 queries
    }
    
    print(f"Company: {state['company_name']}")
    print(f"Industry: {state['industry']}")
    print(f"Competitors: {', '.join(state['competitors'])}")
    print(f"Generating {state['num_queries']} queries...")
    print()
    
    # Generate queries
    print("Generating queries...")
    result_state = generate_queries(state)
    
    # Display results
    print()
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print()
    
    queries = result_state.get("queries", [])
    query_categories = result_state.get("query_categories", {})
    errors = result_state.get("errors", [])
    
    print(f"Total Queries Generated: {len(queries)}")
    print(f"Categories: {len(query_categories)}")
    print()
    
    if errors:
        print("⚠️  ERRORS:")
        for error in errors:
            print(f"  - {error}")
        print()
    
    # Display queries by category
    for category_key, category_data in query_categories.items():
        category_name = category_data["name"]
        category_queries = category_data["queries"]
        
        print(f"\n📁 {category_name} ({len(category_queries)} queries)")
        print("-" * 80)
        
        for idx, query in enumerate(category_queries, 1):
            print(f"  {idx}. {query}")
    
    print()
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    
    # Validate results
    assert len(queries) > 0, "No queries generated"
    assert len(query_categories) == 5, f"Expected 5 categories, got {len(query_categories)}"
    
    print("\n✅ All assertions passed!")


if __name__ == "__main__":
    test_query_generator()
