"""
Data models and schemas for the AI Visibility Scoring System.

This module defines all Pydantic models used for API requests/responses,
workflow state management, and data storage.
"""

from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List, Dict, Any
from typing_extensions import TypedDict


# API Request/Response Models

class AnalyzeRequest(BaseModel):
    """Request model for the /analyze endpoint."""
    company_url: HttpUrl = Field(
        ...,
        description="The company's website URL",
        examples=["https://hellofresh.com"]
    )
    company_name: Optional[str] = Field(
        None,
        description="The company name (optional, can be extracted from URL)",
        examples=["HelloFresh"]
    )
    company_description: Optional[str] = Field(
        None,
        description="Brief description of the company and its business",
        examples=["Meal kit delivery service"]
    )
    models: Optional[List[str]] = Field(
        None,
        description="List of AI models to test (defaults to chatgpt and gemini)",
        examples=[["chatgpt", "gemini", "llama", "mistral"]]
    )


class AnalyzeResponse(BaseModel):
    """Response model for the /analyze endpoint."""
    job_id: str = Field(
        ...,
        description="Unique identifier for this analysis job"
    )
    status: str = Field(
        ...,
        description="Status of the analysis",
        examples=["completed", "failed"]
    )
    industry: str = Field(
        ...,
        description="Detected industry category",
        examples=["food_services", "technology", "retail"]
    )
    visibility_score: float = Field(
        ...,
        description="Visibility score as a percentage (0-100)",
        ge=0.0,
        le=100.0
    )
    total_queries: int = Field(
        ...,
        description="Total number of queries executed",
        ge=0
    )
    total_mentions: int = Field(
        ...,
        description="Total number of times the company was mentioned",
        ge=0
    )
    model_results: Dict[str, Any] = Field(
        ...,
        description="Detailed results broken down by AI model"
    )


class HealthResponse(BaseModel):
    """Response model for the /health endpoint."""
    status: str = Field(
        ...,
        description="Health status of the system",
        examples=["healthy", "degraded"]
    )
    version: str = Field(
        ...,
        description="Application version",
        examples=["1.0.0"]
    )


# LangGraph Workflow State Model

class WorkflowState(TypedDict, total=False):
    """
    State model for the LangGraph workflow.
    
    This TypedDict defines the structure of data passed between agents
    in the workflow. Fields are marked as total=False to allow partial
    state updates at each step.
    """
    company_url: str
    company_name: str
    company_description: str
    company_summary: str  # AI-generated summary from scraped content
    scraped_content: str  # Raw scraped content from Firecrawl
    industry: str
    competitors: List[str]  # List of competitor names
    queries: List[str]
    models: List[str]  # List of AI models to test
    model_responses: Dict[str, List[str]]  # {model_name: [response1, response2, ...]}
    visibility_score: float
    analysis_report: Dict[str, Any]
    errors: List[str]


# RAG Store Data Models

class CompanyProfile(BaseModel):
    """Model for storing company profile information."""
    name: str = Field(
        ...,
        description="Company name",
        min_length=1
    )
    url: str = Field(
        ...,
        description="Company website URL"
    )
    description: str = Field(
        ...,
        description="Company description and business overview"
    )
    industry: str = Field(
        ...,
        description="Classified industry category",
        examples=["technology", "retail", "healthcare", "finance", "food_services", "other"]
    )


class CompetitorProfile(BaseModel):
    """Model for storing competitor information."""
    name: str = Field(
        ...,
        description="Competitor company name",
        min_length=1
    )
    url: Optional[str] = Field(
        None,
        description="Competitor website URL (if available)"
    )
    description: Optional[str] = Field(
        None,
        description="Brief description of the competitor"
    )
    industry: str = Field(
        ...,
        description="Industry category of the competitor",
        examples=["technology", "retail", "healthcare", "finance", "food_services", "other"]
    )
