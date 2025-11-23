"""
Test script for Visibility Orchestration workflow.

This tests the complete 3-agent orchestration:
1. Query Generator (uses dynamic query_categories_template)
2. AI Model Tester
3. Scorer Analyzer

Prerequisites:
- Run Phase 1 (industry detection) first to get company_data
- Or use the cached result from test_dynamic_result.json
"""

import json
import logging
from agents.visibility_orchestrator import run_visibility_orchestration

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def load_company_data_from_cache():
    """Load company data from test_dynamic_result.json."""
    try:
        with open("test_dynamic_result.json", "r") as f:
            data = json.load(f)
            # Add company_url if missing (for backward compatibility)
            if "company_url" not in data:
                data["company_url"] = "https://www.flipkart.com"
            # Add target_region if missing (for backward compatibility)
            if "target_region" not in data:
                data["target_region"] = "India"
            return data
    except FileNotFoundError:
        logger.error("test_dynamic_result.json not found. Run test_dynamic_industry.py first.")
        return None


def test_orchestration_with_cached_data():
    """Test orchestration using cached company data."""
    logger.info("=" * 80)
    logger.info("Testing Visibility Orchestration with Cached Data")
    logger.info("=" * 80)
    
    # Load company data from cache
    company_data = load_company_data_from_cache()
    
    if not company_data:
        logger.error("Cannot proceed without company data")
        return
    
    logger.info(f"\n📋 Company Data Loaded:")
    logger.info(f"   Company: {company_data.get('company_name')}")
    logger.info(f"   Industry: {company_data.get('industry')}")
    logger.info(f"   Competitors: {len(company_data.get('competitors', []))}")
    logger.info(f"   Query Categories: {len(company_data.get('query_categories_template', {}))}")
    
    # Progress callback
    def progress_callback(step, status, message, data):
        logger.info(f"   [{step}] {status}: {message}")
    
    # Run orchestration
    logger.info("\n🚀 Starting Visibility Orchestration...")
    
    try:
        result = run_visibility_orchestration(
            company_data=company_data,
            num_queries=20,  # Small number for testing
            models=["claude", "llama"],
            llm_provider="claude",
            progress_callback=progress_callback
        )
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ ORCHESTRATION COMPLETE")
        logger.info("=" * 80)
        
        logger.info(f"\n📊 Results Summary:")
        logger.info(f"   Total Queries: {len(result['queries'])}")
        logger.info(f"   Query Categories: {len(result['query_categories'])}")
        logger.info(f"   Total Responses: {sum(len(r) for r in result['model_responses'].values())}")
        logger.info(f"   Visibility Score: {result['visibility_score']}%")
        logger.info(f"   Errors: {len(result['errors'])}")
        
        # Show query categories used
        logger.info(f"\n🎯 Query Categories Used:")
        for cat_key, cat_data in result['query_categories'].items():
            logger.info(f"   - {cat_data['name']}: {len(cat_data['queries'])} queries")
        
        # Show sample queries
        logger.info(f"\n📝 Sample Queries (first 5):")
        for i, query in enumerate(result['queries'][:5], 1):
            logger.info(f"   {i}. {query}")
        
        # Show model results
        logger.info(f"\n🤖 Model Results:")
        analysis_report = result['analysis_report']
        for model, stats in analysis_report.get('by_model', {}).items():
            logger.info(f"   {model}: {stats['mentions']}/{stats['total_responses']} mentions ({stats['mention_rate']*100:.1f}%)")
        
        # Show category breakdown
        logger.info(f"\n📈 Category Breakdown:")
        for cat_key, stats in analysis_report.get('by_category', {}).items():
            logger.info(f"   {stats['name']}: {stats['visibility']:.1f}% visibility ({stats['mentions']}/{stats['total_responses']} mentions)")
        
        # Show competitor rankings
        logger.info(f"\n🏆 Top Competitors:")
        for i, comp in enumerate(analysis_report.get('competitor_rankings', {}).get('overall', [])[:5], 1):
            logger.info(f"   {i}. {comp['name']}: {comp['total_mentions']} mentions ({comp['percentage']:.1f}%)")
        
        # Show errors if any
        if result['errors']:
            logger.warning(f"\n⚠️  Errors encountered:")
            for error in result['errors']:
                logger.warning(f"   - {error}")
        
        # Save result
        output_file = "test_orchestration_result.json"
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)
        logger.info(f"\n💾 Full result saved to: {output_file}")
        
        return result
        
    except Exception as e:
        logger.error(f"\n❌ Orchestration failed: {str(e)}", exc_info=True)
        return None


def test_orchestration_with_fresh_data():
    """Test orchestration with fresh industry detection."""
    logger.info("=" * 80)
    logger.info("Testing Visibility Orchestration with Fresh Data")
    logger.info("=" * 80)
    
    from agents.industry_detection_agent import run_industry_detection_workflow
    
    # Run industry detection first
    logger.info("\n🔍 Running Industry Detection...")
    
    company_url = "https://www.amazon.com"
    
    industry_result = run_industry_detection_workflow(
        company_url=company_url,
        target_region="India",
        llm_provider="openai"
    )
    
    logger.info(f"\n✓ Industry Detection Complete:")
    logger.info(f"   Company: {industry_result['company_name']}")
    logger.info(f"   Industry: {industry_result['industry']}")
    logger.info(f"   Query Categories: {len(industry_result['query_categories_template'])}")
    
    # Now run orchestration
    logger.info("\n🚀 Starting Visibility Orchestration...")
    
    result = run_visibility_orchestration(
        company_data=industry_result,
        num_queries=10,
        models=["chatgpt", "gemini"],
        llm_provider="openai"
    )
    
    logger.info(f"\n✅ Complete! Visibility Score: {result['visibility_score']}%")
    
    return result


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--fresh":
        # Test with fresh industry detection
        test_orchestration_with_fresh_data()
    else:
        # Test with cached data (faster)
        test_orchestration_with_cached_data()
