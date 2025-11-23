"""
Real test for Industry Detector with LangGraph workflow.
Configure test parameters at the top and run.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import json
from agents.industry_detector import detect_industry
from models.schemas import WorkflowState

# ============================================================================
# TEST CONFIGURATION - EDIT THESE
# ============================================================================

TEST_COMPANY_URL = "https://boot.dev"
TEST_COMPANY_NAME = ""  # Leave empty to auto-detect
TEST_COMPANY_DESCRIPTION = ""  # Leave empty to auto-detect

# Optional: Provide competitor URLs (max 4)
TEST_COMPETITOR_URLS = {
    # "Blue Apron": "https://blueapron.com",
    # "EveryPlate": "https://everyplate.com",
}

TEST_LLM_PROVIDER = "llama"  # Options: openai, gemini, llama, claude (openai recommended)

# ============================================================================


def test_industry_detector():
    """Run the complete industry detection workflow."""
    
    print("=" * 70)
    print("🧪 INDUSTRY DETECTOR TEST")
    print("=" * 70)
    
    print(f"\n📋 Configuration:")
    print(f"   Company URL: {TEST_COMPANY_URL}")
    print(f"   Company Name: {TEST_COMPANY_NAME or '(auto-detect)'}")
    print(f"   Description: {TEST_COMPANY_DESCRIPTION or '(auto-detect)'}")
    print(f"   Competitors: {len(TEST_COMPETITOR_URLS)} provided")
    print(f"   LLM Provider: {TEST_LLM_PROVIDER}")
    
    # Prepare state
    state: WorkflowState = {
        "company_url": TEST_COMPANY_URL,
        "company_name": TEST_COMPANY_NAME,
        "company_description": TEST_COMPANY_DESCRIPTION,
        "competitor_urls": TEST_COMPETITOR_URLS,
        "errors": []
    }
    
    print(f"\n🚀 Starting workflow...\n")
    
    # Run detection
    result = detect_industry(state, llm_provider=TEST_LLM_PROVIDER)
    
    print("\n" + "=" * 70)
    print("📊 RESULTS")
    print("=" * 70)
    
    # Display results
    print(f"\n🏢 Company Information:")
    print(f"   Name: {result.get('company_name', 'N/A')}")
    print(f"   Description: {result.get('company_description', 'N/A')}")
    print(f"   Industry: {result.get('industry', 'N/A')}")
    print(f"   Product Category: {result.get('product_category', 'N/A')}")
    
    print(f"\n🎯 Target Audience:")
    print(f"   {result.get('target_audience', 'N/A')}")
    
    print(f"\n🔑 Market Keywords:")
    keywords = result.get('market_keywords', [])
    if keywords:
        print(f"   {', '.join(keywords)}")
    else:
        print("   N/A")
    
    print(f"\n💎 Brand Positioning:")
    positioning = result.get('brand_positioning', {})
    if positioning:
        print(f"   Value Prop: {positioning.get('value_proposition', 'N/A')}")
        print(f"   Price: {positioning.get('price_positioning', 'N/A')}")
        differentiators = positioning.get('differentiators', [])
        if differentiators:
            print(f"   Differentiators:")
            for diff in differentiators:
                print(f"      - {diff}")
    else:
        print("   N/A")
    
    print(f"\n🎯 Buyer Intent Signals:")
    intent = result.get('buyer_intent_signals', {})
    if intent:
        questions = intent.get('common_questions', [])
        if questions:
            print(f"   Common Questions:")
            for q in questions[:3]:
                print(f"      - {q}")
        
        factors = intent.get('decision_factors', [])
        if factors:
            print(f"   Decision Factors: {', '.join(factors)}")
        
        pain_points = intent.get('pain_points', [])
        if pain_points:
            print(f"   Pain Points: {', '.join(pain_points)}")
    else:
        print("   N/A")
    
    print(f"\n🏭 Industry-Specific Data:")
    industry_data = result.get('industry_specific', {})
    if industry_data:
        for key, value in industry_data.items():
            print(f"   {key}: {value}")
    else:
        print("   N/A")
    
    print(f"\n🏆 Competitors:")
    competitors = result.get('competitors_data', [])
    if competitors:
        for comp in competitors:
            print(f"\n   {comp.get('name', 'Unknown')}")
            print(f"      Description: {comp.get('description', 'N/A')}")
            print(f"      Price Tier: {comp.get('price_tier', 'N/A')}")
            print(f"      Positioning: {comp.get('positioning', 'N/A')}")
            
            # Show enriched data if available
            if comp.get('value_proposition'):
                print(f"      Value Prop: {comp.get('value_proposition')}")
            if comp.get('unique_features'):
                print(f"      Features: {', '.join(comp.get('unique_features', []))}")
    else:
        print("   None detected")
    
    print(f"\n📝 Scraped Content:")
    content = result.get('scraped_content', '')
    print(f"   Length: {len(content)} characters")
    
    print(f"\n⚠️  Errors:")
    errors = result.get('errors', [])
    if errors:
        for error in errors:
            print(f"   - {error}")
    else:
        print("   None")
    
    print("\n" + "=" * 70)
    
    # Save full results to JSON
    output_file = Path(__file__).parent / "industry_detector_results.json"
    with open(output_file, 'w') as f:
        # Convert to serializable format
        serializable_result = {
            k: v for k, v in result.items() 
            if k != 'scraped_content'  # Exclude large content
        }
        json.dump(serializable_result, f, indent=2)
    
    print(f"💾 Full results saved to: {output_file}")
    print("=" * 70)
    
    # Assertions
    if not result.get('company_name'):
        print("\n⚠️  WARNING: Company name not detected")
        print("   This might indicate:")
        print("   - API key issue for the selected LLM provider")
        print("   - Rate limiting")
        print("   - Network issues")
        print(f"   - Check your {TEST_LLM_PROVIDER.upper()}_API_KEY in .env")
        if result.get('errors'):
            print(f"\n   Errors encountered:")
            for err in result['errors']:
                print(f"      - {err}")
    else:
        assert result.get('industry') in ['technology', 'retail', 'healthcare', 'finance', 'food_services', 'other']
        print("\n✅ TEST PASSED!")


if __name__ == "__main__":
    test_industry_detector()
