"""
Node functions for visibility orchestration workflow.

Category-based batching: Process one category at a time with progressive results.
"""

import logging
from typing import Dict, List
from langchain_core.messages import SystemMessage, HumanMessage

from agents.visibility_orchestrator.models import VisibilityOrchestrationState
from agents.query_generator_agent.models import CategoryQueries
from agents.query_generator_agent.utils import get_query_generation_llm
from config.settings import settings

logger = logging.getLogger(__name__)


def get_exact_model_name(model_key: str) -> str:
    """
    Get the exact model name/version for a given model key.
    
    Args:
        model_key: Short model key (e.g., "chatgpt", "claude", "gemini")
        
    Returns:
        Exact model name (e.g., "gpt-3.5-turbo", "claude-3-5-haiku-20241022")
    """
    model_map = {
        "chatgpt": settings.CHATGPT_MODEL,
        "claude": settings.CLAUDE_MODEL,
        "gemini": settings.GEMINI_MODEL,
        "llama": settings.GROQ_LLAMA_MODEL,
        "grok": settings.OPENROUTER_GROK_MODEL,
        "deepseek": settings.OPENROUTER_DEEPSEEK_MODEL
    }
    return model_map.get(model_key.lower(), model_key)


def initialize_categories(state: VisibilityOrchestrationState) -> VisibilityOrchestrationState:
    """
    Node: Initialize category processing queue and distribution.
    
    Sets up the category-based batching workflow.
    """
    logger.info("🚀 Initializing category-based workflow...")
    
    query_categories_template = state.get("query_categories_template", {})
    num_queries = state.get("num_queries", 20)
    
    if not query_categories_template:
        error_msg = "No query categories template provided"
        logger.error(error_msg)
        state["errors"].append(error_msg)
        state["categories_to_process"] = []
        state["completed"] = True
        return state
    
    # Handle two formats:
    # Format 1: {"categories": [{"category_key": "...", "weight": ..., ...}]}
    # Format 2: {"category_key": {"name": "...", "weight": ..., ...}}
    
    if "categories" in query_categories_template:
        # Format 1: List of categories
        categories = query_categories_template["categories"]
        category_names = [cat["category_key"] for cat in categories]
        
        # Convert to dict format for distribute_queries
        categories_dict = {
            cat["category_key"]: {
                "weight": cat["weight"],
                "name": cat["category_name"],
                "description": cat["description"],
                "examples": cat.get("examples", [])
            }
            for cat in categories
        }
    else:
        # Format 2: Dict of categories (from Phase 1)
        categories_dict = {}
        for key, cat_data in query_categories_template.items():
            categories_dict[key] = {
                "weight": cat_data.get("weight", 0.1),
                "name": cat_data.get("name", key),
                "description": cat_data.get("description", ""),
                "examples": cat_data.get("examples", [])
            }
        category_names = list(categories_dict.keys())
    
    # Calculate how many queries per category based on weights
    from agents.query_generator_agent.utils import distribute_queries
    distribution = distribute_queries(num_queries, categories_dict)
    
    # Initialize state
    state["categories_to_process"] = category_names.copy()
    state["completed_categories"] = []
    state["category_distribution"] = distribution
    state["current_category"] = None
    
    # Initialize accumulators
    state["category_queries"] = {}
    state["category_responses"] = {}
    state["category_scores"] = {}
    state["category_mentions"] = {}
    state["category_analysis"] = {}
    
    # Initialize running totals
    state["total_queries"] = 0
    state["total_mentions"] = 0
    state["total_responses"] = 0
    state["partial_visibility_score"] = 0.0
    
    # Initialize final outputs
    state["queries"] = []
    state["query_categories"] = {}
    state["model_responses"] = {model: [] for model in state.get("models", [])}
    state["visibility_score"] = 0.0
    state["analysis_report"] = {}
    
    logger.info(f"✓ Initialized {len(category_names)} categories: {', '.join(category_names)}")
    logger.info(f"✓ Distribution: {distribution}")
    
    return state


def select_next_category(state: VisibilityOrchestrationState) -> VisibilityOrchestrationState:
    """
    Node: Select the next category to process.
    """
    categories_to_process = list(state.get("categories_to_process", []))
    
    if not categories_to_process:
        logger.info("✓ All categories processed")
        state["current_category"] = None
        return state
    
    # Get the next category (first in queue)
    current_category = categories_to_process[0]
    state["current_category"] = current_category
    
    # Initialize current category working data
    state["current_queries"] = []
    state["current_responses"] = {model: [] for model in state.get("models", [])}
    state["current_mentions"] = 0
    state["current_score"] = 0.0
    
    logger.info(f"📂 Processing category: {current_category} ({len(state.get('completed_categories', []))+1}/{len(categories_to_process) + len(state.get('completed_categories', []))})")
    
    return state


def generate_category_queries(state: VisibilityOrchestrationState) -> VisibilityOrchestrationState:
    """
    Node: Generate queries for the current category only.
    """
    current_category = state.get("current_category")
    category_distribution = state.get("category_distribution", {})
    query_categories_template = state.get("query_categories_template", {})
    
    if not current_category:
        return state
    
    num_queries_for_category = category_distribution.get(current_category, 5)
    
    logger.info(f"🎯 Generating {num_queries_for_category} queries for '{current_category}'...")
    
    # Find category details from template (handle both formats)
    category_info = None
    
    if "categories" in query_categories_template:
        # Format 1: List of categories
        for cat in query_categories_template["categories"]:
            if cat["category_key"] == current_category:
                category_info = cat
                break
    else:
        # Format 2: Dict of categories (from Phase 1)
        if current_category in query_categories_template:
            cat_data = query_categories_template[current_category]
            category_info = {
                "category_key": current_category,
                "category_name": cat_data.get("name", current_category),
                "description": cat_data.get("description", ""),
                "examples": cat_data.get("examples", [])
            }
    
    if not category_info:
        error_msg = f"Category '{current_category}' not found in template"
        logger.error(error_msg)
        state["errors"].append(error_msg)
        state["current_queries"] = []
        return state
    
    try:
        # Generate queries using LLM
        llm = get_query_generation_llm(state.get("llm_provider", "claude"))
        
        if not llm:
            raise Exception("Failed to initialize LLM")
        
        # Build context
        competitors_str = ", ".join(state.get("competitors", [])[:5])
        
        system_prompt = f"""You are a search query expert. Generate realistic search queries that users would type into AI chatbots.

Industry: {state.get('industry')}
Company: {state.get('company_name')}
Description: {state.get('company_description', '')}
Competitors: {competitors_str}

Category: {category_info['category_name']}
Description: {category_info['description']}
Examples: {', '.join(category_info.get('examples', []))}

Generate {num_queries_for_category} diverse, natural search queries for this category.
Mix company name, competitors, and generic industry terms.
Make queries realistic - how real users would search."""

        user_prompt = f"Generate exactly {num_queries_for_category} search queries for the '{category_info['category_name']}' category."
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = llm.with_structured_output(CategoryQueries).invoke(messages)
        queries = response.queries[:num_queries_for_category]
        
        state["current_queries"] = queries
        
        logger.info(f"✓ Generated {len(queries)} queries for '{current_category}'")
        
    except Exception as e:
        error_msg = f"Query generation failed for '{current_category}': {str(e)}"
        logger.error(error_msg)
        state["errors"].append(error_msg)
        state["current_queries"] = []
    
    return state


def test_category_models(state: VisibilityOrchestrationState) -> VisibilityOrchestrationState:
    """
    Node: Test current category queries across all models in parallel.
    """
    current_category = state.get("current_category")
    current_queries = state.get("current_queries", [])
    models = state.get("models", [])
    target_region = state.get("target_region", "Global")
    
    if not current_queries:
        logger.warning(f"No queries to test for '{current_category}'")
        return state
    
    logger.info(f"🧪 Testing {len(current_queries)} queries for '{current_category}' across {len(models)} models...")
    
    try:
        from agents.ai_model_tester_agent import run_ai_model_testing_workflow
        
        result = run_ai_model_testing_workflow(
            queries=current_queries,
            models=models,
            target_region=target_region
        )
        
        state["current_responses"] = result.get("model_responses", {})
        
        if result.get("errors"):
            state["errors"].extend(result["errors"])
        
        total_responses = sum(len(r) for r in state["current_responses"].values())
        logger.info(f"✓ Tested {total_responses} responses for '{current_category}'")
        
    except Exception as e:
        error_msg = f"Model testing failed for '{current_category}': {str(e)}"
        logger.error(error_msg)
        state["errors"].append(error_msg)
        state["current_responses"] = {model: [] for model in models}
    
    return state


def analyze_category_results(state: VisibilityOrchestrationState) -> VisibilityOrchestrationState:
    """
    Node: Analyze results for the current category batch.
    """
    current_category = state.get("current_category")
    current_queries = state.get("current_queries", [])
    current_responses = state.get("current_responses", {})
    company_name = state.get("company_name", "")
    competitors = state.get("competitors", [])
    
    if not current_queries or not current_responses:
        logger.warning(f"No data to analyze for '{current_category}'")
        return state
    
    logger.info(f"📊 Analyzing results for '{current_category}'...")
    
    try:
        from agents.scorer_analyzer_agent import run_scorer_analysis_workflow
        
        # Create a temporary query_categories dict for this category
        temp_query_categories = {
            current_category: {
                "queries": current_queries
            }
        }
        
        result = run_scorer_analysis_workflow(
            company_name=company_name,
            queries=current_queries,
            model_responses=current_responses,
            query_categories=temp_query_categories,
            competitors=competitors
        )
        
        state["current_score"] = result.get("visibility_score", 0.0)
        state["current_mentions"] = result.get("analysis_report", {}).get("total_mentions", 0)
        
        # Store detailed analysis for this category
        state["category_analysis"][current_category] = result.get("analysis_report", {})
        
        # Extract per-model scores for this category
        analysis_report = result.get("analysis_report", {})
        by_model = analysis_report.get("by_model", {})
        
        state["current_model_scores"] = {}
        for model_name, model_data in by_model.items():
            mentions = model_data.get("mentions", 0)
            total = model_data.get("total_responses", 0)
            score = (mentions / total * 100) if total > 0 else 0.0
            state["current_model_scores"][model_name] = {
                "score": round(score, 2),
                "mentions": mentions,
                "total": total
            }
        
        if result.get("errors"):
            state["errors"].extend(result["errors"])
        
        logger.info(f"✓ Category '{current_category}' score: {state['current_score']:.1f}% ({state['current_mentions']} mentions)")
        
    except Exception as e:
        error_msg = f"Analysis failed for '{current_category}': {str(e)}"
        logger.error(error_msg)
        state["errors"].append(error_msg)
        state["current_score"] = 0.0
        state["current_mentions"] = 0
        state["current_model_scores"] = {}
    
    return state


def aggregate_category_results(state: VisibilityOrchestrationState) -> VisibilityOrchestrationState:
    """
    Node: Aggregate current category results into running totals.
    """
    current_category = state.get("current_category")
    current_queries = state.get("current_queries", [])
    current_responses = state.get("current_responses", {})
    current_score = state.get("current_score", 0.0)
    current_mentions = state.get("current_mentions", 0)
    current_model_scores = state.get("current_model_scores", {})
    
    if not current_category:
        return state
    
    logger.info(f"📈 Aggregating results for '{current_category}'...")
    
    # Store category-specific results
    state["category_queries"][current_category] = current_queries
    state["category_responses"][current_category] = current_responses
    state["category_scores"][current_category] = current_score
    state["category_mentions"][current_category] = current_mentions
    
    # Initialize model tracking if not exists
    if "model_mentions" not in state:
        state["model_mentions"] = {model: 0 for model in state.get("models", [])}
    if "model_totals" not in state:
        state["model_totals"] = {model: 0 for model in state.get("models", [])}
    
    # Update per-model running totals
    for model_name, model_data in current_model_scores.items():
        if model_name not in state["model_mentions"]:
            state["model_mentions"][model_name] = 0
        if model_name not in state["model_totals"]:
            state["model_totals"][model_name] = 0
        
        state["model_mentions"][model_name] += model_data.get("mentions", 0)
        state["model_totals"][model_name] += model_data.get("total", 0)
    
    # Update running totals
    state["total_queries"] += len(current_queries)
    state["total_mentions"] += current_mentions
    
    # Aggregate responses into model_responses
    for model, responses in current_responses.items():
        state["model_responses"][model].extend(responses)
        state["total_responses"] += len(responses)
    
    # Aggregate queries
    state["queries"].extend(current_queries)
    state["query_categories"][current_category] = {"queries": current_queries}
    
    # Calculate partial visibility score (overall)
    if state["total_responses"] > 0:
        state["partial_visibility_score"] = (state["total_mentions"] / state["total_responses"]) * 100
    
    # Calculate partial per-model scores
    state["partial_model_scores"] = {}
    for model_name in state.get("models", []):
        model_total = state["model_totals"].get(model_name, 0)
        model_mentions = state["model_mentions"].get(model_name, 0)
        if model_total > 0:
            state["partial_model_scores"][model_name] = round((model_mentions / model_total) * 100, 2)
        else:
            state["partial_model_scores"][model_name] = 0.0
    
    # Mark category as completed and remove from queue
    completed_categories = list(state.get("completed_categories", []))
    if current_category not in completed_categories:
        completed_categories.append(current_category)
    state["completed_categories"] = completed_categories
    
    # Remove from processing queue - create new list
    categories_to_process = list(state.get("categories_to_process", []))
    if current_category in categories_to_process:
        categories_to_process.remove(current_category)
    state["categories_to_process"] = categories_to_process
    
    logger.info(f"✓ Aggregated: {state['total_queries']} queries, {state['total_mentions']} mentions, {state['partial_visibility_score']:.1f}% visibility")
    
    return state


def finalize_results(state: VisibilityOrchestrationState) -> VisibilityOrchestrationState:
    """
    Node: Finalize results and build comprehensive analysis report.
    """
    logger.info("🎉 Finalizing visibility analysis...")
    
    # Set final visibility score
    state["visibility_score"] = state.get("partial_visibility_score", 0.0)
    
    # Build comprehensive analysis report
    analysis_report = {
        "total_mentions": state.get("total_mentions", 0),
        "total_responses": state.get("total_responses", 0),
        "mention_rate": state["visibility_score"] / 100 if state["visibility_score"] > 0 else 0,
        "by_category": {},
        "by_model": {},
        "category_breakdown": []
    }
    
    # Category breakdown with per-model data
    for category in state.get("completed_categories", []):
        category_analysis = state["category_analysis"].get(category, {})
        
        category_data = {
            "category": category,
            "queries": len(state["category_queries"].get(category, [])),
            "score": state["category_scores"].get(category, 0.0),
            "mentions": state["category_mentions"].get(category, 0),
            "analysis": category_analysis
        }
        analysis_report["category_breakdown"].append(category_data)
        analysis_report["by_category"][category] = category_data
    
    # Model breakdown - aggregate from all category analyses
    model_mentions = {}
    model_totals = {}
    
    for category in state.get("completed_categories", []):
        category_analysis = state["category_analysis"].get(category, {})
        by_model = category_analysis.get("by_model", {})
        
        for model_name, model_data in by_model.items():
            if model_name not in model_mentions:
                model_mentions[model_name] = 0
                model_totals[model_name] = 0
            
            model_mentions[model_name] += model_data.get("mentions", 0)
            model_totals[model_name] += model_data.get("total_responses", 0)
    
    # Build final per-model report
    for model_name in state.get("models", []):
        mentions = model_mentions.get(model_name, 0)
        total = model_totals.get(model_name, 0)
        mention_rate = (mentions / total) if total > 0 else 0.0
        
        analysis_report["by_model"][model_name] = {
            "mentions": mentions,
            "total_responses": total,
            "mention_rate": round(mention_rate, 4),
            "non_empty_responses": len([r for r in state.get("model_responses", {}).get(model_name, []) if r])
        }
    
    state["analysis_report"] = analysis_report
    state["completed"] = True
    
    completed_count = len(state.get("completed_categories", []))
    logger.info(f"✅ Final visibility score: {state['visibility_score']:.1f}%")
    logger.info(f"✅ Processed {completed_count} categories")
    
    return state
