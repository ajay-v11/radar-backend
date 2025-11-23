"""
Pydantic models for structured LLM output.
"""

from typing import Dict, List, TypedDict
from pydantic import BaseModel, Field


class BrandPositioning(BaseModel):
    value_proposition: str = Field(description="Main value proposition")
    differentiators: List[str] = Field(description="Unique features")
    price_positioning: str = Field(description="premium, mid, or budget")


class BuyerIntentSignals(BaseModel):
    common_questions: List[str] = Field(description="Common customer questions")
    decision_factors: List[str] = Field(description="Purchase decision factors")
    pain_points: List[str] = Field(description="Customer pain points")


class CompetitorInfo(BaseModel):
    name: str = Field(description="Competitor name")
    description: str = Field(description="Brief description")
    products: str = Field(description="Main products/services")
    positioning: str = Field(description="Market positioning")
    price_tier: str = Field(description="premium, mid, or budget")


class CompanyAnalysis(BaseModel):
    company_name: str = Field(description="Official company name")
    company_description: str = Field(description="Brief 1-2 sentence description")
    company_summary: str = Field(description="Comprehensive 3-4 sentence summary")
    industry: str = Field(description="Industry category")
    product_category: str = Field(description="Specific product/service category")
    market_keywords: List[str] = Field(description="5-8 search keywords")
    target_audience: str = Field(description="Primary target customers")
    brand_positioning: BrandPositioning
    buyer_intent_signals: BuyerIntentSignals
    industry_specific: Dict[str, str] = Field(description="Industry-specific fields")
    competitors: List[CompetitorInfo] = Field(description="3-5 main competitors")


class IndustryDetectorState(TypedDict):
    """State for the industry detector graph."""
    # Input
    company_url: str
    company_name: str
    company_description: str
    competitor_urls: Dict[str, str]
    llm_provider: str
    
    # Scraped content
    company_pages: Dict[str, str]
    competitor_pages: Dict[str, str]
    combined_content: str
    
    # Analysis results
    industry: str
    product_category: str
    market_keywords: List[str]
    target_audience: str
    brand_positioning: Dict
    buyer_intent_signals: Dict
    industry_specific: Dict
    competitors: List[str]
    competitors_data: List[Dict]
    
    # Metadata
    errors: List[str]
    completed: bool
