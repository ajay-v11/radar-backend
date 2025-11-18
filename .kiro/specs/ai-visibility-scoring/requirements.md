# Requirements Document

## Introduction

The AI Visibility Scoring System is a FastAPI-based service that analyzes a company's visibility across AI models by detecting its industry, generating relevant queries, testing those queries across multiple AI models, and calculating visibility scores. The system uses LangGraph to orchestrate a multi-agent workflow and includes a RAG system for storing company and competitor data.

## Glossary

- **Visibility Score System**: The complete FastAPI application that orchestrates AI model testing and scoring
- **LangGraph Orchestrator**: The workflow engine that manages the sequential execution of analysis agents
- **Industry Detector Agent**: The component that identifies the business industry category from company information
- **Query Generator Agent**: The component that creates search queries relevant to the detected industry
- **AI Model Tester Agent**: The component that executes queries across multiple AI models and collects responses
- **Scorer Analyzer Agent**: The component that calculates visibility scores based on AI model responses
- **RAG Store**: The storage system for company profiles, competitor data, and query templates
- **Company Profile**: A data structure containing company URL, name, description, and industry classification
- **Visibility Score**: A numerical metric representing how frequently a company appears in AI model responses

## Requirements

### Requirement 1

**User Story:** As a business analyst, I want to submit a company URL for analysis, so that I can understand the company's visibility across AI models

#### Acceptance Criteria

1. WHEN a user sends a POST request with a company URL, THE Visibility Score System SHALL accept the request and return a job identifier
2. THE Visibility Score System SHALL validate that the company URL is properly formatted before processing
3. IF the company URL is invalid, THEN THE Visibility Score System SHALL return an error response with status code 400
4. THE Visibility Score System SHALL provide a health check endpoint that returns system status

### Requirement 2

**User Story:** As a system administrator, I want the analysis workflow to execute in a defined sequence, so that each step builds on the previous step's output

#### Acceptance Criteria

1. THE LangGraph Orchestrator SHALL execute the Industry Detector Agent as the first step in the workflow
2. WHEN the Industry Detector Agent completes, THE LangGraph Orchestrator SHALL pass the industry classification to the Query Generator Agent
3. WHEN the Query Generator Agent completes, THE LangGraph Orchestrator SHALL pass the generated queries to the AI Model Tester Agent
4. WHEN the AI Model Tester Agent completes, THE LangGraph Orchestrator SHALL pass the test results to the Scorer Analyzer Agent
5. THE LangGraph Orchestrator SHALL maintain state data throughout the workflow execution

### Requirement 3

**User Story:** As a data analyst, I want the system to detect the company's industry, so that relevant queries can be generated for that specific sector

#### Acceptance Criteria

1. THE Industry Detector Agent SHALL analyze the company profile and determine the business industry category
2. THE Industry Detector Agent SHALL return the detected industry classification to the workflow state
3. THE Industry Detector Agent SHALL support common industry categories including technology, retail, healthcare, finance, and food services

### Requirement 4

**User Story:** As a marketing researcher, I want the system to generate industry-specific queries, so that the AI model testing reflects realistic search scenarios

#### Acceptance Criteria

1. THE Query Generator Agent SHALL create a minimum of 20 search queries based on the detected industry
2. THE Query Generator Agent SHALL retrieve industry-specific query templates from the RAG Store
3. THE Query Generator Agent SHALL customize query templates with the company name and relevant context
4. THE Query Generator Agent SHALL return the list of generated queries to the workflow state

### Requirement 5

**User Story:** As a competitive intelligence analyst, I want queries tested across multiple AI models, so that I can compare visibility across different platforms

#### Acceptance Criteria

1. THE AI Model Tester Agent SHALL execute each generated query against a minimum of 2 AI models
2. THE AI Model Tester Agent SHALL support ChatGPT and Claude as AI model providers
3. THE AI Model Tester Agent SHALL collect and store the response from each AI model for each query
4. THE AI Model Tester Agent SHALL handle API failures gracefully and log errors without stopping the workflow
5. THE AI Model Tester Agent SHALL return all collected responses to the workflow state

### Requirement 6

**User Story:** As a business owner, I want to receive a visibility score, so that I can quantify my company's presence in AI model responses

#### Acceptance Criteria

1. THE Scorer Analyzer Agent SHALL calculate a visibility score based on the frequency of company mentions in AI model responses
2. THE Scorer Analyzer Agent SHALL analyze responses to determine if the company was mentioned, recommended, or ignored
3. THE Scorer Analyzer Agent SHALL generate a final report containing the visibility score and supporting metrics
4. THE Scorer Analyzer Agent SHALL return the final analysis results to the workflow state

### Requirement 7

**User Story:** As a system operator, I want company and competitor data stored in a RAG system, so that historical context can inform future analyses

#### Acceptance Criteria

1. THE RAG Store SHALL persist company profiles including URL, name, description, and industry classification
2. THE RAG Store SHALL persist competitor information discovered during analysis
3. THE RAG Store SHALL store industry-specific query templates for reuse
4. THE RAG Store SHALL provide query methods to retrieve stored data by company name or industry
5. WHERE the system is in initial development phase, THE RAG Store SHALL support in-memory storage using Python dictionaries

### Requirement 8

**User Story:** As a developer, I want clear type definitions for all data structures, so that the codebase is maintainable and type-safe

#### Acceptance Criteria

1. THE Visibility Score System SHALL define Pydantic models for all API request payloads
2. THE Visibility Score System SHALL define Pydantic models for all API response payloads
3. THE Visibility Score System SHALL define typed state models for the LangGraph workflow
4. THE Visibility Score System SHALL use type hints throughout the codebase

### Requirement 9

**User Story:** As a system integrator, I want environment-based configuration, so that API keys and settings can be managed securely

#### Acceptance Criteria

1. THE Visibility Score System SHALL load API keys from environment variables
2. THE Visibility Score System SHALL load configuration settings from a centralized settings module
3. THE Visibility Score System SHALL not hardcode sensitive credentials in source code
4. THE Visibility Score System SHALL provide default configuration values for development environments
