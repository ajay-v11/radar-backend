"""
Test query generation caching.

This script tests that query caching works correctly.
"""

import sys
import os
import time

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.query_generator import generate_queries
from models.schemas import WorkflowState


def test_query_caching():
    """Test that query generation caching works."""
    
    print("=" * 80)
    print("QUERY CACHING TEST")
    print("=" * 80)
    print()
    
    # Create a sample state
    state: WorkflowState = {
        "company_url": "https://example-test-company.com",
        "company_name": "TestCo",
        "company_description": "A test company for caching",
        "company_summary": "TestCo is a test company used for cache testing.",
        "industry": "technology",
        "competitors": ["CompetitorA", "CompetitorB"],
        "errors": [],
        "num_queries": 20
    }
    
    print("Test 1: First generation (should be CACHE MISS)")
    print("-" * 80)
    start_time = time.time()
    result1 = generate_queries(state)
    time1 = time.time() - start_time
    
    queries1 = result1.get("queries", [])
    print(f"✅ Generated {len(queries1)} queries in {time1:.2f} seconds")
    print(f"   First 3 queries:")
    for i, q in enumerate(queries1[:3], 1):
        print(f"   {i}. {q}")
    print()
    
    print("Test 2: Second generation with same params (should be CACHE HIT)")
    print("-" * 80)
    start_time = time.time()
    result2 = generate_queries(state)
    time2 = time.time() - start_time
    
    queries2 = result2.get("queries", [])
    print(f"✅ Retrieved {len(queries2)} queries in {time2:.2f} seconds")
    print(f"   First 3 queries:")
    for i, q in enumerate(queries2[:3], 1):
        print(f"   {i}. {q}")
    print()
    
    # Verify caching worked
    print("Verification:")
    print("-" * 80)
    
    if time2 < time1 * 0.1:  # Cache should be at least 10x faster
        print(f"✅ Cache is working! Second call was {time1/time2:.1f}x faster")
    else:
        print(f"⚠️  Cache might not be working. Time difference: {time1:.2f}s vs {time2:.2f}s")
    
    if queries1 == queries2:
        print("✅ Queries are identical (cached correctly)")
    else:
        print("❌ Queries are different (cache not working)")
    
    print()
    
    # Test 3: Different num_queries should be cache miss
    print("Test 3: Different num_queries (should be CACHE MISS)")
    print("-" * 80)
    state["num_queries"] = 30
    start_time = time.time()
    result3 = generate_queries(state)
    time3 = time.time() - start_time
    
    queries3 = result3.get("queries", [])
    print(f"✅ Generated {len(queries3)} queries in {time3:.2f} seconds")
    print()
    
    if time3 > time2 * 5:  # Should be much slower than cached call
        print(f"✅ Different params triggered new generation (not cached)")
    else:
        print(f"⚠️  Might have used cache incorrectly")
    
    print()
    print("=" * 80)
    print("CACHE TEST COMPLETE")
    print("=" * 80)
    print()
    print("Summary:")
    print(f"  First call (20 queries):  {time1:.2f}s - CACHE MISS")
    print(f"  Second call (20 queries): {time2:.2f}s - CACHE HIT (should be <0.1s)")
    print(f"  Third call (30 queries):  {time3:.2f}s - CACHE MISS")
    print()
    
    # Final assertions
    assert len(queries1) > 0, "No queries generated"
    assert queries1 == queries2, "Cache not returning same queries"
    assert len(queries3) > len(queries1), "Different num_queries not working"
    
    print("✅ All cache tests passed!")


if __name__ == "__main__":
    test_query_caching()
