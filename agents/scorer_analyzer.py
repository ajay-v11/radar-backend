"""
Scorer Analyzer Agent

This agent calculates the visibility score by analyzing AI model responses
for mentions of the company name and competitors using semantic matching.

Enhanced with:
- Complete query log (all queries with detailed results)
- Breakdown by category (per-category visibility scores)
- Competitor rankings (overall and per-category)
- Rank/position tracking (where brand appears in responses)
"""

from typing import Dict, List, Any, Tuple, Optional
from models.schemas import WorkflowState
from utils.competitor_matcher import get_competitor_matcher
import logging
import re

logger = logging.getLogger(__name__)


def analyze_score(state: WorkflowState) -> WorkflowState:
    """
    Calculate visibility score based on company mentions in AI model responses.
    
    Enhanced with:
    - Complete query log (all queries with detailed results)
    - Breakdown by category (per-category visibility scores)
    - Competitor rankings (overall and per-category)
    - Rank/position tracking (where brand appears in responses)
    
    The visibility score is calculated as:
    (total_mentions / (num_queries * num_models)) * 100
    
    Args:
        state: WorkflowState containing company_name, queries, and model_responses
        
    Returns:
        Updated WorkflowState with visibility_score and analysis_report populated
        
    Requirements: 6.1, 6.2, 6.3, 6.4
    """
    company_name = state.get("company_name", "")
    queries = state.get("queries", [])
    model_responses = state.get("model_responses", {})
    query_categories = state.get("query_categories", {})
    competitors = state.get("competitors", [])
    
    # Build query-to-category mapping
    query_to_category = _build_query_category_map(queries, query_categories)
    
    # Initialize data structures
    total_mentions = 0
    total_responses = 0
    by_model_results: Dict[str, Dict[str, Any]] = {}
    sample_mentions: List[str] = []
    
    # NEW: Complete query log
    query_log: List[Dict[str, Any]] = []
    
    # NEW: Category tracking
    category_stats: Dict[str, Dict[str, Any]] = {}
    
    # NEW: Competitor tracking (overall)
    competitor_overall_stats: Dict[str, Dict[str, Any]] = {}
    
    # Get competitor matcher for semantic search
    try:
        matcher = get_competitor_matcher()
        use_semantic = True
    except Exception as e:
        logger.warning(f"Competitor matcher unavailable: {e}")
        use_semantic = False
    
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
            analysis = _analyze_single_response(
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
                if comp not in competitor_overall_stats:
                    competitor_overall_stats[comp] = {
                        "total_mentions": 0,
                        "by_category": {},
                        "by_model": {},
                        "ranks": []
                    }
                
                competitor_overall_stats[comp]["total_mentions"] += 1
                
                # By category
                if query_category not in competitor_overall_stats[comp]["by_category"]:
                    competitor_overall_stats[comp]["by_category"][query_category] = 0
                competitor_overall_stats[comp]["by_category"][query_category] += 1
                
                # By model
                if model_name not in competitor_overall_stats[comp]["by_model"]:
                    competitor_overall_stats[comp]["by_model"][model_name] = 0
                competitor_overall_stats[comp]["by_model"][model_name] += 1
            
            total_responses += 1
        
        # Add query entry to log
        query_log.append(query_entry)
        
        # Update category query count
        if query_category in category_stats:
            category_stats[query_category]["total_queries"] += 1
    
    # Calculate per-model results
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
        
        mention_rate = model_mentions / len(responses) if len(responses) > 0 else 0.0
        
        by_model_results[model_name] = {
            "mentions": model_mentions,
            "total_responses": len(responses),
            "mention_rate": round(mention_rate, 4),
            "competitor_mentions": model_competitor_mentions
        }
    
    # Calculate overall visibility score
    num_queries = len(queries)
    num_models = len(model_responses)
    
    if num_queries > 0 and num_models > 0:
        visibility_score = (total_mentions / (num_queries * num_models)) * 100
    else:
        visibility_score = 0.0
    
    # Calculate overall mention rate
    mention_rate = total_mentions / total_responses if total_responses > 0 else 0.0
    
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
    competitor_rankings = _build_competitor_rankings(
        competitor_overall_stats,
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
    
    # Update state with results
    state["visibility_score"] = round(visibility_score, 2)
    state["analysis_report"] = analysis_report
    
    return state




def _build_query_category_map(queries: List[str], query_categories: Dict) -> Dict[int, str]:
    """
    Build a mapping from query index to category key.
    
    Args:
        queries: List of all queries
        query_categories: Dict of categories with their queries
        
    Returns:
        Dict mapping query index to category key
    """
    query_to_category = {}
    
    if not query_categories:
        return query_to_category
    
    # Build reverse mapping
    for category_key, category_data in query_categories.items():
        category_queries = category_data.get("queries", [])
        for cat_query in category_queries:
            # Find this query in the main queries list
            try:
                idx = queries.index(cat_query)
                query_to_category[idx] = category_key
            except ValueError:
                # Query not found in main list (shouldn't happen)
                continue
    
    return query_to_category


def _analyze_single_response(
    response: str,
    company_name: str,
    competitors: List[str],
    matcher: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Analyze a single AI model response for company and competitor mentions.
    
    Returns detailed analysis including:
    - Whether company is mentioned
    - Rank/position of company
    - Which competitors are mentioned
    
    Args:
        response: AI model response text
        company_name: Company name to search for
        competitors: List of competitor names
        matcher: Optional CompetitorMatcher instance for semantic search
        
    Returns:
        Dict with analysis results
    """
    if not response:
        return {
            "company_mentioned": False,
            "rank": None,
            "competitors_found": []
        }
    
    # Normalize company name for matching
    company_name_lower = company_name.lower().strip()
    company_name_variations = [
        company_name_lower,
        company_name_lower.replace(" ", ""),
        company_name_lower.replace(" ", "-"),
    ]
    
    response_lower = response.lower()
    
    # 1. Check if company is mentioned (exact matching)
    company_mentioned = any(var in response_lower for var in company_name_variations)
    
    # 2. Extract rank/position
    rank = _extract_rank(response, company_name, competitors) if company_mentioned else None
    
    # 3. Find competitor mentions (exact + semantic)
    competitors_found = []
    competitors_found_set = set()
    
    # Exact matching for competitors
    for competitor in competitors:
        if competitor.lower() in response_lower:
            if competitor not in competitors_found_set:
                competitors_found.append(competitor)
                competitors_found_set.add(competitor)
    
    # Semantic matching for competitors (if available)
    if matcher and competitors:
        try:
            has_mention, mentioned_comps = matcher.analyze_response_for_mentions(
                company_name=company_name,
                response=response,
                competitors=competitors
            )
            for comp in mentioned_comps:
                if comp not in competitors_found_set:
                    competitors_found.append(comp)
                    competitors_found_set.add(comp)
        except Exception as e:
            logger.debug(f"Semantic matching failed: {e}")
    
    return {
        "company_mentioned": company_mentioned,
        "rank": rank,
        "competitors_found": competitors_found
    }


def _extract_rank(response: str, company_name: str, competitors: List[str]) -> Optional[int]:
    """
    Extract the rank/position of the company in the response.
    
    Uses multiple heuristics:
    1. Numbered lists (1., 2., 3. or 1) 2) 3))
    2. Ordinal mentions (first, second, third)
    3. Order of appearance among all brands
    
    Args:
        response: AI model response text
        company_name: Company name to find rank for
        competitors: List of competitor names
        
    Returns:
        Rank (1-based) or None if rank cannot be determined
    """
    if not response or not company_name:
        return None
    
    company_lower = company_name.lower()
    
    # Strategy 1: Look for numbered lists
    # Pattern: "1. CompanyName" or "1) CompanyName" or "1 - CompanyName"
    numbered_patterns = [
        r'(\d+)\.\s*([^\n]+)',  # 1. Item
        r'(\d+)\)\s*([^\n]+)',  # 1) Item
        r'(\d+)\s*-\s*([^\n]+)',  # 1 - Item
        r'(\d+)\s*\.\s*\*\*([^\*]+)\*\*',  # 1. **Item**
    ]
    
    for pattern in numbered_patterns:
        matches = re.finditer(pattern, response, re.IGNORECASE)
        for match in matches:
            rank_num = int(match.group(1))
            item_text = match.group(2).lower()
            
            # Check if company name is in this item
            if company_lower in item_text:
                return rank_num
    
    # Strategy 2: Look for ordinal words
    ordinal_patterns = {
        r'\bfirst\b': 1,
        r'\bsecond\b': 2,
        r'\bthird\b': 3,
        r'\bfourth\b': 4,
        r'\bfifth\b': 5,
        r'\b#1\b': 1,
        r'\b#2\b': 2,
        r'\b#3\b': 3,
    }
    
    # Look for ordinal + company name in proximity
    for pattern, rank_num in ordinal_patterns.items():
        ordinal_matches = list(re.finditer(pattern, response, re.IGNORECASE))
        for ordinal_match in ordinal_matches:
            # Check if company name appears within 100 chars after ordinal
            start_pos = ordinal_match.start()
            context = response[start_pos:start_pos + 100].lower()
            if company_lower in context:
                return rank_num
    
    # Strategy 3: Order of appearance among all brands
    # Find all brand mentions (company + competitors) and their positions
    brand_positions = []
    
    # Add company position
    company_pos = response.lower().find(company_lower)
    if company_pos != -1:
        brand_positions.append((company_pos, company_name, True))
    
    # Add competitor positions
    for competitor in competitors:
        comp_pos = response.lower().find(competitor.lower())
        if comp_pos != -1:
            brand_positions.append((comp_pos, competitor, False))
    
    # Sort by position
    brand_positions.sort(key=lambda x: x[0])
    
    # Find company's rank in order of appearance
    for idx, (pos, brand, is_company) in enumerate(brand_positions, 1):
        if is_company:
            # Only return rank if there are multiple brands mentioned
            if len(brand_positions) > 1:
                return idx
    
    # Could not determine rank
    return None


def _build_competitor_rankings(
    competitor_stats: Dict[str, Dict[str, Any]],
    num_queries: int,
    num_models: int
) -> Dict[str, Any]:
    """
    Build competitor rankings from collected statistics.
    
    Args:
        competitor_stats: Dict of competitor statistics
        num_queries: Total number of queries
        num_models: Total number of models tested
        
    Returns:
        Dict with overall and per-category rankings
    """
    if not competitor_stats:
        return {
            "overall": [],
            "by_category": {}
        }
    
    # Build overall rankings
    overall_rankings = []
    for comp_name, stats in competitor_stats.items():
        total_mentions = stats["total_mentions"]
        total_possible = num_queries * num_models
        mention_rate = total_mentions / total_possible if total_possible > 0 else 0.0
        
        overall_rankings.append({
            "name": comp_name,
            "total_mentions": total_mentions,
            "mention_rate": round(mention_rate, 4),
            "percentage": round(mention_rate * 100, 2)
        })
    
    # Sort by total mentions (descending)
    overall_rankings.sort(key=lambda x: x["total_mentions"], reverse=True)
    
    # Build per-category rankings
    by_category_rankings = {}
    
    # Collect all categories
    all_categories = set()
    for stats in competitor_stats.values():
        all_categories.update(stats["by_category"].keys())
    
    # For each category, rank competitors
    for category in all_categories:
        category_rankings = []
        
        for comp_name, stats in competitor_stats.items():
            cat_mentions = stats["by_category"].get(category, 0)
            if cat_mentions > 0:
                category_rankings.append({
                    "name": comp_name,
                    "mentions": cat_mentions
                })
        
        # Sort by mentions (descending)
        category_rankings.sort(key=lambda x: x["mentions"], reverse=True)
        by_category_rankings[category] = category_rankings
    
    return {
        "overall": overall_rankings,
        "by_category": by_category_rankings
    }


