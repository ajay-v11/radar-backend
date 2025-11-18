# AI Visibility Scoring System - Agents Documentation

## Overview

This document provides a comprehensive guide to all agents in the AI Visibility Scoring System. The system uses a multi-agent architecture orchestrated by LangGraph to analyze company visibility across various AI models.

## Architecture

The system consists of **4 specialized agents** that work together in a sequential workflow:

```
Input (Company Info)
    ↓
[1] Industry Detector Agent
    ↓
[2] Query Generator Agent
    ↓
[3] AI Model Tester Agent
    ↓
[4] Scorer Analyzer Agent
    ↓
Output (Visibility Score & Report)
```

### Workflow State Management

All agents share a common `WorkflowState` that flows through the pipeline:

```python
WorkflowState = {
    "company_url": str,           # Company website URL
    "company_name": str,          # Company name
    "company_description": str,   # Business description
    "industry": str,              # Detected industry category
    "queries": List[str],         # Generated search queries
    "models": List[str],          # AI models to test
    "model_responses": Dict,      # Responses from each model
    "visibility_score": float,    # Final visibility score (0-100)
    "analysis_report": Dict,      # Detailed analysis results
    "errors": List[str]           # Error messages
}
```

---

## Agent 1: Industry Detector

**File:** `agents/industry_detector.py`

### Purpose

Analyzes company information and classifies it into an industry category using keyword-based pattern matching.

### Function Signature

```python
def detect_industry(state: WorkflowState) -> WorkflowState
```

### Input Requirements

- `company_name`: Company name
- `company_description`: Description of the company's business

### Output

- `industry`: Detected industry classification

### Supported Industries

The agent can classify companies into the following categories:

1. **Technology**

   - Keywords: software, tech, saas, cloud, ai, machine learning, data, analytics, platform, app, digital, cybersecurity, IT, developer, API, web, mobile, hardware, semiconductor, automation, robotics, IoT
   - Examples: Software companies, SaaS platforms, tech startups

2. **Retail**

   - Keywords: retail, store, shop, ecommerce, marketplace, fashion, clothing, apparel, consumer goods, boutique, supermarket, grocery, wholesale, distribution
   - Examples: Online stores, fashion brands, supermarkets

3. **Healthcare**

   - Keywords: health, medical, hospital, clinic, pharmaceutical, biotech, drug, therapy, patient, doctor, wellness, fitness, telemedicine, diagnostic, laboratory
   - Examples: Hospitals, pharma companies, health tech

4. **Finance**

   - Keywords: finance, bank, investment, insurance, fintech, payment, credit, loan, wealth, trading, stock, accounting, cryptocurrency, blockchain
   - Examples: Banks, fintech startups, investment firms

5. **Food Services**

   - Keywords: food, restaurant, dining, meal, catering, delivery, cafe, coffee, bakery, bar, hospitality, culinary, meal kit, food service
   - Examples: Restaurants, meal delivery services, catering companies

6. **Other**
   - Default category when no clear match is found

### Algorithm

1. **Text Preparation**: Combines company name and description into lowercase text
2. **Keyword Extraction**: Splits text into individual words and preserves full text for phrase matching
3. **Scoring System**:
   - Single-word matches: +1 point
   - Multi-word phrase matches: +2 points (higher weight)
4. **Classification**: Selects industry with highest score, defaults to "other" if no matches

### Example Usage

```python
state = {
    "company_name": "HelloFresh",
    "company_description": "Meal kit delivery service providing fresh ingredients"
}

result = detect_industry(state)
# result["industry"] = "food_services"
```

### Error Handling

- Gracefully handles missing or empty company information
- Returns "other" when no clear industry match is found

---

## Agent 2: Query Generator

**File:** `agents/query_generator.py`

### Purpose

Generates industry-specific search queries for AI model testing by retrieving templates from the RAG Store and customizing them with company-specific information.

### Function Signature

```python
def generate_queries(state: WorkflowState) -> WorkflowState
```

### Input Requirements

- `industry`: Detected industry category (from Industry Detector)
- `company_name`: Company name for query customization

### Output

- `queries`: List of exactly 20 customized search queries

### Process Flow

1. **Template Retrieval**

   - Fetches industry-specific query templates from RAG Store
   - Falls back to "other" industry templates if none found for specific industry

2. **Template Selection**

   - Randomly samples 20 unique templates to ensure variety
   - Logs warning if fewer than 20 templates available

3. **Query Customization**
   - Analyzes each query for comparison keywords (best, top, leading, compare, recommend)
   - 30% chance to insert company name as reference point in comparison queries
   - Maintains query variety by selective customization

### Query Customization Logic

```python
# Example transformations:
"What are the best meal delivery services?"
→ "What are the best meal delivery services like HelloFresh?"

"Compare top food delivery platforms"
→ "Compare top food delivery platforms similar to HelloFresh"
```

### Example Output

For a food services company, generates queries like:

- "What are the best meal kit delivery services?"
- "How do meal delivery subscriptions work?"
- "Compare HelloFresh to other meal kit companies"
- "What are healthy meal delivery options?"
- "Best food delivery services for families"
- ... (20 total queries)

### Error Handling

- Logs errors when templates are unavailable
- Falls back to default templates
- Warns when fewer than 20 templates exist

---

## Agent 3: AI Model Tester

**File:** `agents/ai_model_tester.py`

### Purpose

Executes all generated queries against selected AI models and collects their responses for visibility analysis.

### Function Signature

```python
def test_ai_models(state: WorkflowState) -> WorkflowState
```

### Input Requirements

- `queries`: List of search queries (from Query Generator)
- `models`: List of AI models to test (optional, defaults to ["chatgpt", "gemini"])

### Output

- `model_responses`: Dictionary mapping model names to response lists

### Supported AI Models

1. **ChatGPT** (OpenAI)

   - Model: `gpt-4o-mini` (configurable)
   - API: OpenAI Chat Completions
   - Max tokens: 500
   - Temperature: 0.7

2. **Claude** (Anthropic)

   - Model: `claude-3-5-sonnet-20241022` (configurable)
   - API: Anthropic Messages
   - Max tokens: 500

3. **Gemini** (Google)

   - Model: `gemini-1.5-flash` (configurable)
   - API: Google Generative AI via LangChain
   - Max tokens: 500
   - Temperature: 0.7

4. **Llama** (via Groq)

   - Model: `llama-3.3-70b-versatile` (configurable)
   - API: Groq (OpenAI-compatible)
   - Max tokens: 500
   - Temperature: 0.7

5. **Mistral** (via OpenRouter)

   - Model: `mistralai/mistral-large` (configurable)
   - API: OpenRouter (OpenAI-compatible)
   - Max tokens: 500
   - Temperature: 0.7

6. **Qwen** (via OpenRouter)
   - Model: `qwen/qwen-2.5-72b-instruct` (configurable)
   - API: OpenRouter (OpenAI-compatible)
   - Max tokens: 500
   - Temperature: 0.7

### Execution Process

1. **Initialization**: Creates response storage for each model
2. **Query Execution**: For each query, executes against all selected models
3. **Response Collection**: Stores responses in structured format
4. **Error Tracking**: Logs API failures and configuration issues

### Retry Logic

Each model query includes automatic retry on failure:

- **Max retries**: 2 attempts
- **Error logging**: Captures error details on final failure
- **Graceful degradation**: Returns empty string on failure, continues with other queries

### Response Structure

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
    ],
    ...
}
```

### Error Handling

- **Missing API Keys**: Logs error and skips model
- **API Failures**: Retries once, then logs error and returns empty response
- **Unknown Models**: Logs error for unsupported model names
- **Network Issues**: Captured in error log with query context

### Configuration Requirements

Each model requires specific API keys in environment variables:

- ChatGPT: `OPENAI_API_KEY`
- Claude: `ANTHROPIC_API_KEY`
- Gemini: `GEMINI_API_KEY`
- Llama: `GROK_API_KEY` (Groq)
- Mistral/Qwen: `OPEN_ROUTER_API_KEY`

---

## Agent 4: Scorer Analyzer

**File:** `agents/scorer_analyzer.py`

### Purpose

Calculates the visibility score by analyzing AI model responses for mentions of the company name and generates a detailed analysis report.

### Function Signature

```python
def analyze_score(state: WorkflowState) -> WorkflowState
```

### Input Requirements

- `company_name`: Company name to search for
- `queries`: List of queries executed
- `model_responses`: Responses from all AI models

### Output

- `visibility_score`: Overall visibility score (0-100)
- `analysis_report`: Detailed breakdown of results

### Visibility Score Calculation

The visibility score represents the percentage of AI model responses that mentioned the company:

```
visibility_score = (total_mentions / (num_queries × num_models)) × 100
```

**Example:**

- 20 queries × 2 models = 40 total responses
- 30 responses mentioned the company
- Visibility score = (30 / 40) × 100 = 75.0%

### Analysis Process

1. **Mention Detection**

   - Case-insensitive search for company name in each response
   - Counts total mentions across all models

2. **Per-Model Analysis**

   - Calculates mentions and mention rate for each model
   - Identifies which models mention the company most frequently

3. **Sample Collection**

   - Collects up to 5 sample mentions across all models
   - Includes query context for each sample
   - Limits to 3 samples per model for variety

4. **Report Generation**
   - Compiles comprehensive statistics
   - Provides actionable insights

### Analysis Report Structure

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
            "mention_rate": 0.80        # ChatGPT mention rate
        },
        "gemini": {
            "mentions": 14,
            "total_responses": 20,
            "mention_rate": 0.70
        }
    },

    "sample_mentions": [
        "Query: 'What are the best meal kit services?' -> Chatgpt mentioned company",
        "Query: 'Compare food delivery platforms' -> Gemini mentioned company",
        ...
    ]
}
```

### Mention Detection Algorithm

```python
def _count_mentions(company_name, responses, queries, model_name):
    1. Normalize company name to lowercase
    2. For each response:
        a. Check if company name appears (case-insensitive)
        b. Increment mention counter
        c. Collect sample (up to 3 per model)
    3. Return mention count and samples
```

### Interpretation Guide

- **90-100%**: Excellent visibility - Company is consistently mentioned
- **70-89%**: Good visibility - Company appears in most responses
- **50-69%**: Moderate visibility - Company mentioned in about half of responses
- **30-49%**: Low visibility - Company rarely mentioned
- **0-29%**: Very low visibility - Company almost never mentioned

### Error Handling

- Handles empty or missing responses gracefully
- Returns 0 score if no queries or models available
- Continues analysis even if some responses are empty

---

## Workflow Orchestration

**File:** `graph_orchestrator.py`

### Purpose

Manages the sequential execution of all agents using LangGraph's StateGraph.

### Key Functions

#### 1. create_workflow_graph()

Creates and compiles the LangGraph workflow:

```python
def create_workflow_graph() -> StateGraph:
    workflow = StateGraph(WorkflowState)

    # Add agent nodes
    workflow.add_node("industry_detector", detect_industry)
    workflow.add_node("query_generator", generate_queries)
    workflow.add_node("ai_model_tester", test_ai_models)
    workflow.add_node("scorer_analyzer", analyze_score)

    # Define sequential flow
    workflow.set_entry_point("industry_detector")
    workflow.add_edge("industry_detector", "query_generator")
    workflow.add_edge("query_generator", "ai_model_tester")
    workflow.add_edge("ai_model_tester", "scorer_analyzer")
    workflow.add_edge("scorer_analyzer", END)

    return workflow.compile()
```

#### 2. run_analysis()

Main entry point for executing the complete workflow:

```python
def run_analysis(
    company_url: str,
    company_name: str = "",
    company_description: str = "",
    models: list = None
) -> WorkflowState
```

**Parameters:**

- `company_url`: Company website URL (required)
- `company_name`: Company name (optional)
- `company_description`: Business description (optional)
- `models`: List of AI models to test (optional, defaults to ["chatgpt", "gemini"])

**Returns:** Complete WorkflowState with all analysis results

### Execution Flow

```
1. Initialize WorkflowState with input data
2. Execute Industry Detector
   └─> Detect industry category
3. Execute Query Generator
   └─> Generate 20 industry-specific queries
4. Execute AI Model Tester
   └─> Test queries against all selected models
5. Execute Scorer Analyzer
   └─> Calculate visibility score and generate report
6. Return final state with all results
```

### Example Usage

```python
from graph_orchestrator import run_analysis

result = run_analysis(
    company_url="https://hellofresh.com",
    company_name="HelloFresh",
    company_description="Meal kit delivery service",
    models=["chatgpt", "gemini", "claude"]
)

print(f"Industry: {result['industry']}")
print(f"Visibility Score: {result['visibility_score']}%")
print(f"Total Mentions: {result['analysis_report']['total_mentions']}")
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Initial Input                            │
│  • company_url                                               │
│  • company_name                                              │
│  • company_description                                       │
│  • models (optional)                                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Agent 1: Industry Detector                      │
│  Input:  company_name, company_description                   │
│  Output: industry                                            │
│  Logic:  Keyword-based classification                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Agent 2: Query Generator                        │
│  Input:  industry, company_name                              │
│  Output: queries (20 items)                                  │
│  Logic:  RAG template retrieval + customization              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Agent 3: AI Model Tester                        │
│  Input:  queries, models                                     │
│  Output: model_responses                                     │
│  Logic:  Execute queries against each AI model               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Agent 4: Scorer Analyzer                        │
│  Input:  company_name, queries, model_responses              │
│  Output: visibility_score, analysis_report                   │
│  Logic:  Count mentions + calculate metrics                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                     Final Output                             │
│  • industry                                                  │
│  • visibility_score                                          │
│  • analysis_report (detailed breakdown)                      │
│  • errors (if any)                                           │
└─────────────────────────────────────────────────────────────┘
```

---

## Error Handling Strategy

All agents follow consistent error handling principles:

### 1. Non-Blocking Errors

- Agents continue execution even when encountering errors
- Errors are logged to `state["errors"]` list
- Partial results are still returned

### 2. Graceful Degradation

- Missing API keys: Skip that model, continue with others
- API failures: Retry once, then return empty response
- Missing templates: Fall back to default templates

### 3. Error Logging

All errors include context:

```python
errors.append(f"ChatGPT API error on query '{query[:50]}...' (attempt 2/2): {str(e)}")
```

### 4. State Preservation

- Errors don't corrupt workflow state
- Downstream agents can still execute
- Final report includes error summary

---

## Performance Considerations

### Query Execution Time

- **Per query per model**: ~1-3 seconds
- **Total for 20 queries × 2 models**: ~40-120 seconds
- **Total for 20 queries × 6 models**: ~120-360 seconds

### Optimization Strategies

1. **Parallel Execution**: Models could be queried in parallel (future enhancement)
2. **Caching**: Repeated queries could be cached
3. **Batch Processing**: Multiple companies could be analyzed in batches

### Resource Usage

- **Memory**: Minimal (stores ~20 queries × N models × ~500 tokens)
- **API Costs**: Varies by model and usage
- **Network**: Dependent on API response times

---

## Configuration

### Environment Variables

Required API keys (configure in `.env`):

```bash
# OpenAI (ChatGPT)
OPENAI_API_KEY=sk-...

# Anthropic (Claude)
ANTHROPIC_API_KEY=sk-ant-...

# Google (Gemini)
GEMINI_API_KEY=...

# Groq (Llama)
GROK_API_KEY=gsk_...

# OpenRouter (Mistral, Qwen)
OPEN_ROUTER_API_KEY=sk-or-...
```

### Model Configuration

Default models and settings in `config/settings.py`:

```python
DEFAULT_MODELS = ["chatgpt", "gemini"]
CHATGPT_MODEL = "gpt-4o-mini"
CLAUDE_MODEL = "claude-3-5-sonnet-20241022"
GEMINI_MODEL = "gemini-1.5-flash"
GROQ_LLAMA_MODEL = "llama-3.3-70b-versatile"
OPENROUTER_MISTRAL_MODEL = "mistralai/mistral-large"
OPENROUTER_QWEN_MODEL = "qwen/qwen-2.5-72b-instruct"
```

---

## Testing

### Unit Testing

Each agent can be tested independently:

```python
# Test Industry Detector
state = {"company_name": "Test", "company_description": "Software company"}
result = detect_industry(state)
assert result["industry"] == "technology"

# Test Query Generator
state = {"industry": "technology", "company_name": "Test"}
result = generate_queries(state)
assert len(result["queries"]) == 20

# Test Scorer Analyzer
state = {
    "company_name": "Test",
    "queries": ["q1", "q2"],
    "model_responses": {"chatgpt": ["Test is great", "No mention"]}
}
result = analyze_score(state)
assert result["visibility_score"] == 50.0
```

### Integration Testing

Full workflow testing in `test_complete_integration.py`

---

## Future Enhancements

### Potential Improvements

1. **Parallel Model Execution**: Query all models simultaneously
2. **Advanced NLP**: Use embeddings for more sophisticated mention detection
3. **Sentiment Analysis**: Analyze tone of mentions (positive/negative/neutral)
4. **Competitive Analysis**: Compare visibility against competitors
5. **Historical Tracking**: Track visibility changes over time
6. **Custom Query Templates**: Allow users to provide their own query templates
7. **Multi-language Support**: Test queries in different languages
8. **Response Caching**: Cache API responses to reduce costs

---

## Troubleshooting

### Common Issues

**Issue**: Industry detected as "other"

- **Cause**: Company description doesn't match keyword patterns
- **Solution**: Provide more detailed company description with industry-specific terms

**Issue**: Low visibility score

- **Cause**: Company not well-known or queries not relevant
- **Solution**: Review generated queries, consider adding company to RAG store

**Issue**: API errors for specific model

- **Cause**: Missing or invalid API key
- **Solution**: Check `.env` file and verify API key is valid

**Issue**: Empty responses from model

- **Cause**: API rate limiting or service issues
- **Solution**: Check error logs, retry after delay, or exclude problematic model

---

## Summary

The AI Visibility Scoring System uses a sophisticated multi-agent architecture to analyze company visibility across AI models. Each agent has a specific responsibility:

1. **Industry Detector**: Classifies companies into industry categories
2. **Query Generator**: Creates relevant search queries
3. **AI Model Tester**: Executes queries across multiple AI platforms
4. **Scorer Analyzer**: Calculates visibility metrics and generates reports

The system is designed for reliability, extensibility, and ease of use, with comprehensive error handling and detailed reporting capabilities.
