"""
Utility functions for scorer analyzer.
"""

import logging
import re
from typing import Dict, List, Tuple, Optional, Any

logger = logging.getLogger(__name__)


def build_query_category_map(queries: List[str], query_categories: Dict) -> Dict[int, str]:
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


def analyze_single_response(
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
    rank = extract_rank(response, company_name, competitors) if company_mentioned else None
    
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


def extract_rank(response: str, company_name: str, competitors: List[str]) -> Optional[int]:
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


def build_competitor_rankings(
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
