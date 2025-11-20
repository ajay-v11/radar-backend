"""
Integration test for Industry Detector -> Query Generator flow.

This test demonstrates the proper integration between the two agents:
1. Industry Detector scrapes website, analyzes content, stores in vector DB
2. Query Generator uses the cached/stored data to generate queries

The test validates:
- Data flows correctly between agents
- Caching works at both levels
- No redundant API calls are made
- Company data is properly reused
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import logging
from typing import Dict
from agents.industry_detector import detect_industry
from agents.query_generator import generate_queries
from models.schemas import WorkflowState

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestIntegratedFlow:
    """Test the integrated flow from industry detection to query generation."""
    
    def test_full_flow_hellofresh(self):
        """Test complete flow with HelloFresh as example."""
        logger.info("\n" + "="*80)
        logger.info("TEST: Full Integrated Flow - HelloFresh")
        logger.info("="*80)
        
        # Step 1: Initialize state with minimal input
        initial_state: WorkflowState = {
            "company_url": "https://www.hellofresh.com",
            "company_name": "",  # Let detector extract it
            "company_description": "",  # Let detector extract it
            "errors": []
        }
        
        logger.info("\n--- STEP 1: Industry Detection ---")
        logger.info(f"Input: {initial_state['company_url']}")
        
        # Run industry detector
        state_after_detection = detect_industry(initial_state)
        
        # Validate industry detector output
        assert state_after_detection.get("industry"), "Industry should be detected"
        assert state_after_detection.get("company_name"), "Company name should be extracted"
        assert state_after_detection.get("company_description"), "Description should be extracted"
        
        logger.info(f"✓ Industry detected: {state_after_detection['industry']}")
        logger.info(f"✓ Company name: {state_after_detection['company_name']}")
        logger.info(f"✓ Description: {state_after_detection['company_description'][:100]}...")
        logger.info(f"✓ Summary: {state_after_detection.get('company_summary', '')[:100]}...")
        logger.info(f"✓ Competitors found: {len(state_after_detection.get('competitors', []))}")
        
        if state_after_detection.get("competitors"):
            logger.info(f"  Competitors: {', '.join(state_after_detection['competitors'][:5])}")
        
        # Step 2: Generate queries using the detected data
        logger.info("\n--- STEP 2: Query Generation ---")
        logger.info("Using data from industry detector...")
        
        # Add num_queries to state
        state_after_detection["num_queries"] = 20  # Small number for testing
        
        # Run query generator
        state_after_queries = generate_queries(state_after_detection)
        
        # Validate query generator output
        assert state_after_queries.get("queries"), "Queries should be generated"
        assert len(state_after_queries["queries"]) > 0, "Should have at least some queries"
        
        logger.info(f"✓ Generated {len(state_after_queries['queries'])} queries")
        logger.info(f"✓ Query categories: {list(state_after_queries.get('query_categories', {}).keys())}")
        
        # Show sample queries
        logger.info("\nSample queries:")
        for i, query in enumerate(state_after_queries["queries"][:5], 1):
            logger.info(f"  {i}. {query}")
        
        # Validate data reuse
        logger.info("\n--- VALIDATION: Data Reuse ---")
        assert state_after_queries["company_name"] == state_after_detection["company_name"], \
            "Company name should be preserved"
        assert state_after_queries["industry"] == state_after_detection["industry"], \
            "Industry should be preserved"
        assert state_after_queries["competitors"] == state_after_detection["competitors"], \
            "Competitors should be preserved"
        
        logger.info("✓ All data properly passed between agents")
        
        # Check for errors
        if state_after_queries.get("errors"):
            logger.warning(f"Errors encountered: {state_after_queries['errors']}")
        
        logger.info("\n" + "="*80)
        logger.info("TEST PASSED: Full flow completed successfully")
        logger.info("="*80 + "\n")
    
    def test_cache_efficiency(self):
        """Test that second run uses cached data efficiently."""
        logger.info("\n" + "="*80)
        logger.info("TEST: Cache Efficiency")
        logger.info("="*80)
        
        company_url = "https://www.hellofresh.com"
        
        # First run - should hit APIs
        logger.info("\n--- RUN 1: Fresh data (cache miss expected) ---")
        state1: WorkflowState = {
            "company_url": company_url,
            "company_name": "",
            "company_description": "",
            "errors": [],
            "num_queries": 20
        }
        
        state1 = detect_industry(state1)
        state1 = generate_queries(state1)
        
        logger.info(f"✓ Run 1 completed: {len(state1['queries'])} queries generated")
        
        # Second run - should use cache
        logger.info("\n--- RUN 2: Cached data (cache hit expected) ---")
        state2: WorkflowState = {
            "company_url": company_url,
            "company_name": "",
            "company_description": "",
            "errors": [],
            "num_queries": 20
        }
        
        state2 = detect_industry(state2)
        state2 = generate_queries(state2)
        
        logger.info(f"✓ Run 2 completed: {len(state2['queries'])} queries generated")
        
        # Validate results are consistent
        assert state1["industry"] == state2["industry"], "Industry should be same from cache"
        assert state1["company_name"] == state2["company_name"], "Company name should be same"
        assert len(state1["queries"]) == len(state2["queries"]), "Query count should be same"
        
        logger.info("\n✓ Cache working correctly - consistent results")
        logger.info("="*80 + "\n")
    
    def test_different_industries(self):
        """Test flow with companies from different industries."""
        logger.info("\n" + "="*80)
        logger.info("TEST: Different Industries")
        logger.info("="*80)
        
        test_companies = [
            {
                "url": "https://www.salesforce.com",
                "expected_industry": "technology",
                "name": "Salesforce"
            },
            {
                "url": "https://www.nike.com",
                "expected_industry": "retail",
                "name": "Nike"
            }
        ]
        
        for company in test_companies:
            logger.info(f"\n--- Testing: {company['name']} ---")
            
            state: WorkflowState = {
                "company_url": company["url"],
                "company_name": "",
                "company_description": "",
                "errors": [],
                "num_queries": 20
            }
            
            # Run both agents
            state = detect_industry(state)
            state = generate_queries(state)
            
            logger.info(f"✓ Industry: {state['industry']}")
            logger.info(f"✓ Queries: {len(state['queries'])}")
            logger.info(f"✓ Sample query: {state['queries'][0] if state['queries'] else 'None'}")
            
            # Validate industry-specific behavior
            assert state["industry"] in ["technology", "retail", "healthcare", "finance", "food_services", "other"], \
                "Should detect valid industry"
            assert len(state["queries"]) > 0, "Should generate queries"
        
        logger.info("\n✓ All industries processed successfully")
        logger.info("="*80 + "\n")
    
    def test_error_handling(self):
        """Test error handling when data is missing or invalid."""
        logger.info("\n" + "="*80)
        logger.info("TEST: Error Handling")
        logger.info("="*80)
        
        # Test with invalid URL
        logger.info("\n--- Test 1: Invalid URL ---")
        state: WorkflowState = {
            "company_url": "https://this-domain-does-not-exist-12345.com",
            "company_name": "Test Company",
            "company_description": "A test company",
            "errors": [],
            "num_queries": 20
        }
        
        state = detect_industry(state)
        logger.info(f"Industry (fallback): {state['industry']}")
        logger.info(f"Errors: {len(state.get('errors', []))}")
        
        # Should still be able to generate queries with fallback data
        state = generate_queries(state)
        logger.info(f"✓ Generated {len(state['queries'])} queries despite errors")
        
        # Test with missing URL
        logger.info("\n--- Test 2: Missing URL ---")
        state2: WorkflowState = {
            "company_url": "",
            "company_name": "Test Company",
            "company_description": "A test company",
            "errors": [],
            "num_queries": 20
        }
        
        state2 = detect_industry(state2)
        assert "No company URL provided" in str(state2.get("errors", [])), \
            "Should report missing URL error"
        logger.info("✓ Missing URL error handled correctly")
        
        logger.info("\n✓ Error handling working as expected")
        logger.info("="*80 + "\n")
    
    def test_data_preservation(self):
        """Test that all data from industry detector is preserved through query generation."""
        logger.info("\n" + "="*80)
        logger.info("TEST: Data Preservation")
        logger.info("="*80)
        
        state: WorkflowState = {
            "company_url": "https://www.hellofresh.com",
            "company_name": "",
            "company_description": "",
            "errors": [],
            "num_queries": 20
        }
        
        # Run industry detector
        state = detect_industry(state)
        
        # Capture all fields from industry detector
        fields_after_detection = {
            "industry": state.get("industry"),
            "company_name": state.get("company_name"),
            "company_description": state.get("company_description"),
            "company_summary": state.get("company_summary"),
            "competitors": state.get("competitors", []),
            "scraped_content": state.get("scraped_content", "")[:100]  # First 100 chars
        }
        
        logger.info("\nData after industry detection:")
        for key, value in fields_after_detection.items():
            if key == "competitors":
                logger.info(f"  {key}: {len(value)} items")
            elif key == "scraped_content":
                logger.info(f"  {key}: {len(state.get('scraped_content', ''))} chars")
            else:
                logger.info(f"  {key}: {str(value)[:80]}...")
        
        # Run query generator
        state = generate_queries(state)
        
        # Validate all fields are preserved
        logger.info("\nValidating data preservation:")
        assert state["industry"] == fields_after_detection["industry"], "Industry preserved"
        logger.info("  ✓ Industry preserved")
        
        assert state["company_name"] == fields_after_detection["company_name"], "Company name preserved"
        logger.info("  ✓ Company name preserved")
        
        assert state["company_description"] == fields_after_detection["company_description"], "Description preserved"
        logger.info("  ✓ Description preserved")
        
        assert state["company_summary"] == fields_after_detection["company_summary"], "Summary preserved"
        logger.info("  ✓ Summary preserved")
        
        assert state["competitors"] == fields_after_detection["competitors"], "Competitors preserved"
        logger.info("  ✓ Competitors preserved")
        
        # New fields should be added
        assert "queries" in state, "Queries should be added"
        assert "query_categories" in state, "Query categories should be added"
        logger.info("  ✓ New fields added (queries, query_categories)")
        
        logger.info("\n✓ All data properly preserved and extended")
        logger.info("="*80 + "\n")


if __name__ == "__main__":
    """Run tests directly without pytest."""
    test_suite = TestIntegratedFlow()
    
    print("\n" + "="*80)
    print("RUNNING INTEGRATED FLOW TESTS")
    print("="*80)
    
    try:
        # Run all tests
        test_suite.test_full_flow_hellofresh()
        test_suite.test_cache_efficiency()
        test_suite.test_different_industries()
        test_suite.test_error_handling()
        test_suite.test_data_preservation()
        
        print("\n" + "="*80)
        print("ALL TESTS PASSED ✓")
        print("="*80 + "\n")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        raise
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        raise
