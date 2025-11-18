# Implementation Plan

- [x] 1. Set up project structure and configuration

  - Create directory structure for config/, agents/, models/, storage/, and utils/
  - Implement config/settings.py with Pydantic Settings for environment variables (OPENAI_API_KEY, ANTHROPIC_API_KEY, model names, NUM_QUERIES)
  - Create .env.example file with placeholder values for required environment variables
  - Add **init**.py files to all package directories
  - _Requirements: 9.1, 9.2, 9.3, 9.4_

- [x] 2. Implement data models and schemas

  - Create models/schemas.py with all Pydantic models: AnalyzeRequest, AnalyzeResponse, HealthResponse, WorkflowState (TypedDict), CompanyProfile, CompetitorProfile
  - Add type hints and validation rules to all model fields
  - Include HttpUrl validation for company_url field
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 1.2_

- [x] 3. Implement RAG Store for in-memory data storage

  - Create storage/rag_store.py with RAGStore class
  - Implement store_company(), get_company(), store_competitors(), and get_query_templates() methods
  - Implement initialize_templates() method with pre-populated query templates for all supported industries (technology, retail, healthcare, finance, food_services)
  - Create at least 25 query templates per industry to ensure 20 unique queries can be generated
  - Use Python dictionaries for in-memory storage of companies, competitors, and query templates
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 4. Implement Industry Detector Agent

  - Create agents/industry_detector.py with detect_industry() function
  - Implement keyword-based industry classification logic for technology, retail, healthcare, finance, food_services, and other
  - Extract keywords from company_name and company_description fields
  - Match keywords against industry patterns and return best match
  - Update WorkflowState with detected industry
  - _Requirements: 3.1, 3.2, 3.3_

- [x] 5. Implement Query Generator Agent

  - Create agents/query_generator.py with generate_queries() function
  - Retrieve query templates from RAG Store based on detected industry
  - Customize templates by replacing placeholders with company name and context
  - Generate exactly 20 unique queries
  - Update WorkflowState with queries list
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 6. Implement AI Model Tester Agent

  - Create agents/ai_model_tester.py with test_ai_models() function
  - Integrate OpenAI API client for ChatGPT (using gpt-3.5-turbo or gpt-4)
  - Integrate Anthropic API client for Claude (using claude-3-sonnet)
  - Execute each query against both AI models and collect responses
  - Implement error handling with single retry on API failures
  - Log errors to state.errors list and continue workflow
  - Store responses in format: {model_name: [response1, response2, ...]}
  - Update WorkflowState with model_responses dictionary
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 7. Implement Scorer Analyzer Agent

  - Create agents/scorer_analyzer.py with analyze_score() function
  - Implement logic to search for company name in each AI model response (case-insensitive)
  - Count total mentions across all responses
  - Calculate visibility score: (total*mentions / (num_queries * num*models)) * 100
  - Generate detailed analysis report with visibility_score, total_queries, total_responses, total_mentions, mention_rate, by_model breakdown, and sample_mentions
  - Update WorkflowState with visibility_score and analysis_report
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 8. Implement LangGraph Orchestrator

  - Create graph_orchestrator.py with create_workflow_graph() function
  - Define LangGraph StateGraph with WorkflowState schema
  - Add nodes for all four agents: industry_detector, query_generator, ai_model_tester, scorer_analyzer
  - Connect nodes in sequential order with edges
  - Set industry_detector as entry point and scorer_analyzer as finish point
  - Implement run_analysis() function that initializes state and executes the workflow
  - Return final state with all results
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 9. Implement FastAPI server with endpoints

  - Update main.py to create FastAPI application instance
  - Implement GET /health endpoint that returns HealthResponse with status and version
  - Implement POST /analyze endpoint that accepts AnalyzeRequest and returns AnalyzeResponse
  - Validate company_url format using Pydantic validation
  - Call run_analysis() from graph_orchestrator in /analyze endpoint
  - Generate unique job_id for each analysis request
  - Map workflow results to AnalyzeResponse format
  - Implement error handling for invalid URLs (400) and internal errors (500)
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 10. Add utility functions and helpers

  - Create utils/helpers.py with common utility functions
  - Implement generate_job_id() function for creating unique identifiers
  - Add any shared helper functions used across agents
  - _Requirements: 8.4_

- [x] 11. Wire everything together and test end-to-end
  - Initialize RAGStore singleton instance and load query templates on application startup
  - Verify all imports and dependencies are correctly configured
  - Test complete workflow from API request to final response
  - Verify that all four agents execute in sequence and pass state correctly
  - Validate that the final response includes all required fields: job_id, status, industry, visibility_score, total_queries, total_mentions, model_results
  - _Requirements: 1.1, 2.5, 6.4_
