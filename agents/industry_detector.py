"""
Industry Detector Agent (Enhanced)

This agent scrapes company websites using Firecrawl, analyzes the content with OpenAI,
and classifies the company into an industry category. It also extracts company information
and identifies competitors.
"""

from typing import Dict, List, Optional
from openai import OpenAI
from models.schemas import WorkflowState
from config.settings import settings
import json


def detect_industry(state: WorkflowState) -> WorkflowState:
    """
    Enhanced industry detection using Firecrawl and OpenAI.
    
    This function:
    1. Scrapes the company website using Firecrawl
    2. Uses OpenAI to analyze the content and extract:
       - Company name (if not provided)
       - Company description/summary
       - Industry classification
       - List of competitors
    
    Args:
        state: WorkflowState containing company_url and optionally company_name
        
    Returns:
        Updated WorkflowState with industry, company_name, company_description,
        company_summary, competitors, and scraped_content populated
        
    Requirements:
        - 3.1: Scrape company website and analyze content
        - 3.2: Use AI to classify industry and extract information
        - 3.3: Identify competitors in the same industry
        - 3.4: Return comprehensive company profile to workflow state
    """
    company_url = state.get("company_url", "")
    company_name = state.get("company_name", "")
    company_description = state.get("company_description", "")
    errors = state.get("errors", [])
    
    if not company_url:
        errors.append("No company URL provided")
        state["errors"] = errors
        state["industry"] = "other"
        return state
    
    # Step 1: Scrape website content using Firecrawl
    scraped_content = _scrape_website(company_url, errors)
    state["scraped_content"] = scraped_content
    
    # Step 2: Analyze content with OpenAI
    if scraped_content:
        analysis = _analyze_with_openai(
            scraped_content=scraped_content,
            company_url=company_url,
            provided_name=company_name,
            provided_description=company_description,
            errors=errors
        )
        
        # Update state with analysis results
        if analysis:
            state["company_name"] = analysis.get("company_name", company_name)
            state["company_description"] = analysis.get("company_description", company_description)
            state["company_summary"] = analysis.get("company_summary", "")
            state["industry"] = analysis.get("industry", "other")
            state["competitors"] = analysis.get("competitors", [])
        else:
            # Fallback to basic keyword detection if AI analysis fails
            state["industry"] = _fallback_keyword_detection(
                company_name or "",
                company_description or scraped_content[:1000]
            )
            state["competitors"] = []
    else:
        # No scraped content - use fallback method
        state["industry"] = _fallback_keyword_detection(
            company_name or "",
            company_description or ""
        )
        state["competitors"] = []
    
    state["errors"] = errors
    return state


def _scrape_website(url: str, errors: List[str]) -> str:
    """
    Scrape website content using Firecrawl.
    
    Args:
        url: Website URL to scrape
        errors: List to append error messages to
        
    Returns:
        Scraped content in markdown format, or empty string on failure
    """
    if not settings.FIRECRAWL_API_KEY:
        errors.append("Firecrawl API key not configured")
        return ""
    
    try:
        from firecrawl import Firecrawl
        
        firecrawl = Firecrawl(api_key=settings.FIRECRAWL_API_KEY)
        
        # Scrape the website with markdown format
        result = firecrawl.scrape(
            url=url,
            formats=["markdown"],
            only_main_content=True,  # Focus on main content, skip navigation/footer
            timeout=30000  # 30 second timeout
        )
        
        if result and "markdown" in result:
            markdown_content = result["markdown"]
            # Limit content to first 10000 characters to avoid token limits
            return markdown_content[:10000] if markdown_content else ""
        else:
            errors.append(f"Firecrawl returned no content for {url}")
            return ""
            
    except ImportError:
        errors.append("Firecrawl package not installed. Install with: pip install firecrawl-py")
        return ""
    except Exception as e:
        errors.append(f"Firecrawl scraping error for {url}: {str(e)}")
        return ""


def _analyze_with_openai(
    scraped_content: str,
    company_url: str,
    provided_name: str,
    provided_description: str,
    errors: List[str]
) -> Optional[Dict]:
    """
    Analyze scraped content using OpenAI to extract company information.
    
    Args:
        scraped_content: Markdown content from Firecrawl
        company_url: Company website URL
        provided_name: User-provided company name (if any)
        provided_description: User-provided description (if any)
        errors: List to append error messages to
        
    Returns:
        Dictionary with company_name, company_description, company_summary,
        industry, and competitors, or None on failure
    """
    if not settings.OPENAI_API_KEY:
        errors.append("OpenAI API key not configured for industry analysis")
        return None
    
    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Create analysis prompt
        prompt = f"""Analyze the following website content and extract key information about the company.

Website URL: {company_url}
{f"Provided Company Name: {provided_name}" if provided_name else ""}
{f"Provided Description: {provided_description}" if provided_description else ""}

Website Content:
{scraped_content}

Please analyze this content and provide a JSON response with the following structure:
{{
    "company_name": "The official company name",
    "company_description": "A brief 1-2 sentence description of what the company does",
    "company_summary": "A comprehensive 3-4 sentence summary of the company's business, products/services, and value proposition",
    "industry": "One of: technology, retail, healthcare, finance, food_services, or other",
    "competitors": ["List of 3-5 main competitor names in the same industry"]
}}

Industry Classification Guidelines:
- technology: Software, SaaS, AI, cloud, apps, IT services, hardware, semiconductors, automation
- retail: E-commerce, stores, fashion, consumer goods, marketplace platforms
- healthcare: Medical services, pharmaceuticals, biotech, telemedicine, health tech
- finance: Banking, fintech, payments, insurance, investment, cryptocurrency
- food_services: Restaurants, meal delivery, catering, food tech, meal kits
- other: Anything that doesn't clearly fit the above categories

Be accurate and specific. If the company name is already provided and correct, use it. For competitors, list actual company names that compete in the same space."""

        response = client.chat.completions.create(
            model=settings.INDUSTRY_ANALYSIS_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert business analyst specializing in company classification and competitive analysis. Always respond with valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,  # Lower temperature for more consistent results
            max_tokens=1000,
            response_format={"type": "json_object"}  # Ensure JSON response
        )
        
        result_text = response.choices[0].message.content
        if not result_text:
            errors.append("OpenAI returned empty response for industry analysis")
            return None
        
        # Parse JSON response
        analysis = json.loads(result_text)
        
        # Validate and normalize industry
        valid_industries = ["technology", "retail", "healthcare", "finance", "food_services", "other"]
        if analysis.get("industry") not in valid_industries:
            analysis["industry"] = "other"
        
        # Ensure all required fields exist
        analysis.setdefault("company_name", provided_name or "Unknown")
        analysis.setdefault("company_description", provided_description or "")
        analysis.setdefault("company_summary", "")
        analysis.setdefault("competitors", [])
        
        return analysis
        
    except json.JSONDecodeError as e:
        errors.append(f"Failed to parse OpenAI response as JSON: {str(e)}")
        return None
    except Exception as e:
        errors.append(f"OpenAI analysis error: {str(e)}")
        return None


def _fallback_keyword_detection(company_name: str, text_content: str) -> str:
    """
    Fallback keyword-based industry detection when AI analysis fails.
    
    This is the original simple keyword matching approach, used as a backup.
    
    Args:
        company_name: Company name
        text_content: Text to analyze (description or scraped content)
        
    Returns:
        Detected industry category
    """
    # Industry keyword patterns for classification
    INDUSTRY_KEYWORDS: Dict[str, List[str]] = {
        "technology": [
            "software", "tech", "technology", "saas", "cloud", "ai", "artificial intelligence",
            "machine learning", "data", "analytics", "platform", "app", "application",
            "digital", "cyber", "security", "it", "information technology", "computing",
            "developer", "programming", "code", "api", "web", "mobile", "hardware",
            "semiconductor", "chip", "electronics", "automation", "robotics", "iot"
        ],
        "retail": [
            "retail", "store", "shop", "shopping", "ecommerce", "e-commerce", "marketplace",
            "fashion", "clothing", "apparel", "accessories", "consumer", "goods",
            "merchandise", "boutique", "outlet", "department store", "supermarket",
            "grocery", "convenience", "wholesale", "distribution", "supply chain"
        ],
        "healthcare": [
            "health", "healthcare", "medical", "medicine", "hospital", "clinic",
            "pharmaceutical", "pharma", "biotech", "biotechnology", "drug", "therapy",
            "treatment", "patient", "doctor", "physician", "nurse", "care", "wellness",
            "fitness", "telemedicine", "telehealth", "diagnostic", "laboratory", "lab"
        ],
        "finance": [
            "finance", "financial", "bank", "banking", "investment", "insurance",
            "fintech", "payment", "credit", "loan", "mortgage", "wealth", "asset",
            "trading", "stock", "securities", "fund", "capital", "accounting",
            "tax", "audit", "cryptocurrency", "crypto", "blockchain", "wallet"
        ],
        "food_services": [
            "food", "restaurant", "dining", "meal", "kitchen", "catering", "delivery",
            "takeout", "fast food", "cafe", "coffee", "bakery", "bar", "pub",
            "hospitality", "culinary", "chef", "recipe", "cooking", "grocery delivery",
            "meal kit", "subscription box", "prepared meals", "food service"
        ]
    }
    
    # Combine text for analysis (lowercase for case-insensitive matching)
    combined_text = f"{company_name} {text_content}".lower()
    
    # Extract keywords from the combined text
    text_words = set(combined_text.split())
    
    # Score each industry based on keyword matches
    industry_scores: Dict[str, int] = {}
    
    for industry, keywords in INDUSTRY_KEYWORDS.items():
        score = 0
        
        for keyword in keywords:
            if " " in keyword:
                # Multi-word phrase - check in full text
                if keyword in combined_text:
                    score += 2  # Multi-word matches get higher weight
            else:
                # Single word - check in word set
                if keyword in text_words:
                    score += 1
        
        industry_scores[industry] = score
    
    # Determine the best matching industry
    if not industry_scores or max(industry_scores.values()) == 0:
        return "other"
    else:
        # Get industry with highest score
        return max(industry_scores, key=industry_scores.get)
