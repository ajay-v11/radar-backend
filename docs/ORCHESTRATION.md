# Workflow Orchestration

## Overview

The AI Visibility Scoring System uses a two-phase workflow orchestration pattern that balances flexibility, performance, and user control. This document explains how agents are coordinated and how data flows through the system.

## Orchestration Pattern

### Two-Phase Architecture

```
Phase 1: Company Analysis (Isolated)
    └─> Industry Detector Agent
        └─> Output: Company profile

Phase 2: Complete Flow (Orchestrated)
    ├─> Industry Detector Agent (reuses Phase 1)
    ├─> Query Generator Agent
    ├─> AI Model Tester Agent (parallel batches)
    └─> Scorer Analyzer Agent
        └─> Output: Visibility score + report
```

### Why Two Phases?

**Phase 1 Benefits:**

- **Isolation**: Higher failure rate (scraping, broken URLs) doesn't block Phase 2
- **Verification**: User can verify company data before running expensive tests
- **Reusability**: Results cached and reused across multiple analyses
- **Enhancement**: Can be improved independently (e.g., user-provided competitors)

**Phase 2 Benefits:**

- **Orchestration**: Agents work together seamlessly
- **Optimization**: Smart caching at multiple levels
- **Flexibility**: User controls models, query count, batch size
- **Streaming**: Real-time progress updates via SSE

## Flow Diagrams

### Phase 1: Company Analysis Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER REQUEST                             │
│  POST /analyze/company                                           │
│  {                                                               │
│    "company_url": "https://hellofresh.com",                     │
│    "company_name": "HelloFresh"  // optional                    │
│  }                                                               │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CHECK CACHE                                   │
│  Key: industry_analysis:{md5(company_url)}                      │
│  TTL: 24 hours                                                   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                ┌────────┴────────┐
                │                 │
         Cache HIT          Cache MISS
                │                 │
                ▼                 ▼
    ┌──────────────────┐  ┌──────────────────────────────────────┐
    │ Return Cached    │  │  INDUSTRY DETECTOR AGENT             │
    │ JSON Instantly   │  │                                      │
    │ (~10-50ms)       │  │  1. Scrape website (Firecrawl)      │
    │                  │  │  2. Analyze with LLM (gpt-4-mini)   │
    │                  │  │  3. Extract:                         │
    │                  │  │     - Industry classification        │
    │                  │  │     - Company name, description      │
    │                  │  │     - Competitors with metadata      │
    │                  │  │  4. Store in ChromaDB                │
    │                  │  │  5. Cache results                    │
    │                  │  │                                      │
    │                  │  │  Time: ~5-10 seconds                 │
    └──────────────────┘  └──────────────────────────────────────┘
                │                 │
                │                 │ (Stream SSE events)
                │                 │
                └────────┬────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                         RESPONSE                                 │
│  {                                                               │
│    "cached": true/false,                                        │
│    "data": {                                                     │
│      "industry": "food_services",                               │
│      "company_name": "HelloFresh",                              │
│      "company_description": "...",                              │
│      "company_summary": "...",                                  │
│      "competitors": ["Blue Apron", "Home Chef", ...],          │
│      "competitors_data": [{...}, {...}]                         │
│    }                                                             │
│  }                                                               │
└─────────────────────────────────────────────────────────────────┘
```

### Phase 2: Complete Flow Orchestration

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER REQUEST                             │
│  POST /analyze/visibility                                     │
│  {                                                               │
│    "company_url": "https://hellofresh.com",                     │
│    "num_queries": 20,                                           │
│    "models": ["chatgpt", "gemini"],                             │
│    "llm_provider": "gemini",                                    │
│    "batch_size": 5                                              │
│  }                                                               │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                CHECK COMPLETE FLOW CACHE                         │
│  Key: complete_flow:{md5(url+queries+models+weights)}          │
│  TTL: 24 hours                                                   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                ┌────────┴────────┐
                │                 │
         Cache HIT          Cache MISS
                │                 │
                ▼                 ▼
    ┌──────────────────┐  ┌──────────────────────────────────────┐
    │ Return Cached    │  │  START ORCHESTRATED WORKFLOW         │
    │ JSON Instantly   │  │                                      │
    │ (~10-50ms)       │  │  Stream SSE events for progress      │
    └──────────────────┘  └──────────────────┬───────────────────┘
                                             │
                                             ▼
                         ┌─────────────────────────────────────────┐
                         │  STEP 1: INDUSTRY DETECTION             │
                         │  (Reuses Phase 1 cache if available)    │
                         │                                         │
                         │  Event: {"step": "step1", ...}          │
                         │  Time: ~2-10 seconds                    │
                         └──────────────────┬──────────────────────┘
                                            │
                                            ▼
                         ┌─────────────────────────────────────────┐
                         │  STEP 2: QUERY GENERATION               │
                         │  (Cached per company+industry+count)    │
                         │                                         │
                         │  • Select industry categories           │
                         │  • Generate queries with LLM            │
                         │  • Organize by category                 │
                         │                                         │
                         │  Event: {"step": "step2", ...}          │
                         │  Time: ~2-10 seconds                    │
                         └──────────────────┬──────────────────────┘
                                            │
                                            ▼
                         ┌─────────────────────────────────────────┐
                         │  STEP 3: PARALLEL BATCH TESTING         │
                         │                                         │
                         │  For each batch (size=5):               │
                         │    ├─> Test queries on all models       │
                         │    │   (parallel execution)              │
                         │    │   Event: {"step": "batch",          │
                         │    │           "status": "testing"}      │
                         │    │                                     │
                         │    └─> Analyze batch results            │
                         │        Event: {"step": "batch",          │
                         │                "status": "analysis"}     │
                         │                                         │
                         │  Time: ~20-40 seconds (20 queries)      │
                         └──────────────────┬──────────────────────┘
                                            │
                                            ▼
                         ┌─────────────────────────────────────────┐
                         │  STEP 4: FINAL AGGREGATION              │
                         │                                         │
                         │  • Combine all batch results            │
                         │  • Calculate overall visibility score   │
                         │  • Generate detailed report             │
                         │  • Track competitor mentions            │
                         │  • Cache complete flow results          │
                         │                                         │
                         │  Event: {"step": "step4", ...}          │
                         │  Time: ~1-2 seconds                     │
                         └──────────────────┬──────────────────────┘
                                            │
                                            ▼
                         ┌─────────────────────────────────────────┐
                         │  FINAL RESPONSE                         │
                         │                                         │
                         │  Event: {"step": "complete",            │
                         │          "status": "success",           │
                         │          "data": {                      │
                         │            "visibility_score": 75.5,    │
                         │            "analysis_report": {...}     │
                         │          }}                             │
                         └─────────────────────────────────────────┘
```

## Agent Coordination

### Sequential Execution

Agents execute in strict order within Phase 2:

```python
# Simplified orchestration logic
async def complete_flow_stream(request):
    state = initialize_state(request)

    # Step 1: Industry Detection
    state = detect_industry(state, llm_provider=request.llm_provider)
    yield emit("step1", "completed", state)

    # Step 2: Query Generation
    state = generate_queries(state, num_queries=request.num_queries)
    yield emit("step2", "completed", state)

    # Step 3: Parallel Batch Testing
    for batch in batches(state["queries"], request.batch_size):
        batch_state = test_ai_models(batch, request.models)
        yield emit("batch", "testing_completed", batch_state)

        batch_state = analyze_score(batch_state)
        yield emit("batch", "analysis_completed", batch_state)

    # Step 4: Final Aggregation
    final_state = analyze_score(state)
    yield emit("step4", "completed", final_state)

    # Cache and return
    cache_complete_flow(request, final_state)
    yield emit("complete", "success", final_state)
```

### Parallel Execution

Within Step 3, queries are tested across models in parallel batches:

```python
# Batch processing
batch_size = 5
queries = ["query1", "query2", ..., "query20"]
models = ["chatgpt", "gemini"]

for i in range(0, len(queries), batch_size):
    batch_queries = queries[i:i+batch_size]

    # Test all models for this batch
    # (models are tested sequentially, but could be parallelized)
    for model in models:
        for query in batch_queries:
            response = query_model(model, query)
            # Cached per query+model
```

## State Management

### WorkflowState Evolution

The state object accumulates data as it flows through agents:

```python
# Initial state
state = {
    "company_url": "https://hellofresh.com",
    "company_name": "",
    "num_queries": 20,
    "models": ["chatgpt", "gemini"],
    "errors": []
}

# After Industry Detector
state = {
    ...previous,
    "industry": "food_services",
    "company_name": "HelloFresh",
    "company_description": "...",
    "competitors": ["Blue Apron", ...]
}

# After Query Generator
state = {
    ...previous,
    "queries": ["query1", "query2", ...],
    "query_categories": {...}
}

# After AI Model Tester
state = {
    ...previous,
    "model_responses": {
        "chatgpt": ["response1", ...],
        "gemini": ["response1", ...]
    }
}

# After Scorer Analyzer
state = {
    ...previous,
    "visibility_score": 75.5,
    "analysis_report": {...}
}
```

### State Immutability

Each agent receives the state, adds data, and returns the updated state:

```python
def agent_function(state: WorkflowState) -> WorkflowState:
    # Read from state
    input_data = state.get("some_field")

    # Process
    output_data = process(input_data)

    # Update state (non-destructive)
    state["new_field"] = output_data

    # Return updated state
    return state
```

## Error Handling

### Non-Blocking Errors

Agents continue execution even when errors occur:

```python
def detect_industry(state):
    errors = state.get("errors", [])

    try:
        # Attempt scraping
        content = scrape_website(state["company_url"])
    except Exception as e:
        errors.append(f"Scraping failed: {e}")
        content = ""  # Continue with empty content

    # Fallback to keyword matching
    if not content:
        industry = fallback_keyword_detection(state)

    state["errors"] = errors
    return state
```

### Error Propagation

Errors are collected in `state["errors"]` and included in the final response:

```json
{
  "visibility_score": 45.0,
  "analysis_report": {...},
  "errors": [
    "Scraping failed: Timeout",
    "ChatGPT API error on query 'best meal kits'"
  ]
}
```

## Streaming Events

### Server-Sent Events (SSE)

Phase 2 streams progress updates to the client:

```python
def emit(step: str, status: str, data: dict = None, message: str = ""):
    event = {
        "step": step,
        "status": status,
        "message": message,
        "data": data or {}
    }
    return f"data: {json.dumps(event)}\n\n"

# Usage
yield emit("step1", "started", message="Starting industry detection...")
yield emit("step1", "completed", data={"industry": "food_services"})
yield emit("batch", "testing_started", data={"batch_num": 1, "progress": 0})
yield emit("complete", "success", data=final_result)
```

### Event Types

**Step Events:**

- `step1`: Industry detection
- `step2`: Query generation
- `step3`: Batch testing
- `step4`: Final aggregation
- `complete`: Workflow complete

**Batch Events:**

- `batch.testing_started`: Batch testing begins
- `batch.testing_completed`: Batch testing done
- `batch.analysis_started`: Batch analysis begins
- `batch.analysis_completed`: Batch analysis done

**Status Values:**

- `started`: Step/batch started
- `in_progress`: Step/batch in progress
- `completed`: Step/batch completed
- `success`: Workflow succeeded
- `failed`: Workflow failed
- `warning`: Non-blocking error

## Caching Integration

### Cache Checks

Each phase checks its cache before executing:

```python
# Phase 1: Company Analysis
cached = _get_cached_industry_analysis(company_url)
if cached:
    return {"cached": True, "data": cached}
else:
    # Stream analysis
    return StreamingResponse(analyze_company_stream(...))

# Phase 2: Complete Flow
cached = _get_cached_complete_flow(request)
if cached:
    return {"cached": True, "data": cached}
else:
    # Stream workflow
    return StreamingResponse(complete_flow_stream(...))
```

### Granular Caching

Within Phase 2, each step has its own cache:

```python
# Step 1: Industry detection (uses Phase 1 cache)
cached_industry = _get_cached_industry_analysis(url)
if cached_industry:
    state.update(cached_industry)
else:
    state = detect_industry(state)

# Step 2: Query generation (separate cache)
cached_queries = _get_cached_queries(url, industry, num_queries)
if cached_queries:
    state.update(cached_queries)
else:
    state = generate_queries(state)

# Step 3: Model testing (per-query cache)
for query in queries:
    cached_response = _get_cached_response(query, model)
    if cached_response:
        response = cached_response
    else:
        response = query_model(model, query)
        _cache_response(query, model, response)
```

## Performance Optimization

### Batch Processing

Queries are processed in batches to provide incremental progress:

```python
batch_size = 5  # Configurable
total_batches = ceil(len(queries) / batch_size)

for batch_num, i in enumerate(range(0, len(queries), batch_size), 1):
    batch_queries = queries[i:i+batch_size]
    progress = (i / len(queries)) * 100

    yield emit("batch", "testing_started", {
        "batch_num": batch_num,
        "total_batches": total_batches,
        "progress": progress
    })

    # Process batch
    batch_results = test_batch(batch_queries, models)

    yield emit("batch", "testing_completed", {
        "batch_num": batch_num,
        "results": batch_results
    })
```

### Parallel Model Testing

Within each batch, models can be tested in parallel (future enhancement):

```python
# Current: Sequential
for model in models:
    response = query_model(model, query)

# Future: Parallel
import asyncio
responses = await asyncio.gather(*[
    query_model_async(model, query)
    for model in models
])
```

## Monitoring & Debugging

### Logging

Each agent logs its execution:

```python
logger.info(f"Industry detection started for {company_url}")
logger.info(f"Cache HIT for queries: {company_url}")
logger.warning(f"Scraping failed, using fallback: {error}")
logger.error(f"ChatGPT API error: {error}")
```

### Metrics

Track orchestration performance:

```python
metrics = {
    "phase1_duration": 5.2,  # seconds
    "phase2_duration": 32.1,
    "cache_hit_rate": 0.75,
    "total_api_calls": 42,
    "error_count": 2
}
```

### Tracing

Each request has a unique ID for tracing:

```python
request_id = str(uuid.uuid4())
logger.info(f"[{request_id}] Starting workflow")
logger.info(f"[{request_id}] Step 1 completed")
```

## Testing

### Unit Testing

Test each agent independently:

```python
def test_industry_detector():
    state = {"company_url": "https://test.com", "errors": []}
    result = detect_industry(state)
    assert result["industry"] in VALID_INDUSTRIES
```

### Integration Testing

Test the complete workflow:

```python
def test_complete_flow():
    request = CompleteFlowRequest(
        company_url="https://test.com",
        num_queries=20,
        models=["chatgpt"]
    )

    events = []
    async for event in complete_flow_stream(request):
        events.append(event)

    assert any("complete" in e for e in events)
```

### Cache Testing

Verify caching behavior:

```python
def test_cache_hit():
    # First request (cache miss)
    result1 = analyze_company(url)
    assert result1["cached"] == False

    # Second request (cache hit)
    result2 = analyze_company(url)
    assert result2["cached"] == True
    assert result2["data"] == result1["data"]
```

## Related Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture
- [API_ENDPOINTS.md](./API_ENDPOINTS.md) - API reference
- Individual agent docs:
  - [AGENT_INDUSTRY_DETECTOR.md](./AGENT_INDUSTRY_DETECTOR.md)
  - [AGENT_QUERY_GENERATOR.md](./AGENT_QUERY_GENERATOR.md)
  - [AGENT_AI_MODEL_TESTER.md](./AGENT_AI_MODEL_TESTER.md)
  - [AGENT_SCORER_ANALYZER.md](./AGENT_SCORER_ANALYZER.md)
