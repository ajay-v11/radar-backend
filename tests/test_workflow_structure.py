"""
Test workflow structure and state transitions without API calls.

This test validates that all agents are properly connected and state
is passed correctly through the workflow.
"""

from models.schemas import WorkflowState
from agents.industry_detector import detect_industry
from agents.query_generator import generate_queries
from storage.rag_store import get_rag_store


def test_workflow_state_transitions():
    """Test that state transitions work correctly through the workflow."""
    print("\n=== Testing Workflow State Transitions ===\n")
    
    # Initialize RAGStore
    rag_store = get_rag_store()
    print(f"✓ RAGStore initialized with {len(rag_store.query_templates)} industries")
    
    # Step 1: Initialize state
    print("\n1. Initializing workflow state...")
    initial_state: WorkflowState = {
        "company_url": "https://hellofresh.com",
        "company_name": "HelloFresh",
        "company_description": "Meal kit delivery service with fresh ingredients",
        "industry": "",
        "queries": [],
        "model_responses": {},
        "visibility_score": 0.0,
        "analysis_report": {},
        "errors": []
    }
    print(f"   Company: {initial_state['company_name']}")
    print(f"   Description: {initial_state['company_description']}")
    
    # Step 2: Test Industry Detector
    print("\n2. Running Industry Detector Agent...")
    state_after_industry = detect_industry(initial_state)
    print(f"   Detected Industry: {state_after_industry['industry']}")
    assert state_after_industry['industry'] != "", "Industry should be detected"
    assert state_after_industry['industry'] in rag_store.query_templates.keys(), \
        f"Industry should be one of supported industries"
    print("   ✓ Industry detection successful")
    
    # Step 3: Test Query Generator
    print("\n3. Running Query Generator Agent...")
    state_after_queries = generate_queries(state_after_industry)
    print(f"   Generated Queries: {len(state_after_queries['queries'])}")
    assert len(state_after_queries['queries']) == 20, \
        f"Expected 20 queries, got {len(state_after_queries['queries'])}"
    print("   ✓ Query generation successful")
    
    # Print sample queries
    print("\n   Sample Queries:")
    for i, query in enumerate(state_after_queries['queries'][:3], 1):
        print(f"     {i}. {query}")
    
    # Step 4: Verify state structure
    print("\n4. Verifying final state structure...")
    required_fields = [
        "company_url", "company_name", "company_description",
        "industry", "queries", "model_responses", "visibility_score",
        "analysis_report", "errors"
    ]
    
    for field in required_fields:
        assert field in state_after_queries, f"Missing required field: {field}"
        print(f"   ✓ {field}: present")
    
    print("\n=== All Workflow Structure Tests Passed ✓ ===")
    return state_after_queries


def test_all_industries():
    """Test that query generation works for all supported industries."""
    print("\n=== Testing All Industry Categories ===\n")
    
    rag_store = get_rag_store()
    
    test_cases = [
        ("TechCorp", "Software development company", "technology"),
        ("ShopMart", "Online retail store", "retail"),
        ("HealthPlus", "Healthcare provider", "healthcare"),
        ("FinanceHub", "Financial services company", "finance"),
        ("HelloFresh", "Meal kit delivery", "food_services"),
        ("GenericCo", "General business", "other"),
    ]
    
    for company_name, description, expected_industry in test_cases:
        state: WorkflowState = {
            "company_url": f"https://{company_name.lower()}.com",
            "company_name": company_name,
            "company_description": description,
            "industry": "",
            "queries": [],
            "model_responses": {},
            "visibility_score": 0.0,
            "analysis_report": {},
            "errors": []
        }
        
        # Detect industry
        state = detect_industry(state)
        detected = state['industry']
        
        # Generate queries
        state = generate_queries(state)
        query_count = len(state['queries'])
        
        print(f"{company_name:15} -> {detected:15} ({query_count} queries)")
        assert query_count == 20, f"Expected 20 queries for {company_name}"
    
    print("\n✓ All industries tested successfully")


def test_response_format():
    """Test that the response format matches API requirements."""
    print("\n=== Testing Response Format ===\n")
    
    from main import map_workflow_to_response
    
    # Create a mock workflow state
    mock_state = {
        "company_url": "https://example.com",
        "company_name": "Example Corp",
        "company_description": "Test company",
        "industry": "technology",
        "queries": ["query1", "query2"] * 10,  # 20 queries
        "model_responses": {
            "chatgpt": ["response1", "response2"],
            "claude": ["response3", "response4"]
        },
        "visibility_score": 75.5,
        "analysis_report": {
            "total_mentions": 15,
            "total_responses": 40,
            "mention_rate": 0.75,
            "by_model": {
                "chatgpt": {"mentions": 8, "mention_rate": 0.80},
                "claude": {"mentions": 7, "mention_rate": 0.70}
            },
            "sample_mentions": ["Sample mention 1", "Sample mention 2"]
        },
        "errors": []
    }
    
    # Map to response format
    response = map_workflow_to_response("test-job-123", mock_state)
    
    # Verify required fields
    required_fields = [
        "job_id", "status", "industry", "visibility_score",
        "total_queries", "total_mentions", "model_results"
    ]
    
    print("Checking required fields:")
    for field in required_fields:
        value = getattr(response, field)
        print(f"  ✓ {field}: {value}")
        assert value is not None, f"Field {field} should not be None"
    
    # Verify specific values
    assert response.job_id == "test-job-123"
    assert response.status == "completed"
    assert response.industry == "technology"
    assert response.visibility_score == 75.5
    assert response.total_queries == 20
    assert response.total_mentions == 15
    assert "by_model" in response.model_results
    
    print("\n✓ Response format validation passed")


if __name__ == "__main__":
    print("=" * 70)
    print("AI Visibility Scoring System - Workflow Structure Tests")
    print("=" * 70)
    
    try:
        test_workflow_state_transitions()
        test_all_industries()
        test_response_format()
        
        print("\n" + "=" * 70)
        print("ALL WORKFLOW STRUCTURE TESTS PASSED ✓")
        print("=" * 70)
        print("\nThe workflow is properly wired and ready for end-to-end testing.")
        print("To test with real API calls, set OPENAI_API_KEY and ANTHROPIC_API_KEY")
        print("in the .env file and run: python test_e2e.py")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
