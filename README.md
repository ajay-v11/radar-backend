# AI Visibility Scoring System

A FastAPI-based service that analyzes a company's visibility across AI models by detecting its industry, generating relevant queries, testing those queries across multiple AI models, and calculating visibility scores.

## Features

- **Industry Detection**: Automatically classifies companies into industry categories
- **Query Generation**: Creates 20 industry-specific search queries per analysis
- **Multi-Model Testing**: Tests queries across ChatGPT and Claude
- **Visibility Scoring**: Calculates how often companies appear in AI responses
- **RAG Storage**: In-memory storage for company profiles and query templates
- **LangGraph Orchestration**: Sequential multi-agent workflow management

## Quick Start

### Prerequisites

- Python 3.12+
- OpenAI API key
- Anthropic API key

### Installation

1. Clone the repository
2. Install dependencies:

   ```bash
   uv sync
   ```

3. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

### Running the Server

```bash
uvicorn main:app --reload
```

The server will start at `http://localhost:8000`

### API Documentation

Once the server is running, visit:

- Interactive API docs: `http://localhost:8000/docs`
- Alternative docs: `http://localhost:8000/redoc`

## API Endpoints

### Health Check

```bash
GET /health
```

Returns system status and version.

### Analyze Company

```bash
POST /analyze
Content-Type: application/json

{
  "company_url": "https://example.com",
  "company_name": "Example Corp",
  "company_description": "Brief description of the company"
}
```

Returns:

```json
{
  "job_id": "unique-job-id",
  "status": "completed",
  "industry": "technology",
  "visibility_score": 75.5,
  "total_queries": 20,
  "total_mentions": 15,
  "model_results": {
    "by_model": {
      "chatgpt": {
        "mentions": 8,
        "mention_rate": 0.8
      },
      "claude": {
        "mentions": 7,
        "mention_rate": 0.7
      }
    },
    "sample_mentions": ["..."]
  }
}
```

## Architecture

The system uses a multi-agent architecture orchestrated by LangGraph:

1. **Industry Detector Agent**: Classifies the company's industry
2. **Query Generator Agent**: Creates industry-specific queries
3. **AI Model Tester Agent**: Executes queries across AI models
4. **Scorer Analyzer Agent**: Calculates visibility scores

## Supported Industries

- Technology
- Retail
- Healthcare
- Finance
- Food Services
- Other

## Testing

Run the integration tests:

```bash
# Test workflow structure (no API keys needed)
python test_workflow_structure.py

# Test complete integration (requires API keys)
python test_complete_integration.py
```

## Project Structure

```
.
├── main.py                 # FastAPI application
├── graph_orchestrator.py   # LangGraph workflow
├── agents/                 # Agent implementations
│   ├── industry_detector.py
│   ├── query_generator.py
│   ├── ai_model_tester.py
│   └── scorer_analyzer.py
├── models/                 # Data schemas
│   └── schemas.py
├── storage/                # RAG store
│   └── rag_store.py
├── config/                 # Configuration
│   └── settings.py
└── utils/                  # Utilities
    └── helpers.py
```

## Configuration

Environment variables (set in `.env`):

- `OPENAI_API_KEY`: OpenAI API key for ChatGPT
- `ANTHROPIC_API_KEY`: Anthropic API key for Claude
- `CHATGPT_MODEL`: ChatGPT model to use (default: gpt-3.5-turbo)
- `CLAUDE_MODEL`: Claude model to use (default: claude-3-sonnet-20240229)
- `NUM_QUERIES`: Number of queries to generate (default: 20)

## Development

The system is built with:

- FastAPI for the REST API
- LangGraph for workflow orchestration
- Pydantic for data validation
- OpenAI and Anthropic SDKs for AI model integration
