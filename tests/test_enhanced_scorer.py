"""
Test enhanced scorer analyzer with complete query log, category breakdown, and rankings.
"""

import sys
sys.path.insert(0, '/home/ajay/major-project/radar/fastapi-app')

from agents.scorer_analyzer import analyze_score


def test_enhanced_scorer():
    """Test the enhanced scorer with all new features."""
    
    # Mock state with sample data
    state = {
        "company_name": "HelloFresh",
        "competitors": ["Blue Apron", "Home Chef", "EveryPlate"],
        "queries": [
            "best meal kits for families",
            "HelloFresh vs Blue Apron",
            "organic meal delivery services",
            "budget-friendly meal kits",
            "how to choose a meal kit"
        ],
        "query_categories": {
            "product_selection": {
                "name": "Product Selection",
                "queries": ["best meal kits for families", "organic meal delivery services"]
            },
            "comparison": {
                "name": "Comparison",
                "queries": ["HelloFresh vs Blue Apron"]
            },
            "best_of": {
                "name": "Best-of Lists",
                "queries": ["budget-friendly meal kits"]
            },
            "how_to": {
                "name": "How-to & Educational",
                "queries": ["how to choose a meal kit"]
            }
        },
        "model_responses": {
            "chatgpt": [
                "For families, I recommend: 1. HelloFresh - great variety, 2. Blue Apron - premium quality, 3. Home Chef - flexible options",
                "HelloFresh and Blue Apron are both excellent. HelloFresh offers more variety while Blue Apron focuses on gourmet recipes.",
                "Top organic meal delivery: 1. Green Chef 2. HelloFresh 3. Sun Basket",
                "Budget options include EveryPlate, Dinnerly, and Home Chef",
                "When choosing a meal kit, consider HelloFresh for variety, Blue Apron for quality, or EveryPlate for budget"
            ],
            "gemini": [
                "Best meal kits: Blue Apron, HelloFresh, and Purple Carrot are top choices",
                "Comparing HelloFresh vs Blue Apron: Both are great, HelloFresh has more options",
                "HelloFresh offers organic options along with Sun Basket",
                "For budget: EveryPlate is cheapest, followed by Dinnerly",
                "HelloFresh is a solid choice for beginners, with Blue Apron for food enthusiasts"
            ]
        },
        "errors": []
    }
    
    # Run analysis
    result_state = analyze_score(state)
    
    # Print results
    print("\n" + "="*80)
    print("ENHANCED SCORER ANALYZER TEST RESULTS")
    print("="*80)
    
    report = result_state["analysis_report"]
    
    print(f"\n📊 OVERALL VISIBILITY SCORE: {report['visibility_score']}%")
    print(f"   Total Queries: {report['total_queries']}")
    print(f"   Total Mentions: {report['total_mentions']}")
    print(f"   Mention Rate: {report['mention_rate']}")
    
    print("\n" + "-"*80)
    print("📈 BY MODEL BREAKDOWN")
    print("-"*80)
    for model, stats in report["by_model"].items():
        print(f"\n{model.upper()}:")
        print(f"  Mentions: {stats['mentions']}/{stats['total_responses']} ({stats['mention_rate']*100:.1f}%)")
        print(f"  Competitor Mentions: {stats['competitor_mentions']}")
    
    print("\n" + "-"*80)
    print("📂 BY CATEGORY BREAKDOWN")
    print("-"*80)
    for category, stats in report["by_category"].items():
        print(f"\n{stats['name']}:")
        print(f"  Queries: {stats['total_queries']}")
        print(f"  Visibility: {stats['visibility']}%")
        print(f"  Mentions: {stats['mentions']}/{stats['total_responses']}")
        print(f"  By Model: {stats['by_model']}")
    
    print("\n" + "-"*80)
    print("🏆 COMPETITOR RANKINGS")
    print("-"*80)
    rankings = report["competitor_rankings"]
    print("\nOverall Rankings:")
    for i, comp in enumerate(rankings["overall"], 1):
        print(f"  {i}. {comp['name']}: {comp['total_mentions']} mentions ({comp['percentage']}%)")
    
    print("\nBy Category:")
    for category, comps in rankings["by_category"].items():
        print(f"\n  {category}:")
        for comp in comps[:3]:  # Top 3
            print(f"    - {comp['name']}: {comp['mentions']} mentions")
    
    print("\n" + "-"*80)
    print("📋 COMPLETE QUERY LOG (Sample)")
    print("-"*80)
    for i, entry in enumerate(report["query_log"][:3], 1):  # Show first 3
        print(f"\nQuery {i}: {entry['query']}")
        print(f"Category: {entry['category']}")
        for model, result in entry["results"].items():
            mentioned = "✓ YES" if result["mentioned"] else "✗ NO"
            rank_info = f" (Rank {result['rank']})" if result['rank'] else ""
            comps = f" with {', '.join(result['competitors_mentioned'][:2])}" if result['competitors_mentioned'] else ""
            print(f"  {model}: {mentioned}{rank_info}{comps}")
    
    print(f"\n... and {len(report['query_log']) - 3} more queries")
    
    print("\n" + "-"*80)
    print("💡 SAMPLE MENTIONS")
    print("-"*80)
    for mention in report["sample_mentions"]:
        print(f"  • {mention}")
    
    print("\n" + "="*80)
    print("✅ TEST COMPLETED SUCCESSFULLY")
    print("="*80)
    
    # Verify all required fields exist
    assert "visibility_score" in report
    assert "by_model" in report
    assert "by_category" in report
    assert "competitor_rankings" in report
    assert "query_log" in report
    assert len(report["query_log"]) == 5  # All queries
    
    # Verify query log structure
    for entry in report["query_log"]:
        assert "query" in entry
        assert "category" in entry
        assert "results" in entry
        for model_result in entry["results"].values():
            assert "mentioned" in model_result
            assert "rank" in model_result
            assert "competitors_mentioned" in model_result
    
    # Verify category breakdown
    assert len(report["by_category"]) > 0
    for cat_stats in report["by_category"].values():
        assert "visibility" in cat_stats
        assert "mentions" in cat_stats
        assert "total_queries" in cat_stats
    
    # Verify competitor rankings
    assert "overall" in report["competitor_rankings"]
    assert "by_category" in report["competitor_rankings"]
    
    print("\n✅ All assertions passed!")
    
    return result_state


if __name__ == "__main__":
    test_enhanced_scorer()
