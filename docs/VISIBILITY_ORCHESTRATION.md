# Visibility Orchestration - LangGraph Workflow

## Overview

The Visibility Orchestrator is a LangGraph-based workflow that chains together 3 specialized agents to perform complete visibility analysis.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    VISIBILITY ORCHESTRATOR                       │
│                     (LangGraph Workflow)                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │  INPUT: Company Data (from Phase 1)     │
        │  - company_url                           │
        │  - company_name                          │
        │  - industry                              │
        │  - competitors                           │
        │  - query_categories_template ⭐          │
        └─────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │   AGENT 1: Query Generator               │
        │   - Uses dynamic query_categories_template│
        │   - Calculates weighted distribution     │
        │   - Generates queries per category       │
        │   - Returns: queries, query_categories   │
        └─────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │   AGENT 2: AI Model Tester               │
        │   - Tests queries across models          │
        │   - Parallel execution per query         │
        │   - Caches responses (1hr TTL)           │
        │   - Returns: model_responses             │
        └─────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │   AGENT 3: Scorer Analyzer               │
        │   - Hybrid mention detection             │
        │   - Per-category breakdown               │
        │   - Competitor rankings                  │
        │   - Returns: visibility_score, report    │
        └─────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │  OUTPUT: Complete Analysis               │
        │  - queries                               │
        │  - query_categories                      │
        │  - model_responses                       │
        │  - visibility_score                      │
        │  - analysis_report                       │
        └─────────────────────────────────────────┘
```

## Workflow Details

### Linear Flow

```
START
  ↓
generate_queries (Query Generator Agent)
  ↓
test_models (AI Model Tester Agent)
  ↓
analyze_score (Scorer Analyzer Agent)
  ↓
finalize
  ↓
END
```

### State Flow

The `VisibilityOrchestrationState` flows through all nodes:

```python
{
    # Input (from Phase 1)
    "company_url": str,
    "company_name": str,
    "company_description": str,
    "company_summary": str,
    "industry": str,
    "competitors": List[str],
    "query_categories_template": Dict,  # ⭐ Dynamic template

    # Configuration
    "num_queries": int,
    "models": List[str],
    "llm_provider": str,

    # Agent 1 Output
    "queries": List[str],
    "query_categories": Dict,

    # Agent 2 Output
    "model_responses": Dict[str, List[str]],

    # Agent 3 Output
    "visibility_score": float,
    "analysis_report": Dict,

    # Metadata
    "errors": List[str],
    "completed": bool
}
```

## Key Feature: Dynamic Query Categories

### How It Works

1. **Industry Detector** (Phase 1) generates `query_categories_template`:

```python
{
    "product_comparison": {
        "name": "Product Comparison",
        "weight": 0.30,
        "description": "Users comparing products",
        "examples": ["Amazon vs eBay", "best online marketplace"]
    },
    "product_search": {
        "name": "Product Search",
        "weight": 0.25,
        "description": "Finding specific products",
        "examples": ["buy electronics online", "best deals"]
    },
    # ... more categories
}
```

2. **Query Generator** uses this template:

   - Reads `state["query_categories_template"]`
   - Calculates distribution: `num_queries * weight` per category
   - Generates queries for each category using LLM
   - Returns organized queries by category

3. **Result**: Queries are tailored to the specific company and industry!

## Usage

### Basic Usage

```python
from agents.visibility_orchestrator import run_visibility_orchestration

# Assume you have company_data from Phase 1 (industry detection)
result = run_visibility_orchestration(
    company_data=company_data,  # Must include query_categories_template
    num_queries=20,
    models=["chatgpt", "gemini"],
    llm_provider="openai"
)

print(f"Visibility Score: {result['visibility_score']}%")
```

### With Progress Callback

```python
def progress_callback(step, status, message, data):
    print(f"[{step}] {status}: {message}")

result = run_visibility_orchestration(
    company_data=company_data,
    num_queries=20,
    models=["chatgpt", "gemini"],
    progress_callback=progress_callback
)
```

### Testing

```bash
# Test with cached company data (fast)
python test_visibility_orchestration.py

# Test with fresh industry detection (slow)
python test_visibility_orchestration.py --fresh
```

## Output Structure

```python
{
    "queries": [
        "best meal kits for families",
        "HelloFresh vs Blue Apron",
        # ... more queries
    ],

    "query_categories": {
        "comparison": {
            "name": "Product Comparison",
            "queries": ["HelloFresh vs Blue Apron", ...]
        },
        # ... more categories
    },

    "model_responses": {
        "chatgpt": ["response 1", "response 2", ...],
        "gemini": ["response 1", "response 2", ...]
    },

    "visibility_score": 85.5,

    "analysis_report": {
        "total_queries": 20,
        "total_responses": 40,
        "total_mentions": 34,
        "mention_rate": 0.85,

        "by_model": {
            "chatgpt": {
                "mentions": 18,
                "total_responses": 20,
                "mention_rate": 0.90
            },
            "gemini": {...}
        },

        "by_category": {
            "comparison": {
                "name": "Product Comparison",
                "visibility": 95.0,
                "mentions": 19,
                "total_responses": 20
            },
            # ... more categories
        },

        "competitor_rankings": {
            "overall": [
                {"name": "Blue Apron", "total_mentions": 15, "percentage": 37.5},
                {"name": "Home Chef", "total_mentions": 12, "percentage": 30.0}
            ],
            "by_category": {...}
        },

        "query_log": [...],  # Complete log of all queries and results
        "sample_mentions": [...]  # Sample mentions for review
    },

    "errors": []
}
```

## Benefits

### 1. **True Dynamic Query Generation**

- No hardcoded industry categories
- Queries tailored to specific company
- Uses LLM-generated categories from industry detector

### 2. **Simple Linear Flow**

- Easy to understand and debug
- Clear data flow between agents
- No complex branching logic

### 3. **Modular Architecture**

- Each agent is independent
- Can be tested separately
- Easy to swap or upgrade agents

### 4. **Full Observability**

- Stream progress through workflow
- Track state at each node
- Collect errors without failing

### 5. **Reusable Components**

- Each sub-agent has its own caching
- Query generator caches queries (24hr)
- Model tester caches responses (1hr)

## Integration with API

The orchestrator is designed to be called from the API controller:

```python
# In src/controllers/analysis_controller.py
from agents.visibility_orchestrator import run_visibility_orchestration

def execute_visibility_analysis(company_data, num_queries, models, llm_provider):
    """Execute visibility analysis using orchestrator."""
    return run_visibility_orchestration(
        company_data=company_data,
        num_queries=num_queries,
        models=models,
        llm_provider=llm_provider
    )
```

## Performance

- **Query Generation**: 5-10 seconds (with caching: instant)
- **Model Testing**: 20-40 seconds for 20 queries × 2 models (with caching: 5-10s)
- **Score Analysis**: 1-2 seconds
- **Total**: ~30-50 seconds cold, ~10-15 seconds warm

## Future Enhancements

1. **Parallel Model Testing**: Test all models simultaneously (not just per query)
2. **Batch Processing**: Process queries in batches for better progress tracking
3. **Conditional Edges**: Skip steps if cached
4. **Checkpointing**: Resume from failure points
5. **Metrics Collection**: Track performance per node

## Related Documentation

- [Industry Detector](./AGENT_INDUSTRY_DETECTOR.md) - Generates query_categories_template
- [Query Generator](./AGENT_QUERY_GENERATOR.md) - Uses dynamic categories
- [AI Model Tester](./AGENT_AI_MODEL_TESTER.md) - Tests queries
- [Scorer Analyzer](./AGENT_SCORER_ANALYZER.md) - Calculates visibility
- [LangGraph Migration](./LANGGRAPH_MIGRATION.md) - Architecture overview
