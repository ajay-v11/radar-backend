"""
Node functions for the AI model tester LangGraph workflow.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from agents.ai_model_tester_agent.models import AIModelTesterState
from agents.ai_model_tester_agent.utils import query_model

logger = logging.getLogger(__name__)


def initialize_responses(state: AIModelTesterState) -> AIModelTesterState:
    """Node: Initialize response storage."""
    logger.info("🚀 Initializing AI model testing...")
    
    models = state.get("models", [])
    queries = state.get("queries", [])
    
    # Initialize response storage
    model_responses = {model: [] for model in models}
    
    state["model_responses"] = model_responses
    state["current_query_index"] = 0
    
    logger.info(f"Testing {len(queries)} queries across {len(models)} models")
    
    return state


def test_queries_batch(state: AIModelTesterState) -> AIModelTesterState:
    """Node: Test all queries as a batch per model (much more efficient)."""
    logger.info("🧪 Testing queries across models (batched)...")
    
    queries = state.get("queries", [])
    models = state.get("models", [])
    target_region = state.get("target_region", "Global")
    model_responses = state.get("model_responses", {})
    errors = state.get("errors", [])
    
    if not queries:
        errors.append("No queries to test")
        state["errors"] = errors
        return state
    
    if not models:
        errors.append("No models specified")
        state["errors"] = errors
        return state
    
    # Import batch query function
    from agents.ai_model_tester_agent.utils import query_model_batch
    
    # Test all models in parallel, each getting all queries at once
    logger.info(f"Batching {len(queries)} queries across {len(models)} models...")
    
    with ThreadPoolExecutor(max_workers=len(models)) as executor:
        future_to_model = {
            executor.submit(query_model_batch, model, queries, target_region): model
            for model in models
        }
        
        for future in as_completed(future_to_model):
            model = future_to_model[future]
            try:
                # Dynamic timeout: 10s per query, min 120s, max 300s
                timeout = min(max(len(queries) * 10, 120), 300)
                responses = future.result(timeout=timeout)
                model_responses[model] = responses
                logger.info(f"  ✓ {model}: {len(responses)} responses")
            except Exception as e:
                error_msg = f"Error batch testing {model}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
                # Fill with empty responses
                model_responses[model] = [""] * len(queries)
    
    state["model_responses"] = model_responses
    state["errors"] = errors
    
    total_responses = sum(len(r) for r in model_responses.values())
    logger.info(f"✓ Completed batch testing. Total responses: {total_responses}")
    
    return state


def finalize(state: AIModelTesterState) -> AIModelTesterState:
    """Node: Finalize and mark as completed."""
    logger.info("✅ AI model testing workflow complete")
    state["completed"] = True
    return state
