# Agents Summary

Quick reference for the 5 LangGraph-based agents in the system.

## Agent 1: Industry Detector

- **Module**: `agents/industry_detection_agent/`
- **Nodes**: 9 (scrape company, scrape competitors, combine, classify, generate template, extract, generate categories, enrich, finalize)
- **Purpose**: Dynamic industry classification + custom query categories
- **Key Output**: `query_categories_template` (used by query generator)
- **Cache**: Route-level only (24hr TTL)

## Agent 2: Query Generator

- **Module**: `agents/query_generator_agent/`
- **Nodes**: 5 (check cache, calculate distribution, generate queries, cache results, finalize)
- **Purpose**: Generate queries using dynamic categories from Industry Detector
- **Key Feature**: No hardcoded categories, weighted distribution
- **Cache**: Route-level only (24hr TTL)

## Agent 3: AI Model Tester

- **Module**: `agents/ai_model_tester_agent/`
- **Nodes**: 3 (initialize responses, test queries batch, finalize)
- **Purpose**: Test queries across multiple AI models (parallel per query)
- **Models**: ChatGPT, Gemini, Claude, Llama, Grok, DeepSeek
- **Cache**: Route-level only (24hr TTL)

## Agent 4: Scorer Analyzer

- **Module**: `agents/scorer_analyzer_agent/`
- **Nodes**: 4 (initialize analysis, analyze responses, calculate score, finalize)
- **Purpose**: Calculate visibility score with hybrid matching
- **Method**: Exact string + semantic via ChromaDB (threshold 0.70)
- **Output**: Score (0-100) + detailed report with per-model and per-category breakdowns

## Agent 5: Visibility Orchestrator

- **Module**: `agents/visibility_orchestrator/`
- **Nodes**: 7 with conditional looping (initialize, select, generate, test, analyze, aggregate, finalize)
- **Purpose**: Orchestrate agents 2-4 with category-based batching
- **Key Feature**: Progressive results streamed after each category completes
- **Flow**: For each category → generate queries → test models → analyze → aggregate → (loop or finalize)

## Workflow

```
Phase 1: Company Analysis
  └─> Industry Detector

Phase 2: Visibility Analysis
  └─> Visibility Orchestrator
      ├─> Query Generator (per category)
      ├─> AI Model Tester (per category)
      └─> Scorer Analyzer (per category)
```

## All Agents Use LangGraph

- Modular node-based workflows
- Observable state flow
- Non-blocking error handling
- Progress streaming support
- Singleton graph instances
