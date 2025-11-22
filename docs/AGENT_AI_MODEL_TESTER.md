# Agent 3: AI Model Tester

## Purpose

Tests generated queries across multiple AI models and collects their responses for visibility analysis.

## Overview

The AI Model Tester executes queries against selected AI models (ChatGPT, Gemini, Claude, Llama, etc.) and stores responses. It supports parallel batch processing and caches responses per query+model combination.

## Process Flow

```
Input: queries, models
    ↓
For each query:
  ├─> For each model:
  │   ├─> Check cache (1hr TTL)
  │   ├─> If cache miss: Query model
  │   ├─> Cache response
  │   └─> Store in model_responses
  └─> Continue to next query
    ↓
Output: model_responses {model: [responses]}
```

## Implementation

**File**: `agents/ai_model_tester.py`

**Function Signature**:

```python
def test_ai_models(state: WorkflowState) -> WorkflowState
```

**Parameters**:

- `state`: WorkflowState with `queries` and `models`

**Returns**: Updated WorkflowState with:

- `model_responses`: Dict mapping model names to response lists
- `errors`: Updated error list

## Supported Models

### 1. ChatGPT (OpenAI)

**Model**: `gpt-3.5-turbo` (configurable)
**API**: OpenAI Chat Completions
**Cost**: Low (~$0.002 per 1K tokens)

```python
def _query_chatgpt(query: str) -> str:
    llm = ChatOpenAI(
        model=settings.CHATGPT_MODEL,
        openai_api_key=settings.OPENAI_API_KEY,
        temperature=0.7,
        max_tokens=500,
        timeout=30.0
    )
    response = llm.invoke(query)
    return response.content or ""
```

### 2. Gemini (Google)

**Model**: `gemini-2.5-flash-lite` (configurable)
**API**: Google Generative AI via LangChain
**Cost**: Very low (~$0.0001 per 1K tokens)

```python
def _query_gemini(query: str) -> str:
    llm = ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL,
        google_api_key=settings.GEMINI_API_KEY,
        temperature=0.7,
        max_output_tokens=500
    )
    response = llm.invoke(query)
    return response.content or ""
```

### 3. Claude (Anthropic)

**Model**: `claude-3-haiku-20240307` (configurable)
**API**: Anthropic Messages
**Cost**: Low (~$0.0025 per 1K tokens)

```python
def _query_claude(query: str) -> str:
    llm = ChatAnthropic(
        model=settings.CLAUDE_MODEL,
        anthropic_api_key=settings.ANTHROPIC_API_KEY,
        temperature=0.7,
        max_tokens=500,
        timeout=30.0
    )
    response = llm.invoke(query)
    return response.content or ""
```

### 4. Llama (via Groq)

**Model**: `llama-3.1-8b-instant` (configurable)
**API**: Groq (OpenAI-compatible)
**Cost**: Free on Groq

```python
def _query_llama(query: str) -> str:
    llm = ChatGroq(
        model=settings.GROQ_LLAMA_MODEL,
        groq_api_key=settings.GROK_API_KEY,
        temperature=0.7,
        max_tokens=500,
        timeout=30.0
    )
    response = llm.invoke(query)
    return response.content or ""
```

### 5. Grok (via OpenRouter)

**Model**: `x-ai/grok-4.1-fast` (configurable)
**API**: OpenRouter (OpenAI-compatible)
**Cost**: Low

```python
def _query_grok(query: str) -> str:
    llm = ChatOpenAI(
        model=settings.OPENROUTER_GROK_MODEL,
        openai_api_key=settings.OPEN_ROUTER_API_KEY,
        openai_api_base="https://openrouter.ai/api/v1",
        temperature=0.7,
        max_tokens=500,
        timeout=30.0
    )
    response = llm.invoke(query)
    return response.content or ""
```

### 6. DeepSeek (via OpenRouter)

**Model**: `deepseek/deepseek-chat-v3-0324:free` (configurable)
**API**: OpenRouter (OpenAI-compatible)
**Cost**: Free tier available

```python
def _query_deepseek(query: str) -> str:
    llm = ChatOpenAI(
        model=settings.OPENROUTER_DEEPSEEK_MODEL,
        openai_api_key=settings.OPEN_ROUTER_API_KEY,
        openai_api_base="https://openrouter.ai/api/v1",
        temperature=0.7,
        max_tokens=500,
        timeout=30.0
    )
    response = llm.invoke(query)
    return response.content or ""
```

## Model Configuration

### Common Settings

```python
MAX_TOKENS = 500
TEMPERATURE = 0.7
OPENAI_TIMEOUT = 30.0
MAX_MODELS_ALLOWED = 2  # Configurable limit
DEFAULT_MODELS = ["chatgpt", "gemini"]
```

### Model Selection

Users can specify which models to test:

```python
# Request
{
    "models": ["chatgpt", "gemini", "claude"]
}

# Only first 2 models will be tested (MAX_MODELS_ALLOWED=2)
# Result: ["chatgpt", "gemini"]
```

## Response Structure

```python
model_responses = {
    "chatgpt": [
        "Response to query 1",
        "Response to query 2",
        ...
    ],
    "gemini": [
        "Response to query 1",
        "Response to query 2",
        ...
    ]
}
```

## Execution Process

### Sequential Testing

```python
def test_ai_models(state: WorkflowState) -> WorkflowState:
    queries = state.get("queries", [])
    models = state.get("models", DEFAULT_MODELS)[:MAX_MODELS_ALLOWED]
    errors = state.get("errors", [])

    # Initialize response storage
    model_responses = {model: [] for model in models}

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

    return state
```

## Caching

### Cache Strategy

**Cache Key**: `response:{md5(query+model)}`
**TTL**: 1 hour
**Storage**: Redis

### Cache Behavior

**First Run (20 queries × 2 models)**:

```
40 API calls
Cost: ~$0.10-0.50
Time: ~30-60 seconds
```

**Second Run (same queries)**:

```
~12 API calls (70% cache hit rate)
Cost: ~$0.03-0.15 (70% savings)
Time: ~10-20 seconds
```

### Implementation

```python
def _query_model_with_cache(model: str, query: str) -> str:
    # Check cache
    cache_key = f"response:{hashlib.md5(f'{query}:{model}'.encode()).hexdigest()}"
    cached = redis.get(cache_key)

    if cached:
        logger.info(f"Cache HIT for {model}: {query[:30]}...")
        return cached.decode('utf-8')

    # Cache miss - query model
    response = _query_model(model, query)

    # Cache response
    redis.setex(cache_key, 3600, response)  # 1 hour TTL

    return response
```

## Error Handling

### Missing API Keys

```python
if not settings.OPENAI_API_KEY:
    logger.error("OpenAI API key not configured")
    return ""
```

### API Failures

```python
try:
    response = llm.invoke(query)
    return response.content or ""
except Exception as e:
    logger.error(f"ChatGPT API error: {str(e)}")
    return ""  # Return empty string, don't fail workflow
```

### Unknown Models

```python
def _query_model(model: str, query: str) -> str:
    model_lower = model.lower()

    if model_lower == "chatgpt":
        return _query_chatgpt(query)
    elif model_lower == "gemini":
        return _query_gemini(query)
    # ... other models
    else:
        logger.error(f"Unknown model: {model}")
        return ""
```

## Performance

### Latency

**Per Query Per Model**: 1-3 seconds
**20 Queries × 2 Models**: 40-120 seconds
**With Caching (70% hit rate)**: 15-40 seconds

### Throughput

**Sequential**: 1 query at a time across all models
**Future Enhancement**: Parallel model testing

### Cost Optimization

**Without Caching**:

- 20 queries × 2 models = 40 API calls
- Cost: ~$0.10-0.50

**With Caching**:

- First run: 40 API calls
- Subsequent: ~12 API calls (70% cache hit)
- Cost reduction: 70%

## Configuration

### Environment Variables

```bash
# Required (at least one)
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...

# Optional
ANTHROPIC_API_KEY=sk-ant-...
GROK_API_KEY=gsk_...
OPEN_ROUTER_API_KEY=sk-or-...
```

### Settings

```python
# config/settings.py
CHATGPT_MODEL = "gpt-3.5-turbo"
GEMINI_MODEL = "gemini-2.5-flash-lite"
CLAUDE_MODEL = "claude-3-haiku-20240307"
GROQ_LLAMA_MODEL = "llama-3.1-8b-instant"
OPENROUTER_GROK_MODEL = "x-ai/grok-4.1-fast"
OPENROUTER_DEEPSEEK_MODEL = "deepseek/deepseek-chat-v3-0324:free"

MAX_TOKENS = 500
TEMPERATURE = 0.7
OPENAI_TIMEOUT = 30.0
```

## Testing

### Unit Test

```python
def test_ai_model_tester():
    state = {
        "queries": ["What is the best meal kit?", "Compare meal delivery services"],
        "models": ["chatgpt", "gemini"],
        "errors": []
    }

    result = test_ai_models(state)

    assert "model_responses" in result
    assert "chatgpt" in result["model_responses"]
    assert "gemini" in result["model_responses"]
    assert len(result["model_responses"]["chatgpt"]) == 2
    assert len(result["model_responses"]["gemini"]) == 2
```

### Integration Test

```python
def test_with_real_apis():
    state = {
        "queries": ["Test query"],
        "models": ["chatgpt"],
        "errors": []
    }

    result = test_ai_models(state)

    assert len(result["model_responses"]["chatgpt"]) == 1
    assert len(result["model_responses"]["chatgpt"][0]) > 0
```

## Common Issues

### Issue: Empty responses

**Cause**: API key not configured or API failure
**Solution**: Check API key in `.env` and verify API status

### Issue: Slow performance

**Cause**: No caching or rate limiting
**Solution**: Ensure Redis is running and cache is enabled

### Issue: Model not supported

**Cause**: Model name not recognized
**Solution**: Use supported model names: chatgpt, gemini, claude, llama, grok, deepseek

## Future Enhancements

1. **Parallel Model Testing**: Query all models simultaneously
2. **Rate Limiting**: Enforce 60 calls/min per model
3. **Retry Logic**: Automatic retry on API failures
4. **Streaming Responses**: Stream model responses as they arrive
5. **Model Comparison**: Compare response quality across models

## Related Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture
- [ORCHESTRATION.md](./ORCHESTRATION.md) - Workflow orchestration
- [AGENT_QUERY_GENERATOR.md](./AGENT_QUERY_GENERATOR.md) - Previous agent
- [AGENT_SCORER_ANALYZER.md](./AGENT_SCORER_ANALYZER.md) - Next agent
