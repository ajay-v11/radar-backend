# 🎯 AI Visibility Scoring System

> Measure how frequently companies are mentioned by AI models when users search for industry-related queries.

---

## 📌 A. Problem Statement

**The Challenge**: Companies don't know if AI models like ChatGPT, Gemini, or Claude recommend them to potential customers. With 70%+ of users now asking AI for recommendations before searching Google, **AI visibility = brand awareness**.

**Key Problems:**

- No way to measure "AI visibility" across different models
- Lack of competitive intelligence on competitor mentions
- No insights into which queries trigger company mentions

---

## 📌 B. Solution Overview

### Our Approach

An **automated multi-agent system** that:

1. **Analyzes Companies** - Scrapes websites, detects industry, identifies competitors
2. **Generates Smart Queries** - Creates 20-100 realistic search queries
3. **Tests AI Models** - Executes queries across ChatGPT, Gemini, Claude, Llama
4. **Calculates Visibility** - Uses hybrid exact + semantic matching to detect mentions
5. **Provides Insights** - Shows which models mention you and competitor context

### Key Innovation: Hybrid Mention Detection

- **Exact Matching**: Fast company name detection
- **Semantic Matching**: RAG-based competitor detection using ChromaDB
  - Catches variations: "meal kit service" → HelloFresh
  - Identifies indirect mentions: "German sportswear brand" → Adidas

### Impact & Value

- 📊 Quantifiable visibility metrics (0-100% score)
- 🎯 Competitive benchmarking
- ⚡ 70% cost reduction with smart caching
- 🚀 10-50ms response time on cached requests
- 💰 Free tier available (Llama via Groq)

---

## 📌 C. Architecture Diagram

### System Architecture

```
User Request → FastAPI → Orchestration Layer → Agents → Storage
                                                  ↓
                        Phase 1: Company Analysis
                        └─> Industry Detector Agent

                        Phase 2: Visibility Analysis
                        ├─> Query Generator Agent
                        ├─> AI Model Tester Agent
                        └─> Scorer Analyzer Agent
```

### Agent Workflow

```
Company URL
    ↓
[Agent 1] Industry Detector
    → Scrape website, detect industry, identify competitors
    ↓
[Agent 2] Query Generator
    → Generate 20-100 industry-specific queries
    ↓
[Agent 3] AI Model Tester
    → Test queries on ChatGPT, Gemini, Claude, Llama
    ↓
[Agent 4] Scorer Analyzer
    → Hybrid matching, calculate visibility score
    ↓
Visibility Score + Report
```

---

## 📌 D. Tech Stack

**Backend**: FastAPI, Python 3.11+, Pydantic  
**AI/LLM**: LangChain, OpenAI, Gemini, Claude, Llama (Groq - FREE)  
**Vector DB**: ChromaDB, OpenAI Embeddings  
**Caching**: Redis (24hr industry, 1hr responses)  
**Scraping**: Firecrawl API  
**Infrastructure**: Docker Compose, Uvicorn

---

## 📌 E. How to Run

### Quick Start

```bash
# 1. Clone and install
git clone <repo-url>
cd fastapi-app
uv sync  # or: pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env and add API keys

# 3. Start databases
docker-compose up -d

# 4. Run server
uvicorn src.app:app --reload --port 8000

# 5. Access
# API: http://localhost:8000/docs
# Demo: Open demo.html in browser
```

### Test the System

```bash
python tests/test_all_models.py  # Test AI models
python tests/test_clients.py     # Test databases
```

---

## 📌 F. LLM Provider Configuration

### 🎯 Easy Provider Switching

The system uses a **centralized LLM provider system**. Switch providers in one line:

```bash
# Quick switch (recommended)
python switch_provider.py claude

# Or edit .env directly
INDUSTRY_ANALYSIS_PROVIDER=claude
QUERY_GENERATION_PROVIDER=claude
```

### Supported Providers

| Provider   | Model                 | Cost     | Speed     | Recommended For      |
| ---------- | --------------------- | -------- | --------- | -------------------- |
| **claude** | Claude 3.5 Haiku      | Low      | Fast      | ✅ **Best overall**  |
| **llama**  | Llama 3.1 8B (Groq)   | **FREE** | Very Fast | 💰 **Budget option** |
| **gemini** | Gemini 2.5 Flash Lite | Low      | Fast      | Good alternative     |
| openai     | GPT-4o-mini           | Medium   | Medium    | Requires credits     |
| grok       | Grok 4.1 Fast         | Medium   | Fast      | Via OpenRouter       |
| deepseek   | DeepSeek v3           | **FREE** | Fast      | Via OpenRouter       |

### API Keys

**Minimum Required (Choose One):**

| Service       | Purpose                 | Get Key                                                           | Cost      |
| ------------- | ----------------------- | ----------------------------------------------------------------- | --------- |
| **Anthropic** | Claude (Recommended)    | [console.anthropic.com](https://console.anthropic.com)            | Low cost  |
| **Groq**      | Llama (FREE)            | [console.groq.com](https://console.groq.com/keys)                 | FREE      |
| **Gemini**    | Gemini                  | [makersuite.google.com](https://makersuite.google.com/app/apikey) | FREE tier |
| **Firecrawl** | Web scraping (Required) | [firecrawl.dev](https://firecrawl.dev)                            | FREE tier |

**Optional (for testing AI models):**

| Service    | Purpose         | Cost              |
| ---------- | --------------- | ----------------- |
| OpenAI     | ChatGPT testing | ~$0.002/1K tokens |
| OpenRouter | Grok, DeepSeek  | Varies            |

**Environment Variables:**

```bash
# LLM Provider (choose one)
INDUSTRY_ANALYSIS_PROVIDER=claude  # or: llama, gemini, openai
QUERY_GENERATION_PROVIDER=claude   # or: llama, gemini, openai

# API Keys (at least one required)
ANTHROPIC_API_KEY=sk-ant-...       # For Claude (Recommended)
GROK_API_KEY=gsk_...               # For Llama (FREE)
GEMINI_API_KEY=...                 # For Gemini
FIRECRAWL_API_KEY=...              # Required for scraping

# Optional
OPENAI_API_KEY=sk-...              # For OpenAI
OPEN_ROUTER_API_KEY=sk-or-v1-...  # For Grok/DeepSeek
```

**Quick Commands:**

```bash
# Test your configuration
python test_llm_providers.py

# Switch providers easily
python switch_provider.py claude   # Switch to Claude
python switch_provider.py llama    # Switch to Llama (free)
```

📖 **Detailed Guide**: See `docs/LLM_PROVIDER_CONFIGURATION.md`

⚠️ **Never commit `.env` to version control!**

---

## 📌 G. Sample Inputs & Outputs

### Phase 1: Company Analysis

**Input:**

```json
POST /analyze/company
{
  "company_url": "https://hellofresh.com",
  "company_name": "HelloFresh"
}
```

**Output:**

```json
{
  "cached": false,
  "data": {
    "company_name": "HelloFresh",
    "industry": "food_services",
    "company_description": "Meal kit delivery service...",
    "competitors": ["Blue Apron", "Home Chef", "Sun Basket"]
  }
}
```

### Phase 2: Visibility Analysis

**Input:**

```json
POST /analyze/visibility
{
  "company_url": "https://hellofresh.com",
  "num_queries": 20,
  "models": ["llama", "gemini"]
}
```

**Output:**

```json
{
  "visibility_score": 75.5,
  "total_queries": 20,
  "total_mentions": 30,
  "analysis_report": {
    "by_model": {
      "llama": {
        "mentions": 16,
        "mention_rate": 0.8,
        "competitor_mentions": {"Blue Apron": 8}
      },
      "gemini": {
        "mentions": 14,
        "mention_rate": 0.7
      }
    },
    "sample_mentions": ["Query: 'best meal kits' -> Llama mentioned company"]
  }
}
```

---

## 📌 H. Demo & Screenshots

### 🎥 Video Demo

**[Video Demo Link - Coming Soon]**

### Screenshots

| Demo UI                       | API Docs                         | Performance                     |
| ----------------------------- | -------------------------------- | ------------------------------- |
| ![Demo](screenshots/demo.png) | ![API](screenshots/api-docs.png) | ![Cache](screenshots/cache.png) |

_Company analysis, visibility scoring, and cache performance_

---

## 📚 Documentation

Detailed docs in `/docs` folder:

- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - System design
- [API_ENDPOINTS.md](docs/API_ENDPOINTS.md) - API reference
- [AGENTS.md](AGENTS.md) - Agent overview

---

## 🚀 Performance

- **Cached Response**: 10-50ms
- **Cold Response**: 30-60s
- **Cost Reduction**: 70%
- **Cache Hit Rate**: 70%+
- **Supported Models**: 6+
- **Industries**: 6 categories

---

## 📧 Contact

[Your Contact Information]

---

**Built with ❤️ using FastAPI, LangChain, and ChromaDB**
