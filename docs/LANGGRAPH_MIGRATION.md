# LangGraph Migration - Agent Workflows

## Overview

All four agents have been converted to modular LangGraph-based workflows for better maintainability, observability, and extensibility.

## Agent Structure

Each agent follows a consistent folder structure:

```
agents/<agent_name>_agent/
├── __init__.py          # Entry point, exports main workflow function
├── graph.py             # LangGraph workflow definition
├── models.py            # Pydantic models and TypedDict state
├── nodes.py             # Node functions (workflow steps)
└── utils.py             # Helper functions and utilities
```

## Agent 1: Industry Detection Agent ✅

**Location**: `agents/industry_detection_agent/`

**Entry Point**: `run_industry_detection_workflow()`

**Workflow**:

```
START
  ├─> scrape_company (parallel)
  └─> scrape_competitors (parallel)
       ↓
  combine_content
       ↓
  classify_industry (dynamic, no constraints)
       ↓
  generate_template (industry-specific extraction)
       ↓
  extract_data (using template)
       ↓
  generate_query_categories (company-specific)
       ↓
  enrich_competitors
       ↓
  finalize
       ↓
  END
```

**Key Features**:

- Parallel scraping (company + competitors)
- Dynamic industry classification (no hardcoded lists)
- Generates extraction templates on-the-fly
- Creates query categories for query generator
- 24hr caching

## Agent 2: Query Generator Agent ✅

**Location**: `agents/query_generator_agent/`

**Entry Point**: `run_query_generation_workflow()`

**Workflow**:

```
START
  ↓
check_cache
  ↓ (if cache miss)
calculate_distribution
  ↓
generate_queries (for all categories)
  ↓
cache_results
  ↓
finalize
  ↓
END
```

**Key Features**:

- Uses dynamic query_categories_template from industry detector
- Weighted distribution across categories
- LLM-based query generation per category
- Deduplication across categories
- 24hr caching

**Integration with Industry Detector**:

```python
# Industry detector generates query categories
query_categories_template = {
    "comparison": {
        "name": "Product Comparison",
        "weight": 0.30,
        "description": "Users comparing products",
        "examples": ["HelloFresh vs Blue Apron"]
    },
    # ... more categories
}

# Query generator uses these categories
result = run_query_generation_workflow(
    query_categories_template=query_categories_template,
    # ... other params
)
```

## Agent 3: AI Model Tester Agent ✅

**Location**: `agents/ai_model_tester_agent/`

**Entry Point**: `run_ai_model_testing_workflow()`

**Workflow**:

```
START
  ↓
initialize (setup response storage)
  ↓
test_queries (parallel testing per query)
  ↓
finalize
  ↓
END
```

**Key Features**:

- Parallel model testing (all models per query)
- Response caching (1hr TTL)
- Supports 6 models: ChatGPT, Gemini, Claude, Llama, Grok, DeepSeek
- Graceful error handling (empty response on failure)

## Agent 4: Scorer Analyzer Agent ✅

**Location**: `agents/scorer_analyzer_agent/`

**Entry Point**: `run_scorer_analysis_workflow()`

**Workflow**:

```
START
  ↓
initialize (build query-category mapping)
  ↓
analyze (analyze all responses for mentions)
  ↓
calculate (calculate score and build report)
  ↓
finalize
  ↓
END
```

**Key Features**:

- Hybrid mention detection (exact + semantic)
- Per-category visibility breakdown
- Competitor rankings (overall + per-category)
- Rank/position tracking
- Complete query log with detailed results

## Usage Examples

### Industry Detection

```python
from agents.industry_detection_agent import run_industry_detection_workflow

result = run_industry_detection_workflow(
    company_url="https://hellofresh.com",
    competitor_urls={"Blue Apron": "https://blueapron.com"},
    llm_provider="openai",
    progress_callback=lambda step, status, msg, data: print(msg)
)

# Returns: industry, query_categories_template, competitors, etc.
```

### Query Generation

```python
from agents.query_generator_agent import run_query_generation_workflow

result = run_query_generation_workflow(
    company_url="https://hellofresh.com",
    company_name="HelloFresh",
    industry="AI-Powered Meal Kit Delivery",
    competitors=["Blue Apron", "Home Chef"],
    query_categories_template=industry_result["query_categories_template"],
    num_queries=20,
    llm_provider="openai"
)

# Returns: queries, query_categories
```

### AI Model Testing

```python
from agents.ai_model_tester_agent import run_ai_model_testing_workflow

result = run_ai_model_testing_workflow(
    queries=["best meal kits", "HelloFresh vs Blue Apron"],
    models=["chatgpt", "gemini"]
)

# Returns: model_responses
```

### Scorer Analysis

```python
from agents.scorer_analyzer_agent import run_scorer_analysis_workflow

result = run_scorer_analysis_workflow(
    company_name="HelloFresh",
    queries=queries,
    model_responses=model_responses,
    query_categories=query_categories,
    competitors=["Blue Apron", "Home Chef"]
)

# Returns: visibility_score, analysis_report
```

## Benefits of LangGraph Architecture

### 1. Modularity

- Each node is a separate function
- Easy to test individual steps
- Clear separation of concerns

### 2. Observability

- Stream workflow execution
- Track progress in real-time
- Debug specific nodes

### 3. Extensibility

- Add new nodes easily
- Modify workflow without breaking existing code
- Conditional edges for complex logic

### 4. Maintainability

- Consistent structure across agents
- Self-documenting workflow graphs
- Easy to understand data flow

### 5. Reusability

- Singleton graph instances
- Shared utility functions
- Consistent state management

## Migration Notes

### Old vs New

**Old (Function-based)**:

```python
from agents.query_generator import generate_queries

state = {"company_url": "...", "industry": "..."}
state = generate_queries(state, num_queries=20)
```

**New (LangGraph-based)**:

```python
from agents.query_generator_agent import run_query_generation_workflow

result = run_query_generation_workflow(
    company_url="...",
    industry="...",
    query_categories_template={...},
    num_queries=20
)
```

### Backward Compatibility

The old agent files (`agents/query_generator.py`, etc.) can remain for backward compatibility, but new code should use the LangGraph versions.

## Testing

Each agent can be tested independently:

```python
# Test industry detection
python -c "
from agents.industry_detection_agent import run_industry_detection_workflow
result = run_industry_detection_workflow('https://hellofresh.com')
print(result['industry'])
"

# Test query generation
python -c "
from agents.query_generator_agent import run_query_generation_workflow
result = run_query_generation_workflow(
    company_url='https://hellofresh.com',
    company_name='HelloFresh',
    industry='Meal Kit Delivery',
    competitors=['Blue Apron'],
    query_categories_template={'comparison': {'name': 'Comparison', 'weight': 1.0, 'description': 'Compare', 'examples': []}},
    num_queries=5
)
print(len(result['queries']))
"
```

## Next Steps

1. Update main orchestration to use new LangGraph agents
2. Add visualization for workflow graphs
3. Implement workflow checkpointing for long-running tasks
4. Add metrics collection per node
5. Create integration tests for full pipeline

## Documentation

- **Industry Detector**: `docs/AGENT_INDUSTRY_DETECTOR.md`
- **Query Generator**: `docs/AGENT_QUERY_GENERATOR.md` (needs update)
- **AI Model Tester**: `docs/AGENT_AI_MODEL_TESTER.md` (needs update)
- **Scorer Analyzer**: `docs/AGENT_SCORER_ANALYZER.md` (needs update)
