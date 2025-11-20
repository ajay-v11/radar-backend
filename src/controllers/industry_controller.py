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
        
        # Step 1.5: Check for FULL analysis cache first (instant return)
        import logging
        import hashlib
        logger = logging.getLogger(__name__)
        
        cached_analysis = await asyncio.to_thread(_get_cached_analysis, company_url)
        
        if cached_analysis:
            print(f"\n{'='*60}")
            print(f"[FULL CACHE HIT] ⚡⚡⚡ Returning complete analysis instantly!")
            print(f"[FULL CACHE HIT] Company: {cached_analysis.get('company_name')}")
            print(f"[FULL CACHE HIT] Industry: {cached_analysis.get('industry')}")
            print(f"{'='*60}\n")
            
            # Return all steps instantly with cached data
            yield json.dumps({
                "step": "scraping",
                "status": "cached",
                "message": "⚡ Using cached analysis (instant)",
                "data": {"cached": True}
            })
            
            yield json.dumps({
                "step": "analyzing",
                "status": "cached",
                "message": "⚡ Using cached analysis (instant)",
                "data": None
            })
            
            yield json.dumps({
                "step": "competitors",
                "status": "cached",
                "message": f"⚡ Cached: {len(cached_analysis.get('competitors', []))} competitors",
                "data": {"competitor_count": len(cached_analysis.get('competitors', []))}
            })
            
            yield json.dumps({
                "step": "complete",
                "status": "success",
                "message": "Company analysis completed (from cache)",
                "data": cached_analysis
            })
            return
        
        # Step 2: Scrape website (with cache check)
        from agents.industry_detector import _get_cached_scrape
        
        # Check scrape cache
        cached_content = await asyncio.to_thread(_get_cached_scrape, company_url)
        
        if cached_content:
            print(f"\n{'='*60}")
            print(f"[CACHE HIT] ⚡ Scrape cache hit for {company_url}")
            print(f"{'='*60}\n")
            logger.info(f"[CACHE HIT] Scrape cache hit for {company_url}")
            yield json.dumps({
                "step": "scraping",
                "status": "cached",
                "message": f"⚡ Using cached website content (instant retrieval)",
                "data": {"content_length": len(cached_content), "cached": True}
            })
            scraped_content = cached_content
            # Skip delay on cache hit
            await asyncio.sleep(0)
        else:
            print(f"\n{'='*60}")
            print(f"[CACHE MISS] 🔄 Scraping {company_url}")
            print(f"{'='*60}\n")
            logger.info(f"[CACHE MISS] Scraping {company_url}")
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
            logger.error(f"[SCRAPE FAILED] No content retrieved for {company_url}")
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
        
        if not cached_content:
            # Only send completion message if we actually scraped (not cached)
            print(f"[SCRAPE SUCCESS] ✅ Retrieved {len(scraped_content)} characters\n")
            logger.info(f"[SCRAPE SUCCESS] Retrieved {len(scraped_content)} characters")
            yield json.dumps({
                "step": "scraping",
                "status": "completed",
                "message": f"Successfully scraped {len(scraped_content)} characters",
                "data": {"content_length": len(scraped_content), "cached": False}
            })
            await asyncio.sleep(0.1)
        else:
            # No delay on cache hit
            await asyncio.sleep(0)
        
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
        
        # Step 5: Cache the complete analysis and return results
        final_data = {
            "company_name": analysis.get("company_name"),
            "company_description": analysis.get("company_description"),
            "company_summary": analysis.get("company_summary"),
            "industry": analysis.get("industry"),
            "competitors": analysis.get("competitors", [])
        }
        
        # Cache the complete analysis for instant future retrieval
        await asyncio.to_thread(_cache_analysis, company_url, final_data)
        print(f"[ANALYSIS CACHED] 💾 Stored complete analysis for {company_url}\n")
        
        yield json.dumps({
            "step": "complete",
            "status": "success",
            "message": "Company analysis completed successfully",
            "data": final_data
        })
        
    except Exception as e:
        yield json.dumps({
            "step": "error",
            "status": "failed",
            "message": f"Unexpected error: {str(e)}",
            "data": None
        })


def _scrape_website(url: str) -> str:
    """Scrape website content using Firecrawl with retry strategies."""
    if not settings.FIRECRAWL_API_KEY:
        print("ERROR: Firecrawl API key not configured")
        return ""
    
    try:
        from firecrawl import Firecrawl
        import time
        
        firecrawl = Firecrawl(api_key=settings.FIRECRAWL_API_KEY)
        
        # Try multiple strategies for scraping
        strategies = [
            # Strategy 1: Standard scrape with main content only
            {
                "formats": ["markdown"],
                "only_main_content": True,
                "timeout": 30000
            },
            # Strategy 2: Try without only_main_content (gets more content)
            {
                "formats": ["markdown"],
                "only_main_content": False,
                "timeout": 30000
            },
            # Strategy 3: Try with longer timeout
            {
                "formats": ["markdown"],
                "only_main_content": True,
                "timeout": 60000
            }
        ]
        
        last_error = None
        for i, strategy in enumerate(strategies, 1):
            try:
                print(f"Attempting scrape strategy {i}/{len(strategies)} for {url}")
                result = firecrawl.scrape(url=url, **strategy)
                
                # Handle both dict and object responses
                if hasattr(result, 'markdown') and result.markdown:
                    content = result.markdown[:10000]
                    print(f"✅ Strategy {i} succeeded: {len(content)} characters")
                    return content
                elif isinstance(result, dict) and "markdown" in result:
                    content = result["markdown"][:10000]
                    print(f"✅ Strategy {i} succeeded: {len(content)} characters")
                    return content
                else:
                    print(f"⚠️ Strategy {i} returned no markdown content")
                    
            except Exception as e:
                last_error = str(e)
                print(f"❌ Strategy {i} failed: {last_error}")
                if i < len(strategies):
                    time.sleep(2)  # Wait before trying next strategy
                continue
        
        # All strategies failed - try fallback to main domain if this is a regional domain
        if any(tld in url for tld in ['.co.in', '.co.uk', '.com.au', '.de', '.fr', '.jp']):
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain_parts = parsed.netloc.split('.')
            if len(domain_parts) >= 2:
                base_domain = domain_parts[0] if domain_parts[0] != 'www' else domain_parts[1]
                fallback_url = f"{parsed.scheme}://{base_domain}.com{parsed.path}"
                
                print(f"🔄 Trying fallback domain: {fallback_url}")
                try:
                    result = firecrawl.scrape(
                        url=fallback_url,
                        formats=["markdown"],
                        only_main_content=True,
                        timeout=30000
                    )
                    
                    if hasattr(result, 'markdown') and result.markdown:
                        content = result.markdown[:10000]
                        print(f"✅ Fallback succeeded: {len(content)} characters")
                        return content
                    elif isinstance(result, dict) and "markdown" in result:
                        content = result["markdown"][:10000]
                        print(f"✅ Fallback succeeded: {len(content)} characters")
                        return content
                except Exception as fallback_error:
                    print(f"❌ Fallback domain also failed: {fallback_error}")
        
        print(f"ERROR: All scraping strategies failed. Last error: {last_error}")
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


def _get_analysis_cache_key(url: str) -> str:
    """Generate cache key for complete analysis."""
    import hashlib
    normalized_url = url.rstrip('/').lower()
    return f"analysis:{hashlib.md5(normalized_url.encode()).hexdigest()}"


def _get_cached_analysis(url: str) -> Optional[Dict]:
    """Get cached complete analysis."""
    try:
        from config.database import get_redis_client
        redis_client = get_redis_client()
        cache_key = _get_analysis_cache_key(url)
        cached = redis_client.get(cache_key)
        if cached:
            if isinstance(cached, bytes):
                cached = cached.decode('utf-8')
            return json.loads(cached)
        return None
    except Exception as e:
        print(f"Cache retrieval failed: {e}")
        return None


def _cache_analysis(url: str, analysis: Dict, ttl: int = 86400) -> None:
    """Cache complete analysis (24 hour TTL)."""
    try:
        from config.database import get_redis_client
        redis_client = get_redis_client()
        cache_key = _get_analysis_cache_key(url)
        redis_client.setex(cache_key, ttl, json.dumps(analysis))
    except Exception as e:
        print(f"Cache storage failed: {e}")
