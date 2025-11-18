"""
Industry Detection Controller

Handles business logic for company analysis and industry detection.
"""

from typing import Optional, Dict, AsyncGenerator
import asyncio
import json
from openai import OpenAI
from config.settings import settings


async def analyze_company_stream(
    company_url: str,
    company_name: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """
    Stream company analysis with step-by-step updates.
    
    Args:
        company_url: Company website URL
        company_name: Optional company name
        
    Yields:
        JSON string events with step, status, message, and optional data
    """
    try:
        # Step 1: Initialize
        yield json.dumps({
            "step": "initialize",
            "status": "started",
            "message": f"Starting analysis for {company_url}",
            "data": None
        })
        await asyncio.sleep(0.1)
        
        # Step 2: Scrape website
        yield json.dumps({
            "step": "scraping",
            "status": "in_progress",
            "message": f"Crawling website: {company_url}",
            "data": None
        })
        
        scraped_content = await asyncio.to_thread(
            _scrape_website,
            company_url
        )
        
        if not scraped_content:
            yield json.dumps({
                "step": "scraping",
                "status": "failed",
                "message": "Failed to scrape website content",
                "data": None
            })
            yield json.dumps({
                "step": "complete",
                "status": "error",
                "message": "Analysis failed: Could not retrieve website content",
                "data": None
            })
            return
        
        yield json.dumps({
            "step": "scraping",
            "status": "completed",
            "message": f"Successfully scraped {len(scraped_content)} characters",
            "data": {"content_length": len(scraped_content)}
        })
        await asyncio.sleep(0.1)
        
        # Step 3: Analyze with AI
        yield json.dumps({
            "step": "analyzing",
            "status": "in_progress",
            "message": "Analyzing content with AI to extract company information",
            "data": None
        })
        
        analysis = await asyncio.to_thread(
            _analyze_with_ai,
            scraped_content,
            company_url,
            company_name or ""
        )
        
        if not analysis:
            # Fallback to keyword detection
            yield json.dumps({
                "step": "analyzing",
                "status": "warning",
                "message": "AI analysis unavailable, using fallback keyword detection",
                "data": None
            })
            
            industry = await asyncio.to_thread(
                _fallback_keyword_detection,
                company_name or "",
                scraped_content[:1000]
            )
            
            analysis = {
                "company_name": company_name or "Unknown",
                "company_description": "",
                "company_summary": "",
                "industry": industry,
                "competitors": []
            }
        
        yield json.dumps({
            "step": "analyzing",
            "status": "completed",
            "message": "Analysis complete",
            "data": None
        })
        await asyncio.sleep(0.1)
        
        # Step 4: Extract competitors
        yield json.dumps({
            "step": "competitors",
            "status": "completed",
            "message": f"Identified {len(analysis.get('competitors', []))} competitors",
            "data": {"competitor_count": len(analysis.get('competitors', []))}
        })
        await asyncio.sleep(0.1)
        
        # Step 5: Final results
        yield json.dumps({
            "step": "complete",
            "status": "success",
            "message": "Company analysis completed successfully",
            "data": {
                "company_name": analysis.get("company_name"),
                "company_description": analysis.get("company_description"),
                "company_summary": analysis.get("company_summary"),
                "industry": analysis.get("industry"),
                "competitors": analysis.get("competitors", [])
            }
        })
        
    except Exception as e:
        yield json.dumps({
            "step": "error",
            "status": "failed",
            "message": f"Unexpected error: {str(e)}",
            "data": None
        })


def _scrape_website(url: str) -> str:
    """Scrape website content using Firecrawl."""
    if not settings.FIRECRAWL_API_KEY:
        print("ERROR: Firecrawl API key not configured")
        return ""
    
    try:
        from firecrawl import Firecrawl
        
        firecrawl = Firecrawl(api_key=settings.FIRECRAWL_API_KEY)
        result = firecrawl.scrape(
            url=url,
            formats=["markdown"],
            only_main_content=True,
            timeout=30000
        )
        
        # Handle both dict and object responses
        if hasattr(result, 'markdown') and result.markdown:
            return result.markdown[:10000]
        elif isinstance(result, dict) and "markdown" in result:
            return result["markdown"][:10000]
        
        print(f"ERROR: Firecrawl returned no markdown content")
        return ""
    except Exception as e:
        print(f"ERROR: Firecrawl scraping failed: {str(e)}")
        return ""


def _analyze_with_ai(
    scraped_content: str,
    company_url: str,
    provided_name: str
) -> Optional[Dict]:
    """Analyze scraped content using OpenAI."""
    if not settings.OPENAI_API_KEY:
        return None
    
    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        prompt = f"""Analyze the following website content and extract key information about the company.

Website URL: {company_url}
{f"Provided Company Name: {provided_name}" if provided_name else ""}

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

Be accurate and specific. For competitors, list actual company names that compete in the same space."""

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
            temperature=0.3,
            max_tokens=1000,
            response_format={"type": "json_object"}
        )
        
        result_text = response.choices[0].message.content
        if not result_text:
            return None
        
        analysis = json.loads(result_text)
        
        # Validate industry
        valid_industries = ["technology", "retail", "healthcare", "finance", "food_services", "other"]
        if analysis.get("industry") not in valid_industries:
            analysis["industry"] = "other"
        
        return analysis
        
    except Exception:
        return None


def _fallback_keyword_detection(company_name: str, text_content: str) -> str:
    """Fallback keyword-based industry detection."""
    INDUSTRY_KEYWORDS = {
        "technology": [
            "software", "tech", "saas", "cloud", "ai", "machine learning",
            "data", "analytics", "platform", "app", "digital", "cybersecurity"
        ],
        "retail": [
            "retail", "store", "shop", "ecommerce", "marketplace", "fashion",
            "clothing", "consumer goods"
        ],
        "healthcare": [
            "health", "medical", "hospital", "pharmaceutical", "biotech",
            "telemedicine", "wellness"
        ],
        "finance": [
            "finance", "bank", "investment", "insurance", "fintech",
            "payment", "cryptocurrency"
        ],
        "food_services": [
            "food", "restaurant", "meal", "catering", "delivery", "cafe"
        ]
    }
    
    combined_text = f"{company_name} {text_content}".lower()
    text_words = set(combined_text.split())
    
    industry_scores = {}
    for industry, keywords in INDUSTRY_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in text_words or keyword in combined_text)
        industry_scores[industry] = score
    
    if not industry_scores or max(industry_scores.values()) == 0:
        return "other"
    
    return max(industry_scores, key=industry_scores.get)
