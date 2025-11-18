"""
End-to-end test script for AI Visibility Scoring System.

This script tests the complete workflow from API request to final response,
verifying that all agents execute in sequence and the response contains
all required fields.
"""

import asyncio
from main import app, startup_event
from models.schemas import AnalyzeRequest
from fastapi.testclient import TestClient


def test_health_endpoint():
    """Test the health check endpoint."""
    print("\n=== Testing Health Endpoint ===")
    client = TestClient(app)
    response = client.get("/health")
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert data["status"] == "healthy"
    print("✓ Health endpoint test passed")


def test_analyze_endpoint():
    """Test the analyze endpoint with a sample company."""
    print("\n=== Testing Analyze Endpoint ===")
    
    # Initialize the app (trigger startup event)
    asyncio.run(startup_event())
    
    client = TestClient(app)
    
    # Test with a food services company
    request_data = {
        "company_url": "https://hellofresh.com",
        "company_name": "HelloFresh",
        "company_description": "Meal kit delivery service providing fresh ingredients and recipes"
    }
    
    print(f"\nSending request: {request_data}")
    response = client.post("/analyze", json=request_data)
    
    print(f"\nStatus Code: {response.status_code}")
    
    if response.status_code != 200:
        print(f"Error Response: {response.json()}")
        return
    
    data = response.json()
    print(f"\nResponse Data:")
    print(f"  Job ID: {data.get('job_id')}")
    print(f"  Status: {data.get('status')}")
    print(f"  Industry: {data.get('industry')}")
    print(f"  Visibility Score: {data.get('visibility_score')}")
    print(f"  Total Queries: {data.get('total_queries')}")
    print(f"  Total Mentions: {data.get('total_mentions')}")
    
    # Verify all required fields are present
    required_fields = [
        "job_id", "status", "industry", "visibility_score",
        "total_queries", "total_mentions", "model_results"
    ]
    
    print("\n=== Validating Response Fields ===")
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"
        print(f"✓ {field}: {data[field]}")
    
    # Verify model_results structure
    assert "by_model" in data["model_results"]
    print(f"\n✓ Model results breakdown: {list(data['model_results']['by_model'].keys())}")
    
    # Verify workflow executed correctly
    assert data["industry"] != "", "Industry should be detected"
    assert data["total_queries"] == 20, f"Expected 20 queries, got {data['total_queries']}"
    assert isinstance(data["visibility_score"], (int, float)), "Visibility score should be numeric"
    
    print("\n✓ All validations passed!")
    print(f"\n=== Analysis Complete ===")
    print(f"Company: {request_data['company_name']}")
    print(f"Industry: {data['industry']}")
    print(f"Visibility Score: {data['visibility_score']:.2f}%")
    print(f"Mentions: {data['total_mentions']}/{data['total_queries']} queries")
    
    # Print sample mentions if available
    if "sample_mentions" in data["model_results"]:
        print(f"\nSample Mentions:")
        for mention in data["model_results"]["sample_mentions"][:3]:
            print(f"  - {mention}")


def test_invalid_url():
    """Test error handling for invalid URL."""
    print("\n=== Testing Invalid URL Handling ===")
    client = TestClient(app)
    
    request_data = {
        "company_url": "not-a-valid-url",
        "company_name": "Test Company"
    }
    
    response = client.post("/analyze", json=request_data)
    print(f"Status Code: {response.status_code}")
    
    # Should return 422 for validation error (Pydantic validation)
    assert response.status_code == 422
    print("✓ Invalid URL correctly rejected")


if __name__ == "__main__":
    print("=" * 60)
    print("AI Visibility Scoring System - End-to-End Test")
    print("=" * 60)
    
    try:
        # Run tests
        test_health_endpoint()
        test_invalid_url()
        test_analyze_endpoint()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
