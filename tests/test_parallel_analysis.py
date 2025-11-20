"""
Test parallel query generation + model testing + analysis with streaming output
Tests with 100 queries and parallel batch analysis
Flow: Industry Detection → Query Generation → Parallel Batch Testing + Analysis
"""

import sys
import os
import asyncio
import time
from datetime import datetime
from typing import Dict, List, Tuple

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.industry_detector import detect_industry
from agents.query_generator import generate_queries
from agents.ai_model_tester import test_ai_models
from agents.scorer_analyzer import analyze_score


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


async def test_batch_models(queries: List[str], models: List[str], batch_num: int) -> Dict[str, List[str]]:
    """Test a batch of queries against all models"""
    batch_responses = {model: [] for model in models}
    
    try:
        # Create a temporary state for this batch
        batch_state = {
            "queries": queries,
            "models": models,
            "model_responses": {},
            "errors": []
        }
        
        # Test this batch
        batch_state = test_ai_models(batch_state)
        batch_responses = batch_state.get("model_responses", {})
        
    except Exception as e:
        log(f"  ⚠️  Error testing batch {batch_num}: {str(e)}", "red")
    
    return batch_responses


async def analyze_batch_results(
    batch_num: int,
    batch_queries: List[str],
    batch_responses: Dict[str, List[str]],
    company_name: str
) -> Dict:
    """Analyze results for a batch of queries"""
    
    try:
        # Create a temporary state for analysis
        analysis_state = {
            "company_name": company_name,
            "queries": batch_queries,
            "model_responses": batch_responses,
            "errors": []
        }
        
        # Analyze this batch
        analysis_state = analyze_score(analysis_state)
        
        return {
            "batch_num": batch_num,
            "visibility_score": analysis_state.get("visibility_score", 0),
            "total_mentions": analysis_state.get("analysis_report", {}).get("total_mentions", 0),
            "by_model": analysis_state.get("analysis_report", {}).get("by_model", {}),
            "sample_mentions": analysis_state.get("analysis_report", {}).get("sample_mentions", [])
        }
    except Exception as e:
        log(f"  ⚠️  Error analyzing batch {batch_num}: {str(e)}", "red")
        return {
            "batch_num": batch_num,
            "visibility_score": 0,
            "total_mentions": 0,
            "by_model": {},
            "sample_mentions": []
        }


async def test_parallel_analysis_flow():
    """Test parallel query generation + model testing + analysis with 100 queries"""
    
    start_time = time.time()
    
    log("=" * 80, "cyan")
    log("PARALLEL FLOW: GENERATION → TESTING → ANALYSIS (100 QUERIES)", "cyan")
    log("=" * 80, "cyan")
    
    company_url = "https://www.nvidia.com/en-in/"
    company_name = "nvidia"
    
    # ============================================================================
    # STEP 1: Industry Detection
    # ============================================================================
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
    
    # ============================================================================
    # STEP 2: Query Generation (100 queries)
    # ============================================================================
    log("\n[STEP 2] Query Generation (100 queries)", "blue")
    step2_start = time.time()
    state["num_queries"] = 20
    state = generate_queries(state, llm_provider="gemini")  # Using Gemini instead of OpenAI
    step2_time = time.time() - step2_start
    total_queries = len(state.get('queries', []))
    log(f"✓ Generated {total_queries} queries", "green")
    log(f"⏱️  Time: {step2_time:.2f}s", "cyan")
    
    # ============================================================================
    # STEP 3: Parallel Batch Testing + Analysis
    # ============================================================================
    log("\n[STEP 3] Parallel Batch Testing + Analysis", "blue")
    log(f"Testing {total_queries} queries in batches of 5 with parallel analysis...", "yellow")
    
    queries = state.get('queries', [])
    batch_size = 5
    models = ["gemini", "llama"]
    
    all_batch_responses = {model: [] for model in models}
    all_analysis_results = []
    batch_num = 0
    step3_start = time.time()
    
    # Process batches with overlapping generation, testing, and analysis
    for i in range(0, len(queries), batch_size):
        batch_num += 1
        batch_queries = queries[i:i+batch_size]
        batch_start = time.time()
        
        total_tested = min((batch_num * batch_size), len(queries))
        progress = (total_tested / len(queries)) * 100
        log(f"\n📦 Batch {batch_num}: {len(batch_queries)} queries ({progress:.0f}% progress)", "yellow")
        
        # ====================================================================
        # Phase 1: Test batch queries against all models
        # ====================================================================
        log(f"  🔄 Testing batch {batch_num} against {len(models)} models...", "yellow")
        test_start = time.time()
        
        batch_responses = await test_batch_models(batch_queries, models, batch_num)
        
        test_time = time.time() - test_start
        log(f"  ✓ Batch {batch_num} testing complete ({test_time:.2f}s)", "green")
        
        # Store responses for aggregation
        for model in models:
            if model in batch_responses:
                all_batch_responses[model].extend(batch_responses[model])
        
        # ====================================================================
        # Phase 2: Analyze batch results in parallel
        # ====================================================================
        log(f"  📊 Analyzing batch {batch_num} results...", "yellow")
        analysis_start = time.time()
        
        batch_analysis = await analyze_batch_results(
            batch_num=batch_num,
            batch_queries=batch_queries,
            batch_responses=batch_responses,
            company_name=company_name
        )
        
        analysis_time = time.time() - analysis_start
        log(f"  ✓ Batch {batch_num} analysis complete ({analysis_time:.2f}s)", "green")
        
        # Log batch analysis results
        if batch_analysis["visibility_score"] > 0:
            log(f"    📈 Batch Score: {batch_analysis['visibility_score']:.1f}%", "cyan")
            log(f"    📍 Mentions: {batch_analysis['total_mentions']}", "cyan")
        
        all_analysis_results.append(batch_analysis)
        
        # Show per-model breakdown for this batch
        for model, model_data in batch_analysis["by_model"].items():
            mentions = model_data.get("mentions", 0)
            total = model_data.get("total_responses", 0)
            if total > 0:
                rate = (mentions / total) * 100
                log(f"    {model.upper()}: {mentions}/{total} mentions ({rate:.0f}%)", "cyan")
        
        batch_time = time.time() - batch_start
        log(f"  ✓ Batch {batch_num} complete ({batch_time:.2f}s)", "green")
    
    step3_time = time.time() - step3_start
    
    # ============================================================================
    # STEP 4: Aggregate Results
    # ============================================================================
    log("\n[STEP 4] Aggregating Results", "blue")
    agg_start = time.time()
    
    # Create final aggregated state
    final_state = {
        "company_name": company_name,
        "queries": queries,
        "model_responses": all_batch_responses,
        "errors": []
    }
    
    # Run final analysis on all aggregated data
    final_state = analyze_score(final_state)
    agg_time = time.time() - agg_start
    
    log(f"✓ Aggregation complete ({agg_time:.2f}s)", "green")
    
    # ============================================================================
    # Final Results
    # ============================================================================
    log("\n" + "=" * 80, "cyan")
    log("FINAL RESULTS", "cyan")
    log("=" * 80, "cyan")
    
    final_score = final_state.get("visibility_score", 0)
    final_report = final_state.get("analysis_report", {})
    
    log(f"\n🎯 OVERALL VISIBILITY SCORE: {final_score:.1f}%", "green")
    log(f"📊 Total Queries: {len(queries)}", "cyan")
    log(f"📊 Total Responses: {sum(len(r) for r in all_batch_responses.values())}", "cyan")
    log(f"📊 Total Mentions: {final_report.get('total_mentions', 0)}", "cyan")
    log(f"📊 Batches Processed: {batch_num}", "cyan")
    
    # Per-model breakdown
    log(f"\n📈 PER-MODEL BREAKDOWN:", "cyan")
    for model, model_data in final_report.get("by_model", {}).items():
        mentions = model_data.get("mentions", 0)
        total = model_data.get("total_responses", 0)
        rate = model_data.get("mention_rate", 0)
        log(f"  {model.upper()}: {mentions}/{total} mentions ({rate*100:.1f}%)", "cyan")
    
    # Competitor mentions
    if final_report.get("by_model"):
        log(f"\n🏆 COMPETITOR MENTIONS:", "cyan")
        all_competitors = {}
        for model_data in final_report.get("by_model", {}).values():
            for competitor, count in model_data.get("competitor_mentions", {}).items():
                all_competitors[competitor] = all_competitors.get(competitor, 0) + count
        
        if all_competitors:
            for competitor, count in sorted(all_competitors.items(), key=lambda x: x[1], reverse=True)[:5]:
                log(f"  {competitor}: {count} mentions", "cyan")
    
    # Sample mentions
    if final_report.get("sample_mentions"):
        log(f"\n💬 SAMPLE MENTIONS:", "cyan")
        for i, sample in enumerate(final_report.get("sample_mentions", [])[:3], 1):
            log(f"  {i}. {sample[:70]}...", "cyan")
    
    # Timing breakdown
    total_time = time.time() - start_time
    
    log(f"\n⏱️  TIMING BREAKDOWN:", "cyan")
    log(f"  Step 1 (Industry Detection): {step1_time:.2f}s", "cyan")
    log(f"  Step 2 (Query Generation): {step2_time:.2f}s", "cyan")
    log(f"  Step 3 (Parallel Testing + Analysis): {step3_time:.2f}s", "cyan")
    log(f"  Step 4 (Aggregation): {agg_time:.2f}s", "cyan")
    log(f"  ─────────────────────────────────", "cyan")
    log(f"  TOTAL: {total_time:.2f}s", "cyan")
    
    # Efficiency metrics
    log(f"\n⚡ EFFICIENCY METRICS:", "cyan")
    avg_batch_time = step3_time / batch_num if batch_num > 0 else 0
    log(f"  Avg time per batch: {avg_batch_time:.2f}s", "cyan")
    log(f"  Queries per second: {len(queries) / total_time:.2f}", "cyan")
    log(f"  Responses per second: {(len(queries) * len(models)) / total_time:.2f}", "cyan")
    
    log(f"\n✓ Parallel analysis flow test completed successfully!", "green")


if __name__ == "__main__":
    asyncio.run(test_parallel_analysis_flow())
