"""
Test the FULL matching system (exact + semantic) as used in production.

This demonstrates how the scorer_analyzer actually works.
"""

from utils.competitor_matcher import get_competitor_matcher
from config.database import test_connections
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_full_system():
    """Test the complete matching system with exact + semantic."""
    
    print("\n" + "="*70)
    print("Testing FULL Matching System (Exact + Semantic)")
    print("="*70 + "\n")
    
    # Setup
    status = test_connections()
    if not status["chromadb"]["connected"]:
        print("❌ ChromaDB not connected")
        return
    
    matcher = get_competitor_matcher()
    
    # Store competitors
    test_company = "HelloFresh"
    test_competitors = ["Blue Apron", "Home Chef", "Sunbasket", "EveryPlate", "Dinnerly"]
    
    matcher.store_competitors(
        company_name=test_company,
        competitors=test_competitors,
        industry="food_services",
        descriptions={
            "Blue Apron": "Meal kit delivery with chef-designed recipes and premium ingredients",
            "Home Chef": "Meal delivery with customizable meal options and flexible plans",
            "Sunbasket": "Organic meal kit delivery focused on healthy, clean eating",
            "EveryPlate": "Budget-friendly meal kit service with simple recipes",
            "Dinnerly": "Affordable meal delivery with easy-to-follow recipes"
        },
        metadata_extra={
            "Blue Apron": {"products": "meal kits, wine", "positioning": "premium, gourmet"},
            "Home Chef": {"products": "meal kits, oven-ready", "positioning": "flexible, customizable"},
            "Sunbasket": {"products": "organic kits, paleo", "positioning": "healthy, organic"},
            "EveryPlate": {"products": "budget kits", "positioning": "affordable, value"},
            "Dinnerly": {"products": "cheap kits", "positioning": "low-cost, economical"}
        }
    )
    
    print("✅ Stored competitors with rich metadata\n")
    
    # Test responses
    test_cases = [
        {
            "response": "For meal kits, I recommend Blue Apron as they have great recipes.",
            "expected": ["Blue Apron"],
            "type": "Exact match in text"
        },
        {
            "response": "If you want organic options, try that sunbasket company.",
            "expected": ["Sunbasket"],
            "type": "Exact match (lowercase)"
        },
        {
            "response": "Home Chef is good if you like customization.",
            "expected": ["Home Chef"],
            "type": "Exact match"
        },
        {
            "response": "I've heard good things about the meal kit from Dinnerly.",
            "expected": ["Dinnerly"],
            "type": "Exact match"
        },
        {
            "response": "Looking for premium gourmet meal kits with chef-designed recipes.",
            "expected": ["Blue Apron"],
            "type": "Semantic (no name)"
        },
        {
            "response": "Need an economical meal delivery service that's cheap.",
            "expected": ["Dinnerly", "EveryPlate"],
            "type": "Semantic (no name)"
        },
        {
            "response": "Want flexible meal options with customizable plans.",
            "expected": ["Home Chef"],
            "type": "Semantic (no name)"
        },
        {
            "response": "HelloFresh is the most popular meal kit service.",
            "expected": [],
            "type": "Main company (not competitor)"
        }
    ]
    
    print("Testing Full System (Exact + Semantic):\n")
    print("-" * 70)
    
    total_tests = len(test_cases)
    passed = 0
    
    for i, test in enumerate(test_cases, 1):
        response = test["response"]
        expected = test["expected"]
        test_type = test["type"]
        
        # Use the FULL system (exact + semantic)
        has_mention, mentioned = matcher.analyze_response_for_mentions(
            company_name=test_company,
            response=response,
            competitors=test_competitors
        )
        
        # Check if we got expected results
        success = set(mentioned) == set(expected) if expected else not mentioned
        status = "✅ PASS" if success else "❌ FAIL"
        
        if success:
            passed += 1
        
        print(f"\nTest {i}: {test_type}")
        print(f"Response: \"{response[:60]}...\"")
        print(f"Expected: {expected}")
        print(f"Got:      {mentioned}")
        print(f"Result:   {status}")
    
    print("\n" + "-" * 70)
    print(f"\n📊 Results: {passed}/{total_tests} tests passed ({passed/total_tests*100:.0f}%)")
    
    if passed == total_tests:
        print("\n🎉 All tests passed! The system works correctly!")
    else:
        print(f"\n⚠️  {total_tests - passed} tests failed. System needs tuning.")
    
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    test_full_system()
