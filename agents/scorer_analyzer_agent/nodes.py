"""
Node functions for the scorer analyzer LangGraph workflow.
"""

import logging
from typing import Dict, Any

from agents.scorer_analyzer_agent.models import ScorerAnalyzerState
from agents.scorer_analyzer_agent.utils import (
    build_query_category_map,
    analyze_single_response,
    build_competitor_rankings
)

logger = logging.getLogger(__name__)


def initialize_analysis(state: ScorerAnalyzerState) -> ScorerAnalyzerState:
    """Node: Initialize analysis structures."""
    logger.info("🔍 Initializing visibility analysis...")
    
    queries = state.get("queries", [])
    query_categories = state.get("query_categories", {})
    
    # Build query-to-category mapping
    query_to_category = build_query_category_map(queries, query_categories)
    
    state["query_to_category"] = query_to_category
    state["category_stats"] = {}
    state["competitor_stats"] = {}
    state["query_log"] = []
    
    logger.info(f"Analyzing {len(queries)} queries across categories")
    
    return state


def analyze_responses(state: ScorerAnalyzerState) -> ScorerAnalyzerState:
    """Node: Analyze all responses for mentions and rankings."""
    logger.info("📊 Analyzing model responses...")
    
    company_name = state.get("company_name", "")
    queries = state.get("queries", [])
    model_responses = state.get("model_responses", {})
    query_to_category = state.get("query_to_category", {})
    competitors = state.get("competitors", [])
    errors = state.get("errors", [])
    
    # Get competitor matcher for semantic search
    try:
        from utils.competitor_matcher import get_competitor_matcher
        matcher = get_competitor_matcher()
        use_semantic = True
    except Exception as e:
        logger.warning(f"Competitor matcher unavailable: {e}")
        matcher = None
        use_semantic = False
    
    # Initialize tracking structures
    query_log = []
    category_stats = {}
    competitor_stats = {}
    sample_mentions = []
    total_mentions = 0
    total_responses = 0
    
    # Process each query across all models
    for query_idx, query in enumerate(queries):
        query_category = query_to_category.get(query_idx, "unknown")
        
        # Initialize query log entry
        query_entry = {
            "query": query,
            "category": query_category,
            "results": {}
        }
        
        # Process each model's response for this query
        for model_name, responses in model_responses.items():
            if query_idx >= len(responses):
                continue
            
            response = responses[query_idx]
            
            # Analyze this specific response
            analysis = analyze_single_response(
                response=response,
                company_name=company_name,
                competitors=competitors,
                matcher=matcher if use_semantic else None
            )
            
            # Store in query log
            query_entry["results"][model_name] = {
                "mentioned": analysis["company_mentioned"],
                "rank": analysis["rank"],
                "competitors_mentioned": analysis["competitors_found"],
                "response_preview": response[:200] + "..." if len(response) > 200 else response
            }
            
            # Update counters
            if analysis["company_mentioned"]:
                total_mentions += 1
                
                # Collect sample mentions (up to 5 total)
                if len(sample_mentions) < 5:
                    query_text = query[:50] + "..." if len(query) > 50 else query
                    comp_info = f" (with {', '.join(analysis['competitors_found'][:2])})" if analysis['competitors_found'] else ""
                    rank_info = f" at rank {analysis['rank']}" if analysis['rank'] else ""
                    sample = f"Query: '{query_text}' -> {model_name.capitalize()} mentioned company{rank_info}{comp_info}"
                    sample_mentions.append(sample)
            
            # Update category stats
            if query_category not in category_stats:
                category_stats[query_category] = {
                    "total_queries": 0,
                    "total_responses": 0,
                    "mentions": 0,
                    "by_model": {}
                }
            
            category_stats[query_category]["total_responses"] += 1
            if analysis["company_mentioned"]:
                category_stats[query_category]["mentions"] += 1
            
            # Per-model category stats
            if model_name not in category_stats[query_category]["by_model"]:
                category_stats[query_category]["by_model"][model_name] = {
                    "mentions": 0,
                    "total": 0
                }
            category_stats[query_category]["by_model"][model_name]["total"] += 1
            if analysis["company_mentioned"]:
                category_stats[query_category]["by_model"][model_name]["mentions"] += 1
            
            # Update competitor stats
            for comp in analysis["competitors_found"]:
                if comp not in competitor_stats:
                    competitor_stats[comp] = {
                        "total_mentions": 0,
                        "by_category": {},
                        "by_model": {},
                        "ranks": []
                    }
                
                competitor_stats[comp]["total_mentions"] += 1
                
                # By category
                if query_category not in competitor_stats[comp]["by_category"]:
                    competitor_stats[comp]["by_category"][query_category] = 0
                competitor_stats[comp]["by_category"][query_category] += 1
                
                # By model
                if model_name not in competitor_stats[comp]["by_model"]:
                    competitor_stats[comp]["by_model"][model_name] = 0
                competitor_stats[comp]["by_model"][model_name] += 1
            
            total_responses += 1
        
        # Add query entry to log
        query_log.append(query_entry)
        
        # Update category query count
        if query_category in category_stats:
            category_stats[query_category]["total_queries"] += 1
    
    # Store in state
    state["query_log"] = query_log
    state["category_stats"] = category_stats
    state["competitor_stats"] = competitor_stats
    state["total_mentions"] = total_mentions
    state["total_responses"] = total_responses
    state["sample_mentions"] = sample_mentions
    state["errors"] = errors
    
    logger.info(f"✓ Analysis complete: {total_mentions} mentions in {total_responses} responses")
    
    return state


def calculate_score(state: ScorerAnalyzerState) -> ScorerAnalyzerState:
    """Node: Calculate visibility score and build report."""
    logger.info("🎯 Calculating visibility score...")
    
    company_name = state.get("company_name", "")
    queries = state.get("queries", [])
    model_responses = state.get("model_responses", {})
    query_categories = state.get("query_categories", {})
    category_stats = state.get("category_stats", {})
    competitor_stats = state.get("competitor_stats", {})
    query_log = state.get("query_log", [])
    sample_mentions = state.get("sample_mentions", [])
    total_mentions = state.get("total_mentions", 0)
    total_responses = state.get("total_responses", 0)
    
    num_queries = len(queries)
    num_models = len(model_responses)
    
    # Calculate overall visibility score
    if num_queries > 0 and num_models > 0:
        visibility_score = (total_mentions / (num_queries * num_models)) * 100
    else:
        visibility_score = 0.0
    
    # Calculate overall mention rate
    mention_rate = total_mentions / total_responses if total_responses > 0 else 0.0
    
    # Calculate per-model results
    by_model_results = {}
    for model_name, responses in model_responses.items():
        model_mentions = sum(
            1 for entry in query_log
            if entry["results"].get(model_name, {}).get("mentioned", False)
        )
        
        model_competitor_mentions = {}
        for entry in query_log:
            model_result = entry["results"].get(model_name, {})
            for comp in model_result.get("competitors_mentioned", []):
                model_competitor_mentions[comp] = model_competitor_mentions.get(comp, 0) + 1
        
        mention_rate_model = model_mentions / len(responses) if len(responses) > 0 else 0.0
        
        by_model_results[model_name] = {
            "mentions": model_mentions,
            "total_responses": len(responses),
            "mention_rate": round(mention_rate_model, 4),
            "competitor_mentions": model_competitor_mentions
        }
    
    # Build category breakdown
    by_category = {}
    for category_key, stats in category_stats.items():
        total_cat_responses = stats["total_responses"]
        cat_mentions = stats["mentions"]
        
        # Get category name from query_categories
        category_name = category_key
        if query_categories and category_key in query_categories:
            category_name = query_categories[category_key].get("name", category_key)
        
        by_category[category_key] = {
            "name": category_name,
            "total_queries": stats["total_queries"],
            "total_responses": total_cat_responses,
            "mentions": cat_mentions,
            "visibility": round((cat_mentions / total_cat_responses * 100), 2) if total_cat_responses > 0 else 0.0,
            "mention_rate": round((cat_mentions / total_cat_responses), 4) if total_cat_responses > 0 else 0.0,
            "by_model": stats["by_model"]
        }
    
    # Build competitor rankings
    competitor_rankings = build_competitor_rankings(
        competitor_stats,
        num_queries,
        num_models
    )
    
    # Generate detailed analysis report
    analysis_report = {
        "visibility_score": round(visibility_score, 2),
        "total_queries": num_queries,
        "total_responses": total_responses,
        "total_mentions": total_mentions,
        "mention_rate": round(mention_rate, 4),
        "by_model": by_model_results,
        "by_category": by_category,
        "competitor_rankings": competitor_rankings,
        "query_log": query_log,
        "sample_mentions": sample_mentions
    }
    
    state["visibility_score"] = round(visibility_score, 2)
    state["analysis_report"] = analysis_report
    
    logger.info(f"✓ Visibility score: {round(visibility_score, 2)}%")
    
    return state


def finalize(state: ScorerAnalyzerState) -> ScorerAnalyzerState:
    """Node: Finalize and mark as completed."""
    logger.info("✅ Scorer analysis workflow complete")
    state["completed"] = True
    return state
