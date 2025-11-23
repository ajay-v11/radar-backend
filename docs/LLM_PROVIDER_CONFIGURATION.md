# LLM Provider Configuration Guide

## Overview

The system now has a centralized LLM provider management system that makes it easy to switch between different AI models for different tasks.

## Quick Start

### 1. Configure Providers in `.env`

```bash
# Choose which provider to use for each task
INDUSTRY_ANALYSIS_PROVIDER=claude
QUERY_GENERATION_PROVIDER=claude
```

### 2. Supported Providers

| Provider   | Model                 | Cost     | Speed     | Notes                          |
| ---------- | --------------------- | -------- | --------- | ------------------------------ |
| `claude`   | Claude 3.5 Haiku      | Low      | Fast      | **Recommended** - Best balance |
| `gemini`   | Gemini 2.5 Flash Lite | Low      | Fast      | Good alternative               |
| `llama`    | Llama 3.1 8B          | **FREE** | Very Fast | Via Groq (free tier)           |
| `openai`   | GPT-4o-mini           | Medium   | Medium    | Requires credits               |
| `grok`     | Grok 4.1 Fast         | Medium   | Fast      | Via OpenRouter                 |
| `deepseek` | DeepSeek v3           | **FREE** | Fast      | Via OpenRouter                 |

### 3. Required API Keys

Add the API keys for the providers you want to use:

```bash
# At least one is required
ANTHROPIC_API_KEY=sk-ant-...        # For Claude
GEMINI_API_KEY=AIza...              # For Gemini
GROK_API_KEY=gsk_...                # For Llama (Groq)
OPEN_ROUTER_API_KEY=sk-or-v1-...   # For Grok/DeepSeek
OPENAI_API_KEY=sk-proj-...          # For OpenAI
```

## Configuration Options

### Per-Task Configuration

You can configure different providers for different tasks:

```bash
# Use Claude for analysis (more accurate)
INDUSTRY_ANALYSIS_PROVIDER=claude

# Use Llama for query generation (faster, free)
QUERY_GENERATION_PROVIDER=llama
```

### Available Tasks

1. **Industry Analysis** (`INDUSTRY_ANALYSIS_PROVIDER`)

   - Industry classification
   - Company data extraction
   - Competitor analysis
   - Query category generation
   - **Recommended**: `claude` or `gemini`

2. **Query Generation** (`QUERY_GENERATION_PROVIDER`)
   - Search query generation
   - Creative content generation
   - **Recommended**: `claude`, `llama`, or `gemini`

## Model Customization

You can also customize the specific model for each provider in `.env`:

```bash
# Default models (already optimized for cost/performance)
CLAUDE_MODEL=claude-3-5-haiku-20241022
GEMINI_MODEL=gemini-2.5-flash-lite
GROQ_LLAMA_MODEL=llama-3.1-8b-instant
CHATGPT_MODEL=gpt-4o-mini
```

## Cost Optimization

### Free Options

For zero-cost operation, use:

```bash
INDUSTRY_ANALYSIS_PROVIDER=llama
QUERY_GENERATION_PROVIDER=llama
GROK_API_KEY=gsk_...  # Free tier available
```

### Budget-Friendly

For best quality at low cost:

```bash
INDUSTRY_ANALYSIS_PROVIDER=claude
QUERY_GENERATION_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-...
```

Claude 3.5 Haiku is extremely cost-effective and high-quality.

### Mixed Strategy

Use expensive models only where needed:

```bash
# Accurate analysis with Claude
INDUSTRY_ANALYSIS_PROVIDER=claude

# Fast, free query generation with Llama
QUERY_GENERATION_PROVIDER=llama
```

## Troubleshooting

### "API key not configured" Error

Make sure you have the API key for your chosen provider:

```bash
# If using Claude
ANTHROPIC_API_KEY=sk-ant-your-key-here

# If using Llama
GROK_API_KEY=gsk-your-key-here
```

### "Quota exceeded" Error

Your API key has run out of credits. Either:

1. Add credits to your account
2. Switch to a different provider
3. Use a free provider like `llama` or `deepseek`

### Provider Not Available

Check that:

1. The provider name is spelled correctly
2. You have the API key configured
3. The API key is valid and has credits

## Advanced Usage

### Programmatic Provider Selection

You can also pass the provider when calling the API:

```bash
curl -X POST http://localhost:8000/analyze/company \
  -H "Content-Type: application/json" \
  -d '{
    "company_url": "https://example.com",
    "llm_provider": "gemini"
  }'
```

This overrides the default from `.env`.

### Check Available Providers

The system automatically detects which providers are available based on configured API keys.

## Recommendations

### For Production

```bash
INDUSTRY_ANALYSIS_PROVIDER=claude
QUERY_GENERATION_PROVIDER=claude
```

Claude 3.5 Haiku offers the best balance of quality, speed, and cost.

### For Development/Testing

```bash
INDUSTRY_ANALYSIS_PROVIDER=llama
QUERY_GENERATION_PROVIDER=llama
```

Llama via Groq is free and fast, perfect for testing.

### For Maximum Quality

```bash
INDUSTRY_ANALYSIS_PROVIDER=claude
QUERY_GENERATION_PROVIDER=claude
# Or upgrade to more powerful models:
CLAUDE_MODEL=claude-3-5-sonnet-20241022
```

## Getting API Keys

- **Claude**: https://console.anthropic.com/
- **Gemini**: https://aistudio.google.com/app/apikey
- **Llama (Groq)**: https://console.groq.com/keys (FREE)
- **OpenRouter**: https://openrouter.ai/keys (Grok, DeepSeek)
- **OpenAI**: https://platform.openai.com/api-keys
