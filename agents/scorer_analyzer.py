"""
Scorer Analyzer Agent

This agent calculates the visibility score by analyzing AI model responses
for mentions of the company name and generates a detailed analysis report.
"""

from typing import Dict, List, Any, Tuple
from models.schemas import WorkflowState


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
    
    # Analyze responses for each model
    for model_name, responses in model_responses.items():
        mentions, model_samples = _count_mentions(
            company_name=company_name,
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
            "mention_rate": round(mention_rate, 4)
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


def _count_mentions(
    company_name: str,
    responses: List[str],
    queries: List[str],
    model_name: str
) -> Tuple[int, List[str]]:
    """
    Count mentions of the company name in responses and collect samples.
    
    Performs case-insensitive search for the company name in each response.
    
    Args:
        company_name: The company name to search for
        responses: List of response strings from the AI model
        queries: List of queries (for creating sample mentions)
        model_name: Name of the AI model (for sample mentions)
        
    Returns:
        Tuple of (mention_count, sample_mentions_list)
    """
    mentions = 0
    samples: List[str] = []
    
    # Normalize company name for case-insensitive matching
    company_name_lower = company_name.lower()
    
    for idx, response in enumerate(responses):
        if not response:
            continue
            
        # Case-insensitive search for company name
        if company_name_lower in response.lower():
            mentions += 1
            
            # Collect sample mention (up to 3 per model)
            if len(samples) < 3:
                # Get corresponding query if available
                query_text = queries[idx] if idx < len(queries) else "Unknown query"
                
                # Truncate query for readability
                if len(query_text) > 50:
                    query_text = query_text[:47] + "..."
                
                sample = f"Query: '{query_text}' -> {model_name.capitalize()} mentioned company"
                samples.append(sample)
    
    return mentions, samples

