# tests/test_model_tester.py
import sys
import os

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.industry_detector import detect_industry
from agents.query_generator import generate_queries
from agents.ai_model_tester import test_ai_models

def main():
    print("=" * 60)
    print("Testing Model Tester with HelloFresh")
    print("=" * 60)
    
    # Use cached data (instant)
    state = {
        "company_url": "https://hellofresh.com",
        "company_name": "HelloFresh",
        "errors": []
    }
    
    # Step 1: Industry (cached - instant)
    print("\n[Step 1] Running industry detection...")
    state = detect_industry(state)
    print(f"✓ Industry: {state.get('industry')}")
    print(f"✓ Company: {state.get('company_name')}")
    print(f"✓ Competitors: {len(state.get('competitors', []))}")
    
    # Step 2: Queries (cached - instant)
    print("\n[Step 2] Generating queries...")
    state = generate_queries(state)
    total_queries = len(state.get('queries', []))
    print(f"✓ Generated {total_queries} queries")
    
    # Limit to 5 for testing
    state["queries"] = state["queries"][:5]
    print(f"✓ Testing with first 5 queries")
    
    # Step 3: Model Tester (NEW - will make real API calls)
    print("\n[Step 3] Testing AI models...")
    state["models"] = ["chatgpt", "llama"]  # Test ChatGPT + Llama (fast & reliable)
    # Available: ["chatgpt", "gemini", "claude", "llama", "grok", "deepseek"]
    print(f"Models to test: {state['models']}")
    
    state = test_ai_models(state)
    
    # Check results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Queries tested: {len(state['queries'])}")
    print(f"Models tested: {list(state['model_responses'].keys())}")
    
    for model, responses in state['model_responses'].items():
        print(f"\n{model.upper()}:")
        print(f"  Total responses: {len(responses)}")
        if responses and responses[0]:
            print(f"  Sample response: {responses[0][:150]}...")
    
    if state.get('errors'):
        print(f"\n⚠️  Errors: {len(state['errors'])}")
        for error in state['errors'][:3]:
            print(f"  - {error}")

if __name__ == "__main__":
    main()
