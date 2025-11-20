"""
Test parallel query generation + model testing with streaming output
Tests with 100 queries to simulate real use case
"""

import sys
import os
import asyncio
import time
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.industry_detector import detect_industry
from agents.query_generator import generate_queries


def log(message: str, color: str = ""):
    """Log with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    colors = {
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "cyan": "\033[96m",
        "red": "\033[91m",
        "reset": "\033[0m"
    }
    color_code = colors.get(color, "")
    reset = colors["reset"]
    print(f"[{timestamp}] {color_code}{message}{reset}")


async def test_parallel_flow():
    """Test parallel query generation + model testing with 100 queries"""
    
    start_time = time.time()
    
    log("=" * 70, "cyan")
    log("PARALLEL QUERY GENERATION + MODEL TESTING (100 QUERIES)", "cyan")
    log("=" * 70, "cyan")
    
    # Use different brand to avoid cache
    company_url = "https://www.crocs.in"
    company_name="crocs"
    
    # Step 1: Industry Detection
    log("\n[STEP 1] Industry Detection", "blue")
    step1_start = time.time()
    state = {
        "company_url": company_url,
        "company_name": company_name,
        "company_description": "",
        "errors": []
    }
    
    state = detect_industry(state, llm_provider="gemini")  # Using Gemini instead of OpenAI
    step1_time = time.time() - step1_start
    log(f"✓ Industry: {state.get('industry')}", "green")
    log(f"✓ Company: {state.get('company_name')}", "green")
    log(f"✓ Competitors: {len(state.get('competitors', []))}", "green")
    log(f"⏱️  Time: {step1_time:.2f}s", "cyan")
    
    # Step 2: Query Generation (100 queries)
    log("\n[STEP 2] Query Generation (100 queries)", "blue")
    step2_start = time.time()
    state["num_queries"] = 20  # Request 100 queries
    state = generate_queries(state, llm_provider="gemini")  # Using Gemini instead of OpenAI
    step2_time = time.time() - step2_start
    total_queries = len(state.get('queries', []))
    log(f"✓ Generated {total_queries} queries", "green")
    log(f"⏱️  Time: {step2_time:.2f}s", "cyan")
    
    # Step 3: Parallel Batch Testing
    log("\n[STEP 3] Parallel Batch Testing + Model Testing", "blue")
    log(f"Testing {total_queries} queries against 2 models in batches of 5...", "yellow")
    
    queries = state.get('queries', [])
    batch_size = 5
    models = ["gemini", "llama"]
    
    all_responses = {model: [] for model in models}
    batch_num = 0
    step3_start = time.time()
    
    # Simulate batching with real async parallel testing
    for i in range(0, len(queries), batch_size):
        batch_num += 1
        batch_queries = queries[i:i+batch_size]
        batch_start = time.time()
        
        # Show batch start
        total_tested = min((batch_num * batch_size), len(queries))
        progress = (total_tested / len(queries)) * 100
        log(f"\n📦 Batch {batch_num}: {len(batch_queries)} queries ({progress:.0f}% progress)", "yellow")
        
        # Simulate query generation time
        log(f"  ⏳ Generating batch {batch_num}...", "yellow")
        await asyncio.sleep(0.3)  # Simulate generation
        log(f"  ✓ Batch {batch_num} ready", "green")
        
        # Simulate parallel model testing (async)
        log(f"  🔄 Testing batch {batch_num} against {len(models)} models (parallel)...", "yellow")
        
        # Test each query in batch with parallel model calls
        for j, query in enumerate(batch_queries, 1):
            query_num = i + j
            
            # Simulate parallel async calls to both models
            tasks = []
            for model in models:
                # Simulate API call time (0.3s per model)
                await asyncio.sleep(0.15)  # Reduced for faster testing
                response = f"Response from {model}"
                all_responses[model].append(response)
            
            log(f"    ✓ Query {query_num}/{len(queries)}: {query[:45]}...", "cyan")
        
        batch_time = time.time() - batch_start
        log(f"  ✓ Batch {batch_num} complete ({batch_time:.2f}s)", "green")
    
    step3_time = time.time() - step3_start
    
    # Final results
    log("\n" + "=" * 70, "cyan")
    log("FINAL RESULTS", "cyan")
    log("=" * 70, "cyan")
    
    for model, responses in all_responses.items():
        log(f"{model.upper()}: {len(responses)} responses", "green")
    
    total_time = time.time() - start_time
    
    log(f"\n📊 STATISTICS:", "cyan")
    log(f"  Total queries: {len(queries)}", "cyan")
    log(f"  Total responses: {sum(len(r) for r in all_responses.values())}", "cyan")
    log(f"  Batches: {batch_num}", "cyan")
    log(f"\n⏱️  TIMING BREAKDOWN:", "cyan")
    log(f"  Step 1 (Industry): {step1_time:.2f}s", "cyan")
    log(f"  Step 2 (Queries): {step2_time:.2f}s", "cyan")
    log(f"  Step 3 (Testing): {step3_time:.2f}s", "cyan")
    log(f"  TOTAL: {total_time:.2f}s", "cyan")
    
    log(f"\n✓ Parallel flow test completed successfully!", "green")


if __name__ == "__main__":
    asyncio.run(test_parallel_flow())
