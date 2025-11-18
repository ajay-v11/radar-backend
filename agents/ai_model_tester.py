"""
AI Model Tester Agent

This agent executes queries against multiple AI models and collects
their responses for visibility analysis.
"""

from typing import Dict, List, Optional
from openai import OpenAI
from anthropic import Anthropic
from config.settings import settings
from models.schemas import WorkflowState


def test_ai_models(state: WorkflowState) -> WorkflowState:
    """
    Execute all queries against selected AI models, collecting responses.
    
    This function takes the generated queries from the workflow state and
    executes each one against the selected AI models. Responses are collected
    and organized by model name. API failures are handled gracefully with a
    single retry attempt.
    
    Args:
        state: WorkflowState containing queries list and optional models list
        
    Returns:
        Updated WorkflowState with model_responses dictionary populated
        
    Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
    """
    queries = state.get("queries", [])
    errors = state.get("errors", [])
    
    # Get models to test (default to chatgpt and gemini)
    models_to_test = state.get("models", settings.DEFAULT_MODELS)
    
    # Initialize response storage
    model_responses: Dict[str, List[str]] = {model: [] for model in models_to_test}
    
    # Execute each query against all selected models
    for query in queries:
        for model_name in models_to_test:
            response = _query_model(model_name, query, errors)
            model_responses[model_name].append(response)
    
    # Update state with collected responses
    state["model_responses"] = model_responses
    state["errors"] = errors
    
    return state


def _query_model(model_name: str, query: str, errors: List[str]) -> str:
    """
    Route query to the appropriate model handler.
    
    Args:
        model_name: Name of the model to query
        query: The query string to execute
        errors: List to append error messages to
        
    Returns:
        Response string from the model, or empty string on failure
    """
    model_handlers = {
        "chatgpt": _query_chatgpt,
        "claude": _query_claude,
        "gemini": _query_gemini,
        "llama": _query_llama,
        "mistral": _query_mistral,
        "qwen": _query_qwen,
    }
    
    handler = model_handlers.get(model_name)
    if not handler:
        errors.append(f"Unknown model: {model_name}")
        return ""
    
    return handler(query, errors)


def _query_chatgpt(query: str, errors: List[str]) -> str:
    """
    Execute a single query against ChatGPT with retry logic.
    
    Args:
        query: The query string to execute
        errors: List to append error messages to
        
    Returns:
        Response string from ChatGPT, or empty string on failure
    """
    if not settings.OPENAI_API_KEY:
        errors.append(f"ChatGPT: API key not configured")
        return ""
    
    max_retries = 2
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=settings.CHATGPT_MODEL,
                messages=[{"role": "user", "content": query}],
                max_tokens=500,
                temperature=0.7
            )
            return response.choices[0].message.content or ""
            
        except Exception as e:
            if attempt == max_retries - 1:
                errors.append(f"ChatGPT API error on query '{query[:50]}...' (attempt {attempt + 1}/{max_retries}): {str(e)}")
                return ""
    
    return ""


def _query_claude(query: str, errors: List[str]) -> str:
    """
    Execute a single query against Claude with retry logic.
    
    Args:
        query: The query string to execute
        errors: List to append error messages to
        
    Returns:
        Response string from Claude, or empty string on failure
    """
    if not settings.ANTHROPIC_API_KEY:
        errors.append(f"Claude: API key not configured")
        return ""
    
    max_retries = 2
    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=500,
                messages=[{"role": "user", "content": query}]
            )
            if response.content and len(response.content) > 0:
                return response.content[0].text
            return ""
            
        except Exception as e:
            if attempt == max_retries - 1:
                errors.append(f"Claude API error on query '{query[:50]}...' (attempt {attempt + 1}/{max_retries}): {str(e)}")
                return ""
    
    return ""


def _query_gemini(query: str, errors: List[str]) -> str:
    """
    Execute a single query against Gemini with retry logic.
    
    Args:
        query: The query string to execute
        errors: List to append error messages to
        
    Returns:
        Response string from Gemini, or empty string on failure
    """
    if not settings.GEMINI_API_KEY:
        errors.append(f"Gemini: API key not configured")
        return ""
    
    max_retries = 2
    
    for attempt in range(max_retries):
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            
            llm = ChatGoogleGenerativeAI(
                model=settings.GEMINI_MODEL,
                google_api_key=settings.GEMINI_API_KEY,
                temperature=0.7,
                max_output_tokens=500
            )
            response = llm.invoke(query)
            return response.content or ""
            
        except Exception as e:
            if attempt == max_retries - 1:
                errors.append(f"Gemini API error on query '{query[:50]}...' (attempt {attempt + 1}/{max_retries}): {str(e)}")
                return ""
    
    return ""


def _query_llama(query: str, errors: List[str]) -> str:
    """
    Execute a single query against Llama via Groq with retry logic.
    
    Args:
        query: The query string to execute
        errors: List to append error messages to
        
    Returns:
        Response string from Llama, or empty string on failure
    """
    if not settings.GROK_API_KEY:
        errors.append(f"Llama (Groq): API key not configured")
        return ""
    
    max_retries = 2
    
    for attempt in range(max_retries):
        try:
            # Groq uses OpenAI-compatible API
            client = OpenAI(
                api_key=settings.GROK_API_KEY,
                base_url="https://api.groq.com/openai/v1"
            )
            response = client.chat.completions.create(
                model=settings.GROQ_LLAMA_MODEL,
                messages=[{"role": "user", "content": query}],
                max_tokens=500,
                temperature=0.7
            )
            return response.choices[0].message.content or ""
            
        except Exception as e:
            if attempt == max_retries - 1:
                errors.append(f"Llama (Groq) API error on query '{query[:50]}...' (attempt {attempt + 1}/{max_retries}): {str(e)}")
                return ""
    
    return ""


def _query_mistral(query: str, errors: List[str]) -> str:
    """
    Execute a single query against Mistral via OpenRouter with retry logic.
    
    Args:
        query: The query string to execute
        errors: List to append error messages to
        
    Returns:
        Response string from Mistral, or empty string on failure
    """
    if not settings.OPEN_ROUTER_API_KEY:
        errors.append(f"Mistral (OpenRouter): API key not configured")
        return ""
    
    max_retries = 2
    
    for attempt in range(max_retries):
        try:
            # OpenRouter uses OpenAI-compatible API
            client = OpenAI(
                api_key=settings.OPEN_ROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1"
            )
            response = client.chat.completions.create(
                model=settings.OPENROUTER_MISTRAL_MODEL,
                messages=[{"role": "user", "content": query}],
                max_tokens=500,
                temperature=0.7
            )
            return response.choices[0].message.content or ""
            
        except Exception as e:
            if attempt == max_retries - 1:
                errors.append(f"Mistral (OpenRouter) API error on query '{query[:50]}...' (attempt {attempt + 1}/{max_retries}): {str(e)}")
                return ""
    
    return ""


def _query_qwen(query: str, errors: List[str]) -> str:
    """
    Execute a single query against Qwen via OpenRouter with retry logic.
    
    Args:
        query: The query string to execute
        errors: List to append error messages to
        
    Returns:
        Response string from Qwen, or empty string on failure
    """
    if not settings.OPEN_ROUTER_API_KEY:
        errors.append(f"Qwen (OpenRouter): API key not configured")
        return ""
    
    max_retries = 2
    
    for attempt in range(max_retries):
        try:
            # OpenRouter uses OpenAI-compatible API
            client = OpenAI(
                api_key=settings.OPEN_ROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1"
            )
            response = client.chat.completions.create(
                model=settings.OPENROUTER_QWEN_MODEL,
                messages=[{"role": "user", "content": query}],
                max_tokens=500,
                temperature=0.7
            )
            return response.choices[0].message.content or ""
            
        except Exception as e:
            if attempt == max_retries - 1:
                errors.append(f"Qwen (OpenRouter) API error on query '{query[:50]}...' (attempt {attempt + 1}/{max_retries}): {str(e)}")
                return ""
    
    return ""
