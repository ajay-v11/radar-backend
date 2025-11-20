"""
Test the improved industry detector with all enhancements.
"""

from agents.industry_detector import detect_industry
from config.database import test_connections
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)


def test_improvements():
    """Test all improvements to industry detector."""
    
    print("\n" + "="*70)
    print("Testing Industry Detector Improvements")
    print("="*70 + "\n")
    
    # Check database connections
    print("1. Checking database connections...")
    status = test_connections()
    
    if not status["chromadb"]["connected"]:
        print("⚠️  ChromaDB not connected - vector storage will be skipped")
    else:
        print("✅ ChromaDB connected")
    
    if not status["redis"]["connected"]:
        print("⚠️  Redis not connected - caching will be skipped")
    else:
        print("✅ Redis connected")
    
    # Test 1: First run (should scrape)
    print("\n2. Testing first run (should scrape)...")
    test_url = "https://www.nike.com"
    
    start_time = time.time()
    state1 = {
        "company_url": test_url,
        "company_name": "",
        "company_description": "",
        "errors": []
    }
    
    result1 = detect_industry(state1)
    time1 = time.time() - start_time
    
    print(f"   Time: {time1:.2f}s")
    print(f"   Company: {result1.get('company_name')}")
    print(f"   Industry: {result1.get('industry')}")
    print(f"   Competitors: {len(result1.get('competitors', []))}")
    print(f"   Errors: {len(result1.get('errors', []))}")
    
    if result1.get('errors'):
        print(f"   Error details: {result1['errors']}")
    
    # Test 2: Second run (should use cache)
    print("\n3. Testing second run (should use cache)...")
    
    start_time = time.time()
    state2 = {
        "company_url": test_url,
        "company_name": "",
        "company_description": "",
        "errors": []
    }
    
    result2 = detect_industry(state2)
    time2 = time.time() - start_time
    
    print(f"   Time: {time2:.2f}s")
    
    if time2 < time1 * 0.5:
        print(f"   ✅ Cache working! {((time1 - time2) / time1 * 100):.0f}% faster")
    else:
        print(f"   ⚠️  Cache may not be working (check Redis connection)")
    
    # Test 3: Competitor validation
    print("\n4. Testing competitor data validation...")
    competitors = result2.get('competitors', [])
    competitors_data = result2.get('competitors_data', [])
    
    if competitors_data:
        print(f"   ✅ Rich competitor data extracted: {len(competitors_data)} competitors")
        
        # Check first competitor structure
        if competitors_data:
            first_comp = competitors_data[0]
            has_name = bool(first_comp.get('name'))
            has_desc = bool(first_comp.get('description'))
            has_products = bool(first_comp.get('products'))
            has_positioning = bool(first_comp.get('positioning'))
            
            print(f"   Competitor structure:")
            print(f"     - Name: {'✅' if has_name else '❌'}")
            print(f"     - Description: {'✅' if has_desc else '❌'}")
            print(f"     - Products: {'✅' if has_products else '❌'}")
            print(f"     - Positioning: {'✅' if has_positioning else '❌'}")
    else:
        print(f"   ⚠️  No rich competitor data (may be old format)")
    
    # Test 4: Error handling
    print("\n5. Testing error handling...")
    state3 = {
        "company_url": "https://invalid-url-that-does-not-exist-12345.com",
        "company_name": "",
        "company_description": "",
        "errors": []
    }
    
    result3 = detect_industry(state3)
    
    if result3.get('errors'):
        print(f"   ✅ Errors properly logged: {len(result3['errors'])} errors")
        print(f"   Error: {result3['errors'][0][:80]}...")
    else:
        print(f"   ⚠️  No errors captured (unexpected)")
    
    # Summary
    print("\n" + "="*70)
    print("Summary:")
    print("="*70)
    
    checks = []
    checks.append(("Scraping works", bool(result1.get('company_name'))))
    checks.append(("Caching works", time2 < time1 * 0.5 if status["redis"]["connected"] else None))
    checks.append(("Competitor extraction", len(competitors) > 0))
    checks.append(("Data validation", len(competitors_data) > 0))
    checks.append(("Error handling", len(result3.get('errors', [])) > 0))
    
    passed = sum(1 for _, result in checks if result is True)
    total = sum(1 for _, result in checks if result is not None)
    
    for check_name, result in checks:
        if result is True:
            print(f"✅ {check_name}")
        elif result is False:
            print(f"❌ {check_name}")
        else:
            print(f"⚠️  {check_name} (skipped)")
    
    print(f"\n📊 Results: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n🎉 All improvements working correctly!")
    else:
        print(f"\n⚠️  {total - passed} checks failed or skipped")
    
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    test_improvements()
