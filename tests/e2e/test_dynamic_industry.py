"""
Quick test for the new dynamic industry detection workflow.
"""

from app.services.agents import run_industry_detection_workflow
import json

def test_dynamic_industry_detection():
    """Test the new dynamic industry classification."""
    
    print("🧪 Testing Dynamic Industry Detection\n")
    print("=" * 60)
    
    # Test with Flipkart
    result = run_industry_detection_workflow(
        company_url="https://www.flipkart.com/",
        target_region="India",
        llm_provider="claude",
        progress_callback=lambda step, status, msg, data: print(f"  [{step}] {msg}")
    )
    
    print("\n" + "=" * 60)
    print("📊 RESULTS\n")
    
    print(f"Company: {result['company_name']}")
    print(f"Description: {result['company_description']}")
    print(f"\n🏷️  Industry Classification:")
    print(f"  Specific Industry: {result['industry']}")
    print(f"  Broad Category: {result['broad_category']}")
    print(f"  Description: {result['industry_description']}")
    
    print(f"\n📋 Extraction Template:")
    template = result.get('extraction_template', {})
    print(f"  Fields: {', '.join(template.get('extract_fields', []))}")
    print(f"  Competitor Focus: {template.get('competitor_focus', 'N/A')}")
    
    print(f"\n🎯 Query Categories Template:")
    categories = result.get('query_categories_template', {})
    if categories:
        for key, cat in categories.items():
            print(f"  {cat['name']} ({cat['weight']*100:.0f}%): {cat['description']}")
    else:
        print("  No categories generated")
    
    print(f"\n🏢 Competitors ({len(result['competitors'])}):")
    for comp in result['competitors'][:5]:
        print(f"  - {comp}")
    
    print(f"\n⚠️  Errors: {len(result['errors'])}")
    for error in result['errors']:
        print(f"  - {error}")
    
    print("\n" + "=" * 60)
    
    # Save full result
    with open("test_dynamic_result.json", "w") as f:
        json.dump(result, f, indent=2)
    print("\n✅ Full result saved to test_dynamic_result.json")

if __name__ == "__main__":
    test_dynamic_industry_detection()
