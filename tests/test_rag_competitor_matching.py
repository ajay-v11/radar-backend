"""
Test script for RAG-based competitor matching.

This script demonstrates the semantic competitor matching functionality.
"""

from utils.competitor_matcher import get_competitor_matcher
from config.database import test_connections
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_competitor_matching():
    """Test the RAG-based competitor matching system."""
    
    print("\n" + "="*60)
    print("Testing RAG-Based Competitor Matching")
    print("="*60 + "\n")
    
    # 1. Test database connections
    print("1. Testing database connections...")
    status = test_connections()
    
    if not status["chromadb"]["connected"]:
        print(f"❌ ChromaDB connection failed: {status['chromadb']['error']}")
        print("   Make sure ChromaDB is running: docker-compose up -d chromadb")
        return
    
    print("✅ ChromaDB connected")
    
    if not status["redis"]["connected"]:
        print(f"⚠️  Redis connection failed: {status['redis']['error']}")
        print("   Redis is optional but recommended")
    else:
        print("✅ Redis connected")
    
    # 2. Initialize competitor matcher
    print("\n2. Initializing competitor matcher...")
    matcher = get_competitor_matcher()
    print("✅ Competitor matcher initialized")
    
    # 3. Store test competitors with rich metadata
    print("\n3. Storing test competitors with rich metadata...")
    test_company = "HelloFresh"
    test_competitors = [
        "Blue Apron",
        "Home Chef",
        "Sunbasket",
        "EveryPlate",
        "Dinnerly"
    ]
    
    success = matcher.store_competitors(
        company_name=test_company,
        competitors=test_competitors,
        industry="food_services",
        descriptions={
            "Blue Apron": "Meal kit delivery service with chef-designed recipes and premium ingredients",
            "Home Chef": "Meal delivery service with customizable meal options and flexible plans",
            "Sunbasket": "Organic meal kit delivery focused on healthy, clean eating",
            "EveryPlate": "Budget-friendly meal kit service with simple recipes",
            "Dinnerly": "Affordable meal delivery with easy-to-follow recipes"
        },
        metadata_extra={
            "Blue Apron": {
                "products": "meal kits, wine pairing, chef recipes",
                "positioning": "premium, gourmet, chef-designed"
            },
            "Home Chef": {
                "products": "meal kits, oven-ready meals, customizable options",
                "positioning": "flexible, customizable, family-friendly"
            },
            "Sunbasket": {
                "products": "organic meal kits, paleo, gluten-free options",
                "positioning": "healthy, organic, clean eating"
            },
            "EveryPlate": {
                "products": "budget meal kits, simple recipes",
                "positioning": "affordable, budget-friendly, value"
            },
            "Dinnerly": {
                "products": "cheap meal kits, easy recipes",
                "positioning": "low-cost, simple, economical"
            }
        }
    )
    
    if success:
        print(f"✅ Stored {len(test_competitors)} competitors for {test_company}")
    else:
        print("❌ Failed to store competitors")
        return
    
    # 4. Test semantic search
    print("\n4. Testing semantic search...")
    
    test_responses = [
        "For meal kits, I recommend Blue Apron as they have great recipes.",
        "The best budget meal delivery is EveryPlate, it's very affordable.",
        "If you want organic options, try that sunbasket company.",
        "Home Chef is good if you like customization.",
        "I've heard good things about the meal kit from Dinnerly.",
        "HelloFresh is the most popular meal kit service.",
        "For healthy eating, consider the organic meal delivery from Sunbasket.",
        "Looking for premium gourmet meal kits with chef-designed recipes.",
        "Need an economical meal delivery service that's cheap.",
        "Want flexible meal options with customizable plans."
    ]
    
    print(f"\nAnalyzing {len(test_responses)} test responses...\n")
    
    for i, response in enumerate(test_responses, 1):
        print(f"Response {i}: \"{response[:60]}...\"")
        
        matches = matcher.find_competitor_mentions(
            company_name=test_company,
            text=response,
            top_k=3
        )
        
        if matches:
            for match in matches:
                print(f"  ✓ Found: {match['competitor_name']} (similarity: {match['similarity']:.3f})")
        else:
            print("  - No matches found")
        print()
    
    # 5. Test batch analysis
    print("\n5. Testing batch analysis...")
    has_mention, mentioned = matcher.analyze_response_for_mentions(
        company_name=test_company,
        response="I love using HelloFresh and Blue Apron for my weekly meals",
        competitors=test_competitors
    )
    
    print(f"Has mention: {has_mention}")
    print(f"Mentioned competitors: {mentioned}")
    
    # 6. Get stored competitors
    print("\n6. Retrieving stored competitors...")
    stored = matcher.get_competitors_for_company(test_company)
    print(f"Stored competitors for {test_company}: {stored}")
    
    print("\n" + "="*60)
    print("✅ All tests completed successfully!")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_competitor_matching()
