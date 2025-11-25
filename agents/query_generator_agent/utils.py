"""
Utility functions for query generator.
"""

import logging
import hashlib
import json
from typing import Optional, Dict, List
from config.settings import settings

logger = logging.getLogger(__name__)

QUERY_CACHE_TTL = 86400  # 24 hours


# Caching removed - using route-level slug-based caching only


def get_query_generation_llm(llm_provider: str = None):
    """
    Get LLM instance for query generation tasks.
    
    Args:
        llm_provider: Provider name (openai, claude, gemini, llama, grok, deepseek)
                     If None, uses QUERY_GENERATION_PROVIDER from settings
    
    Returns:
        LangChain LLM instance or None if provider not available
    """
    if llm_provider is None:
        llm_provider = settings.QUERY_GENERATION_PROVIDER
    
    llm_provider = llm_provider.lower()
    
    try:
        if llm_provider == "claude":
            if not settings.ANTHROPIC_API_KEY:
                logger.error("Anthropic API key not configured")
                return None
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model=settings.CLAUDE_MODEL,
                anthropic_api_key=settings.ANTHROPIC_API_KEY,
                temperature=0.7,
                max_tokens=2000,
                timeout=60.0
            )
        
        elif llm_provider == "openai":
            if not settings.OPENAI_API_KEY:
                logger.error("OpenAI API key not configured")
                return None
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=settings.CHATGPT_MODEL,
                openai_api_key=settings.OPENAI_API_KEY,
                temperature=0.7,
                max_tokens=2000,
                timeout=60.0
            )
        
        elif llm_provider == "gemini":
            if not settings.GEMINI_API_KEY:
                logger.error("Gemini API key not configured")
                return None
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model=settings.GEMINI_MODEL,
                google_api_key=settings.GEMINI_API_KEY,
                temperature=0.7,
                max_output_tokens=2000
            )
        
        elif llm_provider == "llama":
            if not settings.GROK_API_KEY:
                logger.error("Groq API key not configured")
                return None
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=settings.GROQ_LLAMA_MODEL,
                openai_api_key=settings.GROK_API_KEY,
                openai_api_base="https://api.groq.com/openai/v1",
                temperature=0.7,
                max_tokens=2000,
                timeout=60.0
            )
        
        elif llm_provider == "grok":
            if not settings.OPEN_ROUTER_API_KEY:
                logger.error("OpenRouter API key not configured")
                return None
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=settings.OPENROUTER_GROK_MODEL,
                openai_api_key=settings.OPEN_ROUTER_API_KEY,
                openai_api_base="https://openrouter.ai/api/v1",
                temperature=0.7,
                max_tokens=2000,
                timeout=60.0
            )
        
        elif llm_provider == "deepseek":
            if not settings.OPEN_ROUTER_API_KEY:
                logger.error("OpenRouter API key not configured")
                return None
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=settings.OPENROUTER_DEEPSEEK_MODEL,
                openai_api_key=settings.OPEN_ROUTER_API_KEY,
                openai_api_base="https://openrouter.ai/api/v1",
                temperature=0.7,
                max_tokens=2000,
                timeout=60.0
            )
        
        else:
            logger.error(f"Unknown LLM provider: {llm_provider}")
            return None
            
    except Exception as e:
        logger.error(f"Failed to initialize {llm_provider} LLM: {str(e)}")
        return None


def deduplicate_queries(queries: List[str]) -> List[str]:
    """Remove duplicate queries while preserving order."""
    seen = set()
    unique = []
    for q in queries:
        q_lower = q.lower().strip()
        if q_lower and q_lower not in seen:
            seen.add(q_lower)
            unique.append(q.strip())
    return unique


def distribute_queries(num_queries: int, categories: Dict) -> Dict[str, int]:
    """Distribute queries across categories without rounding errors."""
    distribution = {}
    remaining = num_queries
    
    # Extract weights and sort by weight descending
    weights = {k: v["weight"] for k, v in categories.items()}
    sorted_categories = sorted(weights.items(), key=lambda x: x[1], reverse=True)
    
    for i, (category_key, weight) in enumerate(sorted_categories):
        if i == len(sorted_categories) - 1:
            # Last category gets all remaining queries
            distribution[category_key] = remaining
        else:
            count = int(num_queries * weight)
            distribution[category_key] = count
            remaining -= count
    
    return distribution
