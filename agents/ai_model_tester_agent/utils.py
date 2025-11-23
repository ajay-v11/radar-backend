"""
Utility functions for AI model tester.
"""

import logging
import hashlib
import json
from typing import Optional
from config.settings import settings

logger = logging.getLogger(__name__)

RESPONSE_CACHE_TTL = 3600  # 1 hour


def get_response_cache_key(model: str, query: str) -> str:
    """Generate cache key for model response."""
    key = f"{model}:{query}"
    cache_key = f"response:{hashlib.sha256(key.encode()).hexdigest()}"
    return cache_key


def get_cached_response(model: str, query: str) -> Optional[str]:
    """Get cached model response."""
    try:
        from config.database import get_redis_client
        redis_client = get_redis_client()
        cache_key = get_response_cache_key(model, query)
        cached = redis_client.get(cache_key)
        if cached:
            if isinstance(cached, bytes):
                cached = cached.decode('utf-8')
            logger.debug(f"Cache HIT for {model}: {query[:50]}...")
            return cached
        return None
    except Exception as e:
        logger.warning(f"Cache retrieval failed: {e}")
        return None


def cache_response(model: str, query: str, response: str) -> None:
    """Cache model response."""
    try:
        from config.database import get_redis_client
        redis_client = get_redis_client()
        cache_key = get_response_cache_key(model, query)
        redis_client.setex(cache_key, RESPONSE_CACHE_TTL, response)
        logger.debug(f"Cached response for {model}")
    except Exception as e:
        logger.warning(f"Cache storage failed: {e}")


def query_chatgpt(query: str, target_region: str = "Global") -> str:
    """Query ChatGPT (OpenAI) with region context."""
    if not settings.OPENAI_API_KEY:
        logger.error("OpenAI API key not configured")
        return ""
    
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage, HumanMessage
        
        llm = ChatOpenAI(
            model=settings.CHATGPT_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
            temperature=0.7,
            max_tokens=500,
            timeout=30.0
        )
        
        # Add region context to system prompt
        messages = [
            SystemMessage(content=f"You are helping users in {target_region}. Provide recommendations and information relevant to this region."),
            HumanMessage(content=query)
        ]
        
        response = llm.invoke(messages)
        return response.content or ""
    
    except Exception as e:
        logger.error(f"ChatGPT API error: {str(e)}")
        return ""


def query_gemini(query: str, target_region: str = "Global") -> str:
    """Query Gemini (Google) with region context."""
    if not settings.GEMINI_API_KEY:
        logger.error("Gemini API key not configured")
        return ""
    
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain_core.messages import SystemMessage, HumanMessage
        
        llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.7,
            max_output_tokens=500
        )
        
        # Add region context to system prompt
        messages = [
            SystemMessage(content=f"You are helping users in {target_region}. Provide recommendations and information relevant to this region."),
            HumanMessage(content=query)
        ]
        
        response = llm.invoke(messages)
        return response.content or ""
    
    except Exception as e:
        logger.error(f"Gemini API error: {str(e)}")
        return ""


def query_claude(query: str, target_region: str = "Global") -> str:
    """Query Claude (Anthropic) with region context."""
    if not settings.ANTHROPIC_API_KEY:
        logger.error("Anthropic API key not configured")
        return ""
    
    try:
        from langchain_anthropic import ChatAnthropic
        from langchain_core.messages import SystemMessage, HumanMessage
        
        llm = ChatAnthropic(
            model=settings.CLAUDE_MODEL,
            anthropic_api_key=settings.ANTHROPIC_API_KEY,
            temperature=0.7,
            max_tokens=500,
            timeout=30.0
        )
        
        messages = [
            SystemMessage(content=f"You are helping users in {target_region}. Provide recommendations and information relevant to this region."),
            HumanMessage(content=query)
        ]
        
        response = llm.invoke(messages)
        return response.content or ""
    
    except Exception as e:
        logger.error(f"Claude API error: {str(e)}")
        return ""


def query_llama(query: str, target_region: str = "Global") -> str:
    """Query Llama 3.1 8B Instant (via Groq) with region context."""
    if not settings.GROK_API_KEY:
        logger.error("Groq API key not configured")
        return ""
    
    try:
        from langchain_groq import ChatGroq
        from langchain_core.messages import SystemMessage, HumanMessage
        
        llm = ChatGroq(
            model=settings.GROQ_LLAMA_MODEL,
            groq_api_key=settings.GROK_API_KEY,
            temperature=0.7,
            max_tokens=500,
            timeout=30.0
        )
        
        messages = [
            SystemMessage(content=f"You are helping users in {target_region}. Provide recommendations and information relevant to this region."),
            HumanMessage(content=query)
        ]
        
        response = llm.invoke(messages)
        return response.content or ""
    
    except Exception as e:
        logger.error(f"Llama API error: {str(e)}")
        return ""


def query_grok(query: str, target_region: str = "Global") -> str:
    """Query Grok (via OpenRouter) with region context."""
    if not settings.OPEN_ROUTER_API_KEY:
        logger.error("OpenRouter API key not configured")
        return ""
    
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage, HumanMessage
        
        llm = ChatOpenAI(
            model=settings.OPENROUTER_GROK_MODEL,
            openai_api_key=settings.OPEN_ROUTER_API_KEY,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0.7,
            max_tokens=500,
            timeout=30.0
        )
        
        messages = [
            SystemMessage(content=f"You are helping users in {target_region}. Provide recommendations and information relevant to this region."),
            HumanMessage(content=query)
        ]
        
        response = llm.invoke(messages)
        return response.content or ""
    
    except Exception as e:
        logger.error(f"Grok API error: {str(e)}")
        return ""


def query_deepseek(query: str, target_region: str = "Global") -> str:
    """Query DeepSeek (via OpenRouter) with region context."""
    if not settings.OPEN_ROUTER_API_KEY:
        logger.error("OpenRouter API key not configured")
        return ""
    
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage, HumanMessage
        
        llm = ChatOpenAI(
            model=settings.OPENROUTER_DEEPSEEK_MODEL,
            openai_api_key=settings.OPEN_ROUTER_API_KEY,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0.7,
            max_tokens=500,
            timeout=30.0
        )
        
        messages = [
            SystemMessage(content=f"You are helping users in {target_region}. Provide recommendations and information relevant to this region."),
            HumanMessage(content=query)
        ]
        
        response = llm.invoke(messages)
        return response.content or ""
    
    except Exception as e:
        logger.error(f"DeepSeek API error: {str(e)}")
        return ""


def query_model(model: str, query: str, target_region: str = "Global") -> str:
    """
    Query a specific AI model with caching and region context.
    
    Args:
        model: Model name (chatgpt, gemini, claude, llama, grok, deepseek)
        query: Query string
        target_region: Target region for context (e.g., "India", "United States")
        
    Returns:
        Model response as string
    """
    # Check cache first (cache key includes region)
    cache_key_with_region = f"{model}:{target_region}:{query}"
    cached = get_cached_response(model, cache_key_with_region)
    if cached is not None:
        return cached
    
    # Query model with region context
    model_lower = model.lower()
    
    if model_lower == "chatgpt":
        response = query_chatgpt(query, target_region)
    elif model_lower == "gemini":
        response = query_gemini(query, target_region)
    elif model_lower == "claude":
        response = query_claude(query, target_region)
    elif model_lower == "llama":
        response = query_llama(query, target_region)
    elif model_lower == "grok":
        response = query_grok(query, target_region)
    elif model_lower == "deepseek":
        response = query_deepseek(query, target_region)
    else:
        logger.error(f"Unknown model: {model}")
        response = ""
    
    # Cache response
    if response:
        cache_response(model, cache_key_with_region, response)
    
    return response
