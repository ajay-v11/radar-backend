"""
AI Model Tester Agent

This agent tests generated queries against multiple AI models and collects responses.
"""

import logging
from typing import Dict, List
from models.schemas import WorkflowState
from config.settings import settings

logger = logging.getLogger(__name__)

# Constants
MAX_MODELS_ALLOWED = 2  # Limit for now, easy to change to 4 later
DEFAULT_MODELS = ["chatgpt", "gemini"]
OPENAI_TIMEOUT = 30.0
MAX_TOKENS = 500
TEMPERATURE = 0.7


def test_ai_models(state: WorkflowState) -> WorkflowState:
    """
    Test queries against multiple AI models.
    
    Args:
        state: WorkflowState containing queries and models list
        
    Returns:
        Updated WorkflowState with model_responses populated
    """
    queries = state.get("queries", [])
    models = state.get("models", DEFAULT_MODELS)[:MAX_MODELS_ALLOWED]
    errors = state.get("errors", [])
    
    if not queries:
        errors.append("No queries to test")
        state["errors"] = errors
        return state
    
    if not models:
        errors.append("No models specified")
        state["errors"] = errors
        return state
    
    logger.info(f"Testing {len(queries)} queries against {len(models)} models")
    
    # Initialize response storage
    model_responses: Dict[str, List[str]] = {model: [] for model in models}
    
    # Test each query against all models
    for i, query in enumerate(queries):
        logger.info(f"Testing query {i+1}/{len(queries)}: {query[:50]}...")
        
        for model in models:
            try:
                response = _query_model(model, query)
                model_responses[model].append(response)
                logger.debug(f"  {model}: {len(response)} chars")
            except Exception as e:
                error_msg = f"Error testing {model} on query '{query[:50]}...': {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
                model_responses[model].append("")  # Empty response on error
    
    state["model_responses"] = model_responses
    state["errors"] = errors
    
    logger.info(f"Completed testing. Total responses: {sum(len(r) for r in model_responses.values())}")
    
    return state


def _query_model(model: str, query: str) -> str:
    """
    Query a specific AI model.
    
    Args:
        model: Model name (chatgpt, gemini, claude, llama, grok, deepseek)
        query: Query string
        
    Returns:
        Model response as string
    """
    model_lower = model.lower()
    
    if model_lower == "chatgpt":
        return _query_chatgpt(query)
    elif model_lower == "gemini":
        return _query_gemini(query)
    elif model_lower == "claude":
        return _query_claude(query)
    elif model_lower == "llama":
        return _query_llama(query)
    elif model_lower == "grok":
        return _query_grok(query)
    elif model_lower == "deepseek":
        return _query_deepseek(query)
    else:
        logger.error(f"Unknown model: {model}")
        return ""


def _query_chatgpt(query: str) -> str:
    """Query ChatGPT (OpenAI) via LangChain."""
    if not settings.OPENAI_API_KEY:
        logger.error("OpenAI API key not configured")
        return ""
    
    try:
        from langchain_openai import ChatOpenAI
        
        llm = ChatOpenAI(
            model=settings.CHATGPT_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            timeout=OPENAI_TIMEOUT
        )
        
        response = llm.invoke(query)
        return response.content or ""
    
    except Exception as e:
        logger.error(f"ChatGPT API error: {str(e)}")
        return ""


def _query_gemini(query: str) -> str:
    """Query Gemini (Google) via LangChain."""
    if not settings.GEMINI_API_KEY:
        logger.error("Gemini API key not configured")
        return ""
    
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=TEMPERATURE,
            max_output_tokens=MAX_TOKENS
        )
        
        response = llm.invoke(query)
        return response.content or ""
    
    except Exception as e:
        logger.error(f"Gemini API error: {str(e)}")
        return ""


def _query_claude(query: str) -> str:
    """Query Claude (Anthropic) via LangChain."""
    if not settings.ANTHROPIC_API_KEY:
        logger.error("Anthropic API key not configured")
        return ""
    
    try:
        from langchain_anthropic import ChatAnthropic
        
        llm = ChatAnthropic(
            model=settings.CLAUDE_MODEL,
            anthropic_api_key=settings.ANTHROPIC_API_KEY,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            timeout=OPENAI_TIMEOUT
        )
        
        response = llm.invoke(query)
        return response.content or ""
    
    except Exception as e:
        logger.error(f"Claude API error: {str(e)}")
        return ""


def _query_llama(query: str) -> str:
    """Query Llama 3.1 8B Instant (via Groq) using LangChain."""
    if not settings.GROK_API_KEY:
        logger.error("Groq API key not configured")
        return ""
    
    try:
        from langchain_groq import ChatGroq
        
        llm = ChatGroq(
            model=settings.GROQ_LLAMA_MODEL,
            groq_api_key=settings.GROK_API_KEY,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            timeout=OPENAI_TIMEOUT
        )
        
        response = llm.invoke(query)
        return response.content or ""
    
    except Exception as e:
        logger.error(f"Llama API error: {str(e)}")
        return ""


def _query_grok(query: str) -> str:
    """Query Grok 4.1 Fast (via OpenRouter) using LangChain."""
    if not settings.OPEN_ROUTER_API_KEY:
        logger.error("OpenRouter API key not configured")
        return ""
    
    try:
        from langchain_openai import ChatOpenAI
        
        llm = ChatOpenAI(
            model=settings.OPENROUTER_GROK_MODEL,
            openai_api_key=settings.OPEN_ROUTER_API_KEY,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            timeout=OPENAI_TIMEOUT
        )
        
        response = llm.invoke(query)
        return response.content or ""
    
    except Exception as e:
        logger.error(f"Grok API error: {str(e)}")
        return ""


def _query_deepseek(query: str) -> str:
    """Query DeepSeek Chat (via OpenRouter) using LangChain."""
    if not settings.OPEN_ROUTER_API_KEY:
        logger.error("OpenRouter API key not configured")
        return ""
    
    try:
        from langchain_openai import ChatOpenAI
        
        llm = ChatOpenAI(
            model=settings.OPENROUTER_DEEPSEEK_MODEL,
            openai_api_key=settings.OPEN_ROUTER_API_KEY,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            timeout=OPENAI_TIMEOUT
        )
        
        response = llm.invoke(query)
        return response.content or ""
    
    except Exception as e:
        logger.error(f"DeepSeek API error: {str(e)}")
        return ""
