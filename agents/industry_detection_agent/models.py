"""
Pydantic models for structured LLM output.
"""

from typing import Dict, List, TypedDict, Optional, Annotated
from typing_extensions import TypedDict
import operator
from pydantic import BaseModel, Field


class IndustryClassification(BaseModel):
    """Dynamic industry classification without constraints."""
    industry: str = Field(description="Specific industry name (e.g., 'AI-Powered Meal Delivery', 'B2B SaaS Marketing Tools')")
    broad_category: str = Field(description="Broad category (e.g., 'Technology', 'Food Services', 'Healthcare')")
    industry_description: str = Field(description="2-3 sentence description of this industry")


class ExtractionTemplate(BaseModel):
    """Dynamic extraction template for the detected industry."""
    extract_fields: List[str] = Field(description="5-8 industry-specific fields to extract (e.g., 'menu_types', 'tech_stack')")
    competitor_focus: str = Field(description="Description of what types of competitors to look for")


class QueryCategory(BaseModel):
    """Dynamic query category for search intent."""
    category_key: str = Field(description="Unique key (e.g., 'comparison', 'pricing')")
    category_name: str = Field(description="Human-readable name")
    weight: float = Field(description="Weight between 0 and 1 (must sum to 1.0 across all categories)")
    description: str = Field(description="What this category represents")
    examples: List[str] = Field(description="2-3 example queries")


class QueryCategoriesTemplate(BaseModel):
    """Collection of query categories for this specific company."""
    categories: List[QueryCategory] = Field(description="5-7 query categories with weights summing to 1.0")


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
    """Complete company analysis with dynamic fields."""
    company_name: str = Field(description="Official company name")
    company_description: str = Field(description="Brief 1-2 sentence description")
    company_summary: str = Field(description="Comprehensive 3-4 sentence summary")
    product_category: str = Field(description="Specific product/service category")
    market_keywords: List[str] = Field(description="5-8 search keywords")
    target_audience: str = Field(description="Primary target customers")
    brand_positioning: BrandPositioning
    buyer_intent_signals: BuyerIntentSignals
    industry_specific: Optional[Dict[str, str]] = Field(default={}, description="Industry-specific fields based on template")
    competitors: List[CompetitorInfo] = Field(description="3-5 main competitors")


class IndustryDetectorState(TypedDict):
    """State for the industry detector graph."""
    # Input
    company_url: str
    target_region: str
    company_name: str
    company_description: str
    competitor_urls: Dict[str, str]
    llm_provider: str
    
    # Scraped content
    company_pages: Dict[str, str]
    competitor_pages: Dict[str, str]
    combined_content: str
    
    # Dynamic industry classification
    industry: str
    broad_category: str
    industry_description: str
    extraction_template: Optional[Dict]
    query_categories_template: Optional[Dict]
    
    # Analysis results
    product_category: str
    market_keywords: List[str]
    target_audience: str
    brand_positioning: Dict
    buyer_intent_signals: Dict
    industry_specific: Dict
    competitors: List[str]
    competitors_data: List[Dict]
    
    # Metadata - use Annotated with operator.add for parallel node updates
    errors: Annotated[List[str], operator.add]
    completed: bool
