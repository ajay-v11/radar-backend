# Category-Based Batching Workflow

## Overview

The visibility orchestrator now processes queries **category-by-category** instead of all at once, providing progressive results and better UX.

## Workflow

```
START
  ↓
initialize_categories (setup queue, distribution)
  ↓
┌─→ select_next_category
│   ↓
│   generate_category_queries (5-10 queries for this category)
│   ↓
│   test_category_models (parallel testing across all models)
│   ↓
│   analyze_category_results (calculate category score)
│   ↓
│   aggregate_category_results (update running totals, stream progress)
│   ↓
└───[more categories?] YES → loop back
    │
    NO
    ↓
finalize_results
    ↓
END
```

## Key Features

### 1. Progressive Results

- User sees results after each category completes
- No waiting for entire pipeline
- Real-time feedback: "Comparison: 85%, Pricing: 60%..."

### 2. Streaming Progress

After each category completes, the system emits:

```json
{
  "step": "category_complete",
  "status": "completed",
  "message": "Category 'comparison' complete! Partial score: 72.5%",
  "data": {
    "category": "comparison",
    "category_score": 85.0,
    "completed_categories": 2,
    "total_categories": 7,
    "progress": "2/7",
    "partial_visibility_score": 72.5,
    "total_queries": 15,
    "total_mentions": 42,
    "category_breakdown": [...]
  }
}
```

### 3. Cancellable

- User can stop mid-process
- Partial results are preserved
- Running totals show progress so far

### 4. Aggregation

State tracks:

- `category_queries` - Queries per category
- `category_responses` - Responses per category
- `category_scores` - Score per category
- `category_mentions` - Mentions per category
- `total_queries` - Running total
- `total_mentions` - Running total
- `partial_visibility_score` - Updates after each category

### 5. Parallelism

Within each category:

- All models tested in parallel
- Fast batch processing
- Efficient resource usage

## State Management

```python
{
  # Category tracking
  "categories_to_process": ["comparison", "pricing", "best-of"],
  "current_category": "comparison",
  "completed_categories": [],
  "category_distribution": {"comparison": 10, "pricing": 8, ...},

  # Per-category results
  "category_queries": {"comparison": [...], "pricing": [...]},
  "category_responses": {"comparison": {...}, "pricing": {...}},
  "category_scores": {"comparison": 85.0, "pricing": 60.0},
  "category_mentions": {"comparison": 17, "pricing": 12},

  # Running totals
  "total_queries": 18,
  "total_mentions": 29,
  "total_responses": 72,
  "partial_visibility_score": 72.5,

  # Final output (aggregated)
  "queries": [...],  # All queries
  "model_responses": {...},  # All responses
  "visibility_score": 72.5,
  "analysis_report": {
    "category_breakdown": [...]
  }
}
```

## Benefits

✅ **Better UX** - Progressive feedback instead of long wait
✅ **Cancellable** - Stop anytime, keep partial results
✅ **Transparent** - See which categories perform well
✅ **Efficient** - Parallel testing within categories
✅ **Debuggable** - Clear per-category metrics
✅ **Scalable** - Easy to add more categories

## Example User Experience

```
[10:00:00] Initialized 7 categories
[10:00:01] Category 'comparison': Generated 10 queries
[10:00:05] Category 'comparison': Tested 40 responses
[10:00:06] Category 'comparison': 85% visibility (17 mentions)
[10:00:06] ✓ Category 'comparison' complete! Partial score: 85%

[10:00:07] Category 'pricing': Generated 8 queries
[10:00:10] Category 'pricing': Tested 32 responses
[10:00:11] Category 'pricing': 60% visibility (12 mentions)
[10:00:11] ✓ Category 'pricing' complete! Partial score: 72.5%

... continues for each category ...

[10:00:45] ✓ Visibility analysis complete! Final score: 68.3%
```

## Implementation Notes

- Reuses existing agent logic (query gen, model test, scorer)
- LangGraph handles loop control with conditional edges
- State accumulation is simple dict updates
- Streaming happens naturally through graph.stream()
- No breaking changes to API - same input/output format
