"""
Test script for category-based batching workflow.

This tests the new visibility orchestrator with progressive category processing.
"""

import json
import logging
from agents.visibility_orchestrator import run_visibility_orchestration

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

logger = logging.getLogger(__name__)


def progress_callback(step, status, message, data):
    """Callback to track progress."""
    print(f"\n{'='*80}")
    print(f"STEP: {step}")
    print(f"STATUS: {status}")
    print(f"MESSAGE: {message}")
    if data:
        print(f"DATA: {json.dumps(data, indent=2)}")
    print(f"{'='*80}\n")


def test_category_batching():
    """Test the category-based batching workflow."""
    
    # Load real company data from test_dynamic_result.json
    logger.info("📂 Loading company data from test_dynamic_result.json...")
    
    with open('test_dynamic_result.json', 'r') as f:
        phase1_data = json.load(f)
    
    # Transform the query_categories_template to the expected format
    # The file has it as a dict, but we need it with a "categories" list
    query_categories_raw = phase1_data.get("query_categories_template", {})
    
    # Convert to the format expected by the orchestrator
    categories_list = []
    for category_key, category_data in query_categories_raw.items():
        categories_list.append({
            "category_key": category_key,
            "category_name": category_data.get("name", category_key),
            "weight": category_data.get("weight", 0.1),
            "description": category_data.get("description", ""),
            "examples": category_data.get("examples", [])
        })
    
    # Prepare company data in the format expected by orchestrator
    company_data = {
        "company_url": "https://flipkart.com",  # Add URL since it's not in the file
        "company_name": phase1_data["company_name"],
        "company_description": phase1_data["company_description"],
        "company_summary": phase1_data["company_summary"],
        "industry": phase1_data["industry"],
        "target_region": phase1_data["target_region"],
        "competitors": phase1_data["competitors"],
        "query_categories_template": {
            "categories": categories_list
        }
    }
    
    logger.info("🚀 Starting category-based batching test...")
    logger.info(f"Company: {company_data['company_name']}")
    logger.info(f"Industry: {company_data['industry']}")
    logger.info(f"Target Region: {company_data['target_region']}")
    logger.info(f"Categories: {len(categories_list)}")
    logger.info(f"Category names: {[c['category_key'] for c in categories_list]}")
    
    try:
        # Run the orchestration with progress callback
        result = run_visibility_orchestration(
            company_data=company_data,
            num_queries=25,  # Will be distributed across 6 categories
            models=["chatgpt", "claude"],  # Use free/fast models for testing
            llm_provider="claude",  # Use Claude for query generation (supports structured output)
            progress_callback=progress_callback
        )
        
        # Print final results
        print("\n" + "="*80)
        print("FINAL RESULTS")
        print("="*80)
        print(f"Total Queries: {len(result['queries'])}")
        print(f"Total Responses: {sum(len(r) for r in result['model_responses'].values())}")
        print(f"Visibility Score: {result['visibility_score']:.1f}%")
        print(f"\nCategory Breakdown:")
        
        for category_data in result['analysis_report'].get('category_breakdown', []):
            print(f"  - {category_data['category']}: {category_data['score']:.1f}% ({category_data['queries']} queries, {category_data['mentions']} mentions)")
        
        print(f"\nErrors: {len(result['errors'])}")
        if result['errors']:
            for error in result['errors']:
                print(f"  - {error}")
        
        print("="*80)
        
        # Save results to file
        with open('test_category_batching_result.json', 'w') as f:
            json.dump(result, f, indent=2)
        
        logger.info("✅ Test complete! Results saved to test_category_batching_result.json")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    test_category_batching()
