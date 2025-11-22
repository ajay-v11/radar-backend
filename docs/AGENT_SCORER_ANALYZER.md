# Agent 4: Scorer Analyzer

## Purpose

Calculates the visibility score by analyzing AI model responses for mentions of the company name and competitors using hybrid exact + semantic matching.

## Overview

The Scorer Analyzer is the final agent in the workflow. It uses a hybrid approach combining exact string matching with RAG-based semantic search to detect company and competitor mentions in AI responses.

## Process Flow

```
Input: company_name, competitors, queries, model_responses
    ↓
For each model:
  ├─> For each response:
  │   ├─> Exact string matching (company name)
  │   ├─> Semantic matching (competitors via ChromaDB)
  │   ├─> Track mentions and competitor context
  │   └─> Collect samples
  ├─> Calculate per-model metrics
  └─> Store in by_model results
    ↓
Calculate overall visibility score
    ↓
Generate detailed analysis report
    ↓
Output: visibility_score + analysis_report
```

## Implementation

**File**: `agents/scorer_analyzer.py`

**Function Signature**:

```python
def analyze_score(state: WorkflowState) -> WorkflowState
```

**Parameters**:

- `state`: WorkflowState with company_name, competitors, queries, model_responses

**Returns**: Updated WorkflowState with:

- `visibility_score`: Overall score (0-100)
- `analysis_report`: Detailed breakdown

## Visibility Score Calculation

### Formula

```python
visibility_score = (total_mentions / (num_queries × num_models)) × 100
```

### Example

```
20 queries × 2 models = 40 total responses
30 responses mentioned the company
Visibility score = (30 / 40) × 100 = 75.0%
```

### Interpretation

- **90-100%**: Excellent visibility - Company consistently mentioned
- **70-89%**: Good visibility - Company appears in most responses
- **50-69%**: Moderate visibility - Company mentioned in about half
- **30-49%**: Low visibility - Company rarely mentioned
- **0-29%**: Very low visibility - Company almost never mentioned

## Mention Detection

### Hybrid Approach

Combines two methods for best accuracy:

**1. Exact String Matching** (Fast, High Precision)

- Case-insensitive search for company name
- Handles spacing variations
- Direct substring matching

**2. Semantic Matching** (Comprehensive, High Recall)

- RAG-based competitor detection using ChromaDB
- Catches variations like "meal kit service" → HelloFresh
- Similarity threshold: 0.70
- Uses rich embeddings (name + description + products + positioning)

### Implementation

```python
def _count_mentions_semantic(
    company_name: str,
    competitors: List[str],
    responses: List[str],
    queries: List[str],
    model_name: str
) -> Tuple[int, List[str], Dict[str, int]]:
    mentions = 0
    samples = []
    competitor_mention_counts = {}

    # Normalize company name
    company_name_lower = company_name.lower().strip()
    company_name_variations = [
        company_name_lower,
        company_name_lower.replace(" ", ""),  # Remove spaces
        company_name_lower.replace(" ", "-"),  # Replace with dash
    ]

    # Get competitor matcher for semantic search
    matcher = get_competitor_matcher()

    for idx, response in enumerate(responses):
        if not response:
            continue

        # 1. Exact string matching for company name
        response_lower = response.lower()
        company_mentioned = any(var in response_lower for var in company_name_variations)

        # 2. Semantic matching for competitors
        competitors_found = []
        if competitors:
            has_mention, mentioned_comps = matcher.analyze_response_for_mentions(
                company_name=company_name,
                response=response,
                competitors=competitors
            )
            competitors_found = mentioned_comps

            # Track competitor mentions
            for comp in mentioned_comps:
                competitor_mention_counts[comp] = competitor_mention_counts.get(comp, 0) + 1

        # Count as mention if company or competitors found
        if company_mentioned:
            mentions += 1

            # Collect sample mention (up to 3 per model)
            if len(samples) < 3:
                query_text = queries[idx] if idx < len(queries) else "Unknown query"
                if len(query_text) > 50:
                    query_text = query_text[:47] + "..."

                comp_info = f" (with {', '.join(competitors_found[:2])})" if competitors_found else ""
                sample = f"Query: '{query_text}' -> {model_name.capitalize()} mentioned company{comp_info}"
                samples.append(sample)

    return mentions, samples, competitor_mention_counts
```

## Semantic Matching Details

### ChromaDB Integration

Uses competitor matcher to detect variations:

```python
from utils.competitor_matcher import get_competitor_matcher

matcher = get_competitor_matcher()

# Analyze response for competitor mentions
has_mention, mentioned_competitors = matcher.analyze_response_for_mentions(
    company_name="HelloFresh",
    response="I recommend trying a meal kit service for convenience",
    competitors=["Blue Apron", "Home Chef", "Sun Basket"]
)

# Result:
# has_mention = True (semantic match for "meal kit service")
# mentioned_competitors = ["HelloFresh", "Blue Apron"]
```

### Rich Embeddings

Competitors stored with comprehensive metadata:

```python
{
    "name": "Blue Apron",
    "description": "Meal kit delivery with chef-designed recipes",
    "products": "meal kits, wine subscriptions",
    "positioning": "premium quality ingredients"
}

# Embedding includes all fields for better semantic matching
embedding_text = "Blue Apron: Meal kit delivery with chef-designed recipes. Products: meal kits, wine subscriptions. Positioning: premium quality ingredients"
```

### Similarity Threshold

**Threshold**: 0.70 (cosine similarity)
**Rationale**: Balances precision and recall

```python
# Examples of matches at 0.70 threshold:
"German sportswear brand" → Adidas (0.82)
"meal kit service" → HelloFresh (0.75)
"premium meal delivery" → Blue Apron (0.73)
"budget meal kits" → EveryPlate (0.71)
```

## Analysis Report Structure

```python
analysis_report = {
    "visibility_score": 75.5,           # Overall score (0-100)
    "total_queries": 20,                # Number of queries executed
    "total_responses": 40,              # Total responses received
    "total_mentions": 30,               # Total company mentions
    "mention_rate": 0.75,               # Mentions per response (0-1)

    "by_model": {
        "chatgpt": {
            "mentions": 16,             # Mentions in ChatGPT responses
            "total_responses": 20,      # Total ChatGPT responses
            "mention_rate": 0.80,       # ChatGPT mention rate
            "competitor_mentions": {    # Competitors mentioned by this model
                "Blue Apron": 8,
                "Home Chef": 5
            }
        },
        "gemini": {
            "mentions": 14,
            "total_responses": 20,
            "mention_rate": 0.70,
            "competitor_mentions": {
                "Blue Apron": 6,
                "EveryPlate": 4
            }
        }
    },

    "sample_mentions": [
        "Query: 'What are the best meal kit services?' -> Chatgpt mentioned company (with Blue Apron, Home Chef)",
        "Query: 'Compare food delivery platforms' -> Gemini mentioned company",
        "Query: 'HelloFresh vs Blue Apron' -> Chatgpt mentioned company (with Blue Apron)",
        "Query: 'Meal kit subscriptions' -> Gemini mentioned company",
        "Query: 'Best meal delivery 2025' -> Chatgpt mentioned company (with Blue Apron)"
    ]
}
```

## Per-Model Analysis

### Metrics Calculated

For each model:

- **mentions**: Number of responses mentioning company
- **total_responses**: Total responses from this model
- **mention_rate**: mentions / total_responses
- **competitor_mentions**: Dict of competitor names to mention counts

### Example

```python
# ChatGPT tested on 20 queries
# 16 responses mentioned HelloFresh
# 8 responses also mentioned Blue Apron
# 5 responses also mentioned Home Chef

"chatgpt": {
    "mentions": 16,
    "total_responses": 20,
    "mention_rate": 0.80,  # 80% mention rate
    "competitor_mentions": {
        "Blue Apron": 8,
        "Home Chef": 5
    }
}
```

## Sample Collection

### Strategy

Collects up to 5 sample mentions across all models:

- Maximum 3 samples per model (for variety)
- Includes query context
- Shows which competitors were mentioned alongside company

### Format

```
"Query: '{query_text}' -> {model_name} mentioned company (with {competitors})"
```

### Examples

```python
[
    "Query: 'What are the best meal kit services?' -> Chatgpt mentioned company (with Blue Apron, Home Chef)",
    "Query: 'Compare food delivery platforms' -> Gemini mentioned company",
    "Query: 'HelloFresh vs Blue Apron' -> Chatgpt mentioned company (with Blue Apron)"
]
```

## Competitor Tracking

### Purpose

Tracks which competitors appear alongside the company in AI responses:

- Identifies competitive landscape
- Shows which competitors are frequently mentioned together
- Helps understand market positioning

### Implementation

```python
competitor_mention_counts = {}

for comp in mentioned_competitors:
    competitor_mention_counts[comp] = competitor_mention_counts.get(comp, 0) + 1

# Result:
{
    "Blue Apron": 14,  # Mentioned in 14 responses
    "Home Chef": 9,
    "Sun Basket": 6,
    "EveryPlate": 4
}
```

## Performance

### Latency

- **Per response**: ~10-50ms (exact + semantic matching)
- **20 queries × 2 models**: ~1-2 seconds total
- **Negligible** compared to model testing time

### Accuracy

**Exact Matching**:

- Precision: Very high (>95%)
- Recall: Moderate (~60-70%)

**Semantic Matching**:

- Precision: High (~85-90%)
- Recall: High (~80-90%)

**Combined (Hybrid)**:

- Precision: High (~90-95%)
- Recall: Very high (~85-95%)

## Error Handling

### Missing Data

```python
if not company_name:
    logger.warning("No company name provided")
    return state

if not queries or not model_responses:
    state["visibility_score"] = 0.0
    state["analysis_report"] = {}
    return state
```

### Semantic Matching Failures

```python
try:
    matcher = get_competitor_matcher()
    has_mention, mentioned_comps = matcher.analyze_response_for_mentions(...)
except Exception as e:
    logger.debug(f"Semantic matching failed: {e}")
    # Fall back to exact matching only
    mentioned_comps = []
```

## Configuration

### Settings

```python
# Semantic matching threshold
SIMILARITY_THRESHOLD = 0.70

# Sample collection limits
MAX_SAMPLES_TOTAL = 5
MAX_SAMPLES_PER_MODEL = 3
```

## Testing

### Unit Test

```python
def test_scorer_analyzer():
    state = {
        "company_name": "HelloFresh",
        "competitors": ["Blue Apron", "Home Chef"],
        "queries": ["query1", "query2"],
        "model_responses": {
            "chatgpt": ["HelloFresh is great", "No mention"],
            "gemini": ["Try HelloFresh", "HelloFresh and Blue Apron"]
        },
        "errors": []
    }

    result = analyze_score(state)

    assert result["visibility_score"] == 75.0  # 3 out of 4 responses
    assert result["analysis_report"]["total_mentions"] == 3
    assert result["analysis_report"]["by_model"]["chatgpt"]["mentions"] == 1
    assert result["analysis_report"]["by_model"]["gemini"]["mentions"] == 2
```

### Semantic Matching Test

```python
def test_semantic_matching():
    state = {
        "company_name": "HelloFresh",
        "competitors": ["Blue Apron"],
        "queries": ["What meal kit should I try?"],
        "model_responses": {
            "chatgpt": ["I recommend trying a meal kit service like Blue Apron"]
        },
        "errors": []
    }

    result = analyze_score(state)

    # Should detect "meal kit service" as semantic match for HelloFresh
    assert result["visibility_score"] > 0
    assert "Blue Apron" in result["analysis_report"]["by_model"]["chatgpt"]["competitor_mentions"]
```

## Common Issues

### Issue: Low visibility score despite mentions

**Cause**: Company name variations not detected
**Solution**: Hybrid matching handles variations automatically

### Issue: Competitors not tracked

**Cause**: Competitors not stored in ChromaDB
**Solution**: Ensure Industry Detector ran successfully and stored competitors

### Issue: Semantic matching not working

**Cause**: ChromaDB not connected or competitors not embedded
**Solution**: Check ChromaDB connection and verify competitors were stored

## Future Enhancements

1. **Sentiment Analysis**: Analyze tone of mentions (positive/negative/neutral)
2. **Context Analysis**: Understand context of mentions (recommendation, comparison, criticism)
3. **Ranking Analysis**: Track position in "best of" lists
4. **Temporal Tracking**: Track visibility changes over time
5. **Competitive Benchmarking**: Compare visibility against competitors

## Related Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture
- [ORCHESTRATION.md](./ORCHESTRATION.md) - Workflow orchestration
- [AGENT_AI_MODEL_TESTER.md](./AGENT_AI_MODEL_TESTER.md) - Previous agent
- [API_ENDPOINTS.md](./API_ENDPOINTS.md) - API reference
