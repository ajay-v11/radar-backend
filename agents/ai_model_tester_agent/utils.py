"""
Utility functions for AI model tester.
"""

import logging
import hashlib
import json
import time
from typing import Optional, List
from functools import wraps
from config.settings import settings

logger = logging.getLogger(__name__)

RESPONSE_CACHE_TTL = 3600  # 1 hour
MAX_BATCH_SIZE = 15  # Split batches larger than this
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 2  # seconds


def retry_with_backoff(max_retries=MAX_RETRIES, initial_delay=INITIAL_RETRY_DELAY):
    """Decorator for retrying functions with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    error_msg = str(e).lower()
                    
                    # Check if it's a rate limit error
                    is_rate_limit = any(term in error_msg for term in [
                        'rate limit', 'too many requests', '429', 'quota'
                    ])
                    
                    if attempt < max_retries - 1:
                        # Longer delay for rate limits
                        wait_time = delay * 3 if is_rate_limit else delay
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}. "
                            f"Retrying in {wait_time}s..."
                        )
                        time.sleep(wait_time)
                        delay *= 2  # Exponential backoff
                    else:
                        logger.error(f"All {max_retries} attempts failed: {str(e)}")
            
            raise last_exception
        return wrapper
    return decorator


# Caching removed - using route-level slug-based caching only


@retry_with_backoff()
def query_chatgpt(query: str, target_region: str = "Global") -> str:
    """Query ChatGPT (OpenAI) with region context."""
    if not settings.OPENAI_API_KEY:
        logger.error("OpenAI API key not configured")
        return ""
    
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage, HumanMessage
    
    llm = ChatOpenAI(
        model=settings.CHATGPT_MODEL,
        openai_api_key=settings.OPENAI_API_KEY,
        temperature=0.7,
        max_tokens=500,
        timeout=60.0
    )
    
    # Add region context to system prompt
    messages = [
        SystemMessage(content=f"You are helping users in {target_region}. Provide recommendations and information relevant to this region."),
        HumanMessage(content=query)
    ]
    
    response = llm.invoke(messages)
    return response.content or ""


@retry_with_backoff()
def query_gemini(query: str, target_region: str = "Global") -> str:
    """Query Gemini (Google) with region context."""
    if not settings.GEMINI_API_KEY:
        logger.error("Gemini API key not configured")
        return ""
    
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


@retry_with_backoff()
def query_claude(query: str, target_region: str = "Global") -> str:
    """Query Claude (Anthropic) with region context."""
    if not settings.ANTHROPIC_API_KEY:
        logger.error("Anthropic API key not configured")
        return ""
    
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import SystemMessage, HumanMessage
    
    llm = ChatAnthropic(
        model=settings.CLAUDE_MODEL,
        anthropic_api_key=settings.ANTHROPIC_API_KEY,
        temperature=0.7,
        max_tokens=500,
        timeout=60.0
    )
    
    messages = [
        SystemMessage(content=f"You are helping users in {target_region}. Provide recommendations and information relevant to this region."),
        HumanMessage(content=query)
    ]
    
    response = llm.invoke(messages)
    return response.content or ""


@retry_with_backoff()
def query_llama(query: str, target_region: str = "Global") -> str:
    """Query Llama 3.1 8B Instant (via Groq) with region context."""
    if not settings.GROK_API_KEY:
        logger.error("Groq API key not configured")
        return ""
    
    from langchain_groq import ChatGroq
    from langchain_core.messages import SystemMessage, HumanMessage
    
    llm = ChatGroq(
        model=settings.GROQ_LLAMA_MODEL,
        groq_api_key=settings.GROK_API_KEY,
        temperature=0.7,
        max_tokens=500,
        timeout=60.0
    )
    
    messages = [
        SystemMessage(content=f"You are helping users in {target_region}. Provide recommendations and information relevant to this region."),
        HumanMessage(content=query)
    ]
    
    response = llm.invoke(messages)
    return response.content or ""


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
    Query a specific AI model with region context.
    
    Args:
        model: Model name (chatgpt, gemini, claude, llama, grok, deepseek)
        query: Query string
        target_region: Target region for context (e.g., "India", "United States")
        
    Returns:
        Model response as string
    """
    # No caching at agent level - using route-level caching only
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
    
    return response


def query_model_batch(model: str, queries: List[str], target_region: str = "Global") -> List[str]:
    """
    Query a model with multiple queries in batches.
    
    Optimizations:
    - Splits large batches (>15 queries) into chunks
    - Retries with exponential backoff
    - Scales timeout with batch size
    
    Args:
        model: Model name (chatgpt, gemini, claude, llama, grok, deepseek)
        queries: List of query strings
        target_region: Target region for context
        
    Returns:
        List of responses (same order as queries)
    """
    if not queries:
        return []
    
    # No caching - query all
    responses = [None] * len(queries)
    uncached_indices = list(range(len(queries)))
    uncached_queries = queries
    
    if len(uncached_queries) > MAX_BATCH_SIZE:
        logger.info(f"Splitting {len(uncached_queries)} queries into chunks of {MAX_BATCH_SIZE}")
        chunks = [uncached_queries[i:i + MAX_BATCH_SIZE] for i in range(0, len(uncached_queries), MAX_BATCH_SIZE)]
        chunk_indices = [uncached_indices[i:i + MAX_BATCH_SIZE] for i in range(0, len(uncached_indices), MAX_BATCH_SIZE)]
    else:
        chunks = [uncached_queries]
        chunk_indices = [uncached_indices]
    
    # Process each chunk
    for chunk_num, (chunk_queries, chunk_idx) in enumerate(zip(chunks, chunk_indices)):
        logger.info(f"Processing chunk {chunk_num + 1}/{len(chunks)} ({len(chunk_queries)} queries)")
        
        try:
            chunk_responses = _query_batch_chunk(model, chunk_queries, target_region)
            
            # Validate we got the right number of responses
            if len(chunk_responses) != len(chunk_queries):
                logger.warning(
                    f"Response count mismatch: expected {len(chunk_queries)}, got {len(chunk_responses)}. "
                    f"Padding with empty strings."
                )
                # Pad or truncate
                while len(chunk_responses) < len(chunk_queries):
                    chunk_responses.append("")
                chunk_responses = chunk_responses[:len(chunk_queries)]
            
            # Fill in responses (no caching)
            for idx, response_text in zip(chunk_idx, chunk_responses):
                responses[idx] = response_text
            
        except Exception as e:
            logger.error(f"Chunk {chunk_num + 1} failed for {model}: {str(e)}")
            # Fill with empty strings
            for idx in chunk_idx:
                responses[idx] = ""
    
    logger.info(f"✓ Batch query complete for {model}")
    return responses


@retry_with_backoff()
def _query_batch_chunk(model: str, queries: List[str], target_region: str) -> List[str]:
    """
    Internal function to query a single batch chunk with retry logic.
    
    Args:
        model: Model name
        queries: List of queries (already chunked)
        target_region: Target region
        
    Returns:
        List of responses
    """
    if not queries:
        return []
    # Calculate timeout based on batch size (10s per query, min 60s, max 180s)
    timeout = min(max(len(queries) * 10, 60), 180)
    
    # Get the appropriate LLM
    model_lower = model.lower()
    
    if model_lower == "chatgpt":
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            model=settings.CHATGPT_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
            temperature=0.7,
            max_tokens=2000,  # Increased for batch responses
            timeout=timeout
        )
    elif model_lower == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.7,
            max_output_tokens=2000
        )
    elif model_lower == "claude":
        from langchain_anthropic import ChatAnthropic
        llm = ChatAnthropic(
            model=settings.CLAUDE_MODEL,
            anthropic_api_key=settings.ANTHROPIC_API_KEY,
            temperature=0.7,
            max_tokens=2000,
            timeout=timeout
        )
    elif model_lower == "llama":
        from langchain_groq import ChatGroq
        llm = ChatGroq(
            model=settings.GROQ_LLAMA_MODEL,
            groq_api_key=settings.GROK_API_KEY,
            temperature=0.7,
            max_tokens=2000,
            timeout=timeout
        )
    elif model_lower == "grok":
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            model=settings.OPENROUTER_GROK_MODEL,
            openai_api_key=settings.OPEN_ROUTER_API_KEY,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0.7,
            max_tokens=2000,
            timeout=timeout
        )
    elif model_lower == "deepseek":
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            model=settings.OPENROUTER_DEEPSEEK_MODEL,
            openai_api_key=settings.OPEN_ROUTER_API_KEY,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0.7,
            max_tokens=2000,
            timeout=timeout
        )
    else:
        raise ValueError(f"Unknown model: {model}")
    
    # Create batch prompt
    from langchain_core.messages import SystemMessage, HumanMessage
    
    system_prompt = f"""You are helping users in {target_region}. Provide recommendations and information relevant to this region.

You will receive multiple queries. Answer each query separately and clearly.
Format your response as:

Query 1: [answer to first query]

Query 2: [answer to second query]

... and so on."""
    
    # Build the batch query
    batch_query = "\n\n".join([f"Query {i+1}: {q}" for i, q in enumerate(queries)])
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=batch_query)
    ]
    
    # Get batch response
    response = llm.invoke(messages)
    batch_response = response.content or ""
    
    # Parse responses with multiple strategies
    parsed_responses = _parse_batch_response(batch_response, len(queries))
    
    return parsed_responses


def _parse_batch_response(batch_response: str, expected_count: int) -> List[str]:
    """
    Parse batch response into individual answers with fallback strategies.
    
    Args:
        batch_response: The full batch response text
        expected_count: Number of responses expected
        
    Returns:
        List of parsed responses
    """
    import re
    
    # Strategy 1: Split by "Query N:" markers
    parts = re.split(r'Query \d+:', batch_response)
    parts = [p.strip() for p in parts if p.strip()]
    
    if len(parts) >= expected_count:
        return parts[:expected_count]
    
    # Strategy 2: Split by numbered list (1., 2., etc.)
    parts = re.split(r'\n\s*\d+\.\s+', batch_response)
    parts = [p.strip() for p in parts if p.strip()]
    
    if len(parts) >= expected_count:
        return parts[:expected_count]
    
    # Strategy 3: Split by double newlines
    parts = batch_response.split('\n\n')
    parts = [p.strip() for p in parts if p.strip()]
    
    if len(parts) >= expected_count:
        return parts[:expected_count]
    
    # Strategy 4: Split by single newlines (less reliable)
    parts = batch_response.split('\n')
    parts = [p.strip() for p in parts if p.strip()]
    
    if len(parts) >= expected_count:
        return parts[:expected_count]
    
    # Fallback: Duplicate the whole response
    logger.warning(f"Could not parse batch response into {expected_count} parts. Using fallback.")
    return [batch_response] * expected_count
