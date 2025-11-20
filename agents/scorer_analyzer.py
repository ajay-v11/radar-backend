"""
Scorer Analyzer Agent

This agent calculates the visibility score by analyzing AI model responses
for mentions of the company name and competitors using semantic matching.
"""

from typing import Dict, List, Any, Tuple
from models.schemas import WorkflowState
from utils.competitor_matcher import get_competitor_matcher
import logging

logger = logging.getLogger(__name__)


def analyze_score(state: WorkflowState) -> WorkflowState:
    """
    Calculate visibility score based on company mentions in AI model responses.
    
    This function analyzes all responses from AI models to determine how often
    the company was mentioned. It calculates an overall visibility score and
    generates a detailed report with per-model breakdowns and sample mentions.
    
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
    
    # Initialize counters
    total_mentions = 0
    total_responses = 0
    by_model_results: Dict[str, Dict[str, Any]] = {}
    sample_mentions: List[str] = []
    
    # Get competitors for semantic matching
    competitors = state.get("competitors", [])
    
    # Analyze responses for each model
    for model_name, responses in model_responses.items():
        mentions, model_samples, competitor_mentions = _count_mentions_semantic(
            company_name=company_name,
            competitors=competitors,
            responses=responses,
            queries=queries,
            model_name=model_name
        )
        
        total_mentions += mentions
        total_responses += len(responses)
        
        # Calculate per-model mention rate
        mention_rate = mentions / len(responses) if len(responses) > 0 else 0.0
        
        by_model_results[model_name] = {
            "mentions": mentions,
            "total_responses": len(responses),
            "mention_rate": round(mention_rate, 4),
            "competitor_mentions": competitor_mentions
        }
        
        # Collect sample mentions (up to 5 total across all models)
        if len(sample_mentions) < 5:
            sample_mentions.extend(model_samples[:5 - len(sample_mentions)])
    
    # Calculate overall visibility score
    num_queries = len(queries)
    num_models = len(model_responses)
    
    if num_queries > 0 and num_models > 0:
        visibility_score = (total_mentions / (num_queries * num_models)) * 100
    else:
        visibility_score = 0.0
    
    # Calculate overall mention rate
    mention_rate = total_mentions / total_responses if total_responses > 0 else 0.0
    
    # Generate detailed analysis report
    analysis_report = {
        "visibility_score": round(visibility_score, 2),
        "total_queries": num_queries,
        "total_responses": total_responses,
        "total_mentions": total_mentions,
        "mention_rate": round(mention_rate, 4),
        "by_model": by_model_results,
        "sample_mentions": sample_mentions
    }
    
    # Update state with results
    state["visibility_score"] = round(visibility_score, 2)
    state["analysis_report"] = analysis_report
    
    return state


def _count_mentions_semantic(
    company_name: str,
    competitors: List[str],
    responses: List[str],
    queries: List[str],
    model_name: str
) -> Tuple[int, List[str], Dict[str, int]]:
    """
    Count mentions using both exact matching and semantic search.
    
    Combines traditional string matching with RAG-based semantic matching
    to catch variations and indirect mentions.
    
    Args:
        company_name: The company name to search for
        competitors: List of competitor names for context
        responses: List of response strings from the AI model
        queries: List of queries (for creating sample mentions)
        model_name: Name of the AI model (for sample mentions)
        
    Returns:
        Tuple of (mention_count, sample_mentions_list, competitor_mention_counts)
    """
    mentions = 0
    samples: List[str] = []
    competitor_mention_counts: Dict[str, int] = {}
    
    # Normalize company name for case-insensitive matching
    company_name_lower = company_name.lower().strip()
    
    # Also create variations of company name (handle spacing issues)
    company_name_variations = [
        company_name_lower,
        company_name_lower.replace(" ", ""),  # Remove spaces
        company_name_lower.replace(" ", "-"),  # Replace with dash
    ]
    
    # Get competitor matcher for semantic search
    try:
        matcher = get_competitor_matcher()
        use_semantic = True
    except Exception as e:
        logger.warning(f"Competitor matcher unavailable, using exact matching only: {e}")
        use_semantic = False
    
    for idx, response in enumerate(responses):
        if not response:
            continue
        
        # 1. Exact string matching for company name (with variations)
        response_lower = response.lower()
        company_mentioned = any(var in response_lower for var in company_name_variations)
        
        # 2. Semantic matching for competitors (if available)
        competitors_found = []
        if use_semantic and competitors:
            try:
                has_mention, mentioned_comps = matcher.analyze_response_for_mentions(
                    company_name=company_name,
                    response=response,
                    competitors=competitors
                )
                competitors_found = mentioned_comps
                
                # Track competitor mentions
                for comp in mentioned_comps:
                    competitor_mention_counts[comp] = competitor_mention_counts.get(comp, 0) + 1
            except Exception as e:
                logger.debug(f"Semantic matching failed for response {idx}: {e}")
        
        # Count as mention if company or competitors found
        if company_mentioned:
            mentions += 1
            
            # Collect sample mention (up to 3 per model)
            if len(samples) < 3:
                query_text = queries[idx] if idx < len(queries) else "Unknown query"
                if len(query_text) > 50:
                    query_text = query_text[:47] + "..."
                
                comp_info = f" (with {', '.join(competitors_found[:2])})" if competitors_found else ""
                sample = f"Query: '{query_text}' -> {model_name.capitalize()} mentioned company{comp_info}"
                samples.append(sample)
    
    return mentions, samples, competitor_mention_counts


def _count_mentions(
    company_name: str,
    responses: List[str],
    queries: List[str],
    model_name: str
) -> Tuple[int, List[str]]:
    """
    Legacy exact matching function (kept for backward compatibility).
    
    Args:
        company_name: The company name to search for
        responses: List of response strings from the AI model
        queries: List of queries (for creating sample mentions)
        model_name: Name of the AI model (for sample mentions)
        
    Returns:
        Tuple of (mention_count, sample_mentions_list)
    """
    mentions, samples, _ = _count_mentions_semantic(
        company_name=company_name,
        competitors=[],
        responses=responses,
        queries=queries,
        model_name=model_name
    )
    return mentions, samples

