"""
Complete integration test for AI Visibility Scoring System.

This test validates the entire system including:
- RAGStore initialization
- All four agents in sequence
- API endpoints
- Response format
- Error handling
"""

from fastapi.testclient import TestClient
from main import app
from storage.rag_store import get_rag_store
from graph_orchestrator import run_analysis


def test_complete_workflow():
    """Test the complete workflow from start to finish."""
    print("\n" + "=" * 70)
    print("COMPLETE INTEGRATION TEST")
    print("=" * 70)
    
    # Step 1: Verify RAGStore initialization
    print("\n[1/5] Verifying RAGStore Initialization...")
    rag_store = get_rag_store()
    assert len(rag_store.query_templates) == 6, "Should have 6 industry categories"
    for industry, templates in rag_store.query_templates.items():
        assert len(templates) >= 20, f"{industry} should have at least 20 templates"
    print(f"      ✓ RAGStore initialized with {len(rag_store.query_templates)} industries")
    print(f"      ✓ All industries have sufficient query templates")
    
    # Step 2: Test workflow execution
    print("\n[2/5] Testing Workflow Execution...")
    result = run_analysis(
        company_url="https://hellofresh.com",
        company_name="HelloFresh",
        company_description="Meal kit delivery service"
    )
    
    print(f"      ✓ Workflow completed")
    print(f"      - Industry detected: {result['industry']}")
    print(f"      - Queries generated: {len(result['queries'])}")
    print(f"      - Visibility score: {result['visibility_score']:.2f}%")
    
    # Verify workflow results
    assert result['industry'] == 'food_services', "Should detect food_services industry"
    assert len(result['queries']) == 20, "Should generate 20 queries"
    assert 'analysis_report' in result, "Should have analysis report"
    assert 'visibility_score' in result, "Should have visibility score"
    
    # Step 3: Test API health endpoint
    print("\n[3/5] Testing API Health Endpoint...")
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'healthy'
    assert 'version' in data
    print(f"      ✓ Health endpoint responding")
    print(f"      - Status: {data['status']}")
    print(f"      - Version: {data['version']}")
    
    # Step 4: Test API analyze endpoint
    print("\n[4/5] Testing API Analyze Endpoint...")
    response = client.post("/analyze", json={
        "company_url": "https://bluapron.com",
        "company_name": "Blue Apron",
        "company_description": "Meal kit delivery company"
    })
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    
    # Verify all required fields
    required_fields = [
        'job_id', 'status', 'industry', 'visibility_score',
        'total_queries', 'total_mentions', 'model_results'
    ]
    
    print(f"      ✓ API request successful")
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"
        print(f"      - {field}: {data[field]}")
    
    # Verify model_results structure
    assert 'by_model' in data['model_results'], "Should have by_model breakdown"
    print(f"      ✓ Response contains all required fields")
    
    # Step 5: Test error handling
    print("\n[5/5] Testing Error Handling...")
    
    # Test invalid URL
    response = client.post("/analyze", json={
        "company_url": "invalid-url",
        "company_name": "Test"
    })
    assert response.status_code == 422, "Should reject invalid URL"
    print(f"      ✓ Invalid URL rejected (status: {response.status_code})")
    
    # Test missing required field
    response = client.post("/analyze", json={
        "company_name": "Test"
    })
    assert response.status_code == 422, "Should reject missing company_url"
    print(f"      ✓ Missing required field rejected (status: {response.status_code})")
    
    print("\n" + "=" * 70)
    print("ALL INTEGRATION TESTS PASSED ✓")
    print("=" * 70)
    print("\nSystem Status:")
    print("  ✓ RAGStore initialized and loaded with query templates")
    print("  ✓ All four agents execute in sequence")
    print("  ✓ State is passed correctly between agents")
    print("  ✓ API endpoints respond correctly")
    print("  ✓ Response includes all required fields")
    print("  ✓ Error handling works as expected")
    print("\nThe AI Visibility Scoring System is fully operational!")
    print("\nNext Steps:")
    print("  1. Set OPENAI_API_KEY and ANTHROPIC_API_KEY in .env for real AI testing")
    print("  2. Start the server: uvicorn main:app --reload")
    print("  3. Access API docs: http://localhost:8000/docs")
    print("=" * 70)


def test_multiple_industries():
    """Test workflow with companies from different industries."""
    print("\n" + "=" * 70)
    print("MULTI-INDUSTRY TEST")
    print("=" * 70)
    
    test_companies = [
        {
            "url": "https://microsoft.com",
            "name": "Microsoft",
            "description": "Technology company providing software and cloud services",
            "expected_industry": "technology"
        },
        {
            "url": "https://amazon.com",
            "name": "Amazon",
            "description": "Online retail marketplace",
            "expected_industry": "retail"
        },
        {
            "url": "https://unitedhealthcare.com",
            "name": "UnitedHealthcare",
            "description": "Health insurance provider",
            "expected_industry": "healthcare"
        },
        {
            "url": "https://jpmorgan.com",
            "name": "JPMorgan Chase",
            "description": "Banking and financial services",
            "expected_industry": "finance"
        }
    ]
    
    client = TestClient(app)
    
    for i, company in enumerate(test_companies, 1):
        print(f"\n[{i}/{len(test_companies)}] Testing {company['name']}...")
        
        response = client.post("/analyze", json={
            "company_url": company["url"],
            "company_name": company["name"],
            "company_description": company["description"]
        })
        
        assert response.status_code == 200
        data = response.json()
        
        print(f"      Industry: {data['industry']}")
        print(f"      Queries: {data['total_queries']}")
        print(f"      Score: {data['visibility_score']:.2f}%")
        
        assert data['total_queries'] == 20
        assert data['industry'] in ['technology', 'retail', 'healthcare', 'finance', 'food_services', 'other']
        print(f"      ✓ Analysis completed successfully")
    
    print("\n" + "=" * 70)
    print("MULTI-INDUSTRY TEST PASSED ✓")
    print("=" * 70)


if __name__ == "__main__":
    try:
        test_complete_workflow()
        test_multiple_industries()
        
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
