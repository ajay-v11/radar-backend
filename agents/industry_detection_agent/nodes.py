"""
Node functions for the industry detection LangGraph workflow.
"""

import logging
import json
from urllib.parse import urlparse
from langchain_core.messages import SystemMessage, HumanMessage

from agents.industry_detection_agent.models import IndustryDetectorState
from agents.industry_detection_agent.utils import (
    scrape_website,
    get_analysis_llm,
    quick_industry_detection,
    fallback_keyword_detection,
    INDUSTRY_EXTRACTION_TEMPLATES,
    VALID_INDUSTRIES,
    MAX_FALLBACK_CONTENT_LENGTH
)

logger = logging.getLogger(__name__)


def scrape_company_pages(state: IndustryDetectorState) -> IndustryDetectorState:
    """Node: Scrape multiple pages from company website."""
    logger.info("🌐 Scraping company pages...")
    
    company_url = state["company_url"]
    errors = state.get("errors", [])
    
    parsed = urlparse(company_url)
    base_path = f"{parsed.scheme}://{parsed.netloc}"
    
    pages_to_scrape = {
        "homepage": company_url,
        "about": f"{base_path}/about",
        "pricing": f"{base_path}/pricing",
        "products": f"{base_path}/products"
    }
    
    scraped_pages = {}
    
    # Scrape pages sequentially to properly track errors
    for page_type, url in pages_to_scrape.items():
        try:
            logger.info(f"Scraping {page_type}: {url}")
            content = scrape_website(url, errors)
            if content:
                scraped_pages[page_type] = content[:1000]
                logger.info(f"✓ Scraped {page_type} ({len(content)} chars)")
            else:
                logger.warning(f"✗ No content from {page_type}")
        except Exception as e:
            error_msg = f"Failed to scrape {page_type}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
    
    # Fallback to single page if multi-page fails
    if not scraped_pages:
        logger.info("Multi-page scraping failed, falling back to homepage only")
        content = scrape_website(company_url, errors)
        if content:
            scraped_pages["homepage"] = content
    
    state["company_pages"] = scraped_pages
    state["errors"] = errors
    
    return state


def scrape_competitor_pages(state: IndustryDetectorState) -> IndustryDetectorState:
    """Node: Scrape competitor websites (if URLs provided)."""
    competitor_urls = state.get("competitor_urls", {})
    
    if not competitor_urls:
        logger.info("⏭️  No competitor URLs provided, skipping")
        state["competitor_pages"] = {}
        return state
    
    logger.info(f"🏢 Scraping {len(competitor_urls)} competitor websites...")
    
    errors = state.get("errors", [])
    competitor_pages = {}
    limited_competitors = dict(list(competitor_urls.items())[:4])
    
    # Scrape competitors sequentially to properly track errors
    for name, url in limited_competitors.items():
        try:
            logger.info(f"Scraping competitor {name}: {url}")
            content = scrape_website(url, errors)
            if content:
                competitor_pages[name] = content[:1500]
                logger.info(f"✓ Scraped competitor: {name} ({len(content)} chars)")
            else:
                logger.warning(f"✗ No content from competitor: {name}")
        except Exception as e:
            error_msg = f"Failed to scrape competitor {name}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
    
    state["competitor_pages"] = competitor_pages
    state["errors"] = errors
    return state


def combine_scraped_content(state: IndustryDetectorState) -> IndustryDetectorState:
    """Node: Combine all scraped content for analysis."""
    logger.info("📝 Combining scraped content...")
    
    company_pages = state.get("company_pages", {})
    
    if not company_pages:
        logger.error("❌ No company pages scraped!")
        errors = state.get("errors", [])
        errors.append("No content was scraped from company website")
        state["errors"] = errors
        state["combined_content"] = ""
        return state
    
    combined = "\n\n".join([
        f"=== {page_type.upper()} ===\n{content}" 
        for page_type, content in company_pages.items()
    ])
    
    logger.info(f"✓ Combined {len(company_pages)} pages, total {len(combined)} chars")
    state["combined_content"] = combined
    return state


def analyze_with_llm(state: IndustryDetectorState) -> IndustryDetectorState:
    """Node: Analyze content with LLM to extract all information."""
    logger.info("🤖 Analyzing with LLM...")
    
    combined_content = state.get("combined_content", "")
    company_url = state["company_url"]
    provided_name = state.get("company_name", "")
    provided_description = state.get("company_description", "")
    llm_provider = state.get("llm_provider", "openai")
    errors = state.get("errors", [])
    
    if not combined_content or combined_content.strip() == "":
        logger.error("❌ No content to analyze - scraping likely failed")
        logger.error(f"Errors so far: {errors}")
        state["industry"] = fallback_keyword_detection(provided_name, provided_description or "")
        state["company_name"] = provided_name or "Unknown"
        state["company_description"] = provided_description or ""
        state["competitors"] = []
        state["competitors_data"] = []
        state["errors"] = errors + ["No scraped content available for analysis"]
        return state
    
    llm = get_analysis_llm(llm_provider)
    if not llm:
        logger.error(f"Could not initialize {llm_provider} LLM")
        state["industry"] = fallback_keyword_detection(provided_name, combined_content[:MAX_FALLBACK_CONTENT_LENGTH])
        state["errors"] = errors + [f"LLM initialization failed for {llm_provider}"]
        return state
    
    logger.info(f"LLM initialized: {type(llm).__name__}")
    
    try:
        # Quick industry detection for template
        preliminary_industry = quick_industry_detection(combined_content)
        industry_template = INDUSTRY_EXTRACTION_TEMPLATES.get(preliminary_industry, INDUSTRY_EXTRACTION_TEMPLATES["other"])
        
        prompt = f"""Analyze the following website content and extract comprehensive business intelligence.

Website URL: {company_url}
{f"Provided Company Name: {provided_name}" if provided_name else ""}
{f"Provided Description: {provided_description}" if provided_description else ""}

Website Content:
{combined_content}

Please analyze this content and provide a JSON response with the following structure:
{{
    "company_name": "The official company name",
    "company_description": "A brief 1-2 sentence description of what the company does",
    "company_summary": "A comprehensive 3-4 sentence summary of the company's business, products/services, and value proposition",
    "industry": "One of: technology, retail, healthcare, finance, food_services, or other",
    "product_category": "Specific product/service category",
    "market_keywords": ["keyword1", "keyword2", "keyword3"],
    "target_audience": "Description of primary target customers",
    
    "brand_positioning": {{
        "value_proposition": "Main value proposition in one sentence",
        "differentiators": ["unique feature 1", "unique feature 2"],
        "price_positioning": "One of: premium, mid, budget"
    }},
    
    "buyer_intent_signals": {{
        "common_questions": ["question 1", "question 2"],
        "decision_factors": ["factor 1", "factor 2"],
        "pain_points": ["pain point 1", "pain point 2"]
    }},
    
    "industry_specific": {{
        {', '.join([f'"{field}": "value"' for field in industry_template["extract_fields"]])}
    }},
    
    "competitors": [
        {{
            "name": "Competitor name",
            "description": "Brief 1-sentence description",
            "products": "Main products/services",
            "positioning": "Key differentiator",
            "price_tier": "One of: premium, mid, budget"
        }}
    ]
}}

For competitors, provide 3-5 main {industry_template["competitor_focus"]}.
Be specific and accurate. RESPOND ONLY WITH VALID JSON, NO MARKDOWN."""

        # Try structured output first (works with OpenAI, Gemini)
        from agents.industry_detection_agent.models import CompanyAnalysis
        
        try:
            logger.info(f"Attempting structured output with {type(llm).__name__}")
            structured_llm = llm.with_structured_output(CompanyAnalysis)
            logger.info("Structured output wrapper created")
            
            messages = [
                SystemMessage(content="You are an expert business analyst. Analyze the company and provide structured output."),
                HumanMessage(content=prompt)
            ]
            
            logger.info("Invoking structured LLM...")
            analysis_obj = structured_llm.invoke(messages)
            logger.info(f"Structured LLM returned: {type(analysis_obj)}")
            
            # Convert Pydantic model to dict
            analysis = {
                "company_name": analysis_obj.company_name,
                "company_description": analysis_obj.company_description,
                "company_summary": analysis_obj.company_summary,
                "industry": analysis_obj.industry,
                "product_category": analysis_obj.product_category,
                "market_keywords": analysis_obj.market_keywords,
                "target_audience": analysis_obj.target_audience,
                "brand_positioning": analysis_obj.brand_positioning.dict(),
                "buyer_intent_signals": analysis_obj.buyer_intent_signals.dict(),
                "industry_specific": analysis_obj.industry_specific,
                "competitors": [comp.dict() for comp in analysis_obj.competitors]
            }
            
            logger.info(f"✓ Structured output parsed successfully")
            
        except Exception as e:
            # Fallback to JSON parsing if structured output fails
            logger.warning(f"Structured output failed ({type(e).__name__}: {e}), falling back to JSON parsing")
            
            messages = [
                SystemMessage(content="You are an expert business analyst. Always respond with valid JSON only, no markdown formatting."),
                HumanMessage(content=prompt)
            ]
            
            response = llm.invoke(messages)
            
            logger.info(f"Response type: {type(response)}")
            
            # Extract content safely
            result_text = ""
            if hasattr(response, 'content'):
                result_text = response.content if response.content else ""
            else:
                result_text = str(response) if response else ""
            
            logger.info(f"Result text type: {type(result_text)}, length: {len(result_text)}")
            
            # Check for empty response BEFORE attempting JSON parse
            if not result_text or result_text.strip() == "":
                error_msg = f"LLM returned empty response. Response object: {type(response)}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            logger.info(f"Raw LLM response (first 200 chars): {result_text[:200]}")
            
            # Clean markdown if present
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            # Final check after cleaning
            if not result_text or result_text.strip() == "":
                error_msg = "LLM response was empty after markdown cleaning"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Parse JSON with error handling
            try:
                analysis = json.loads(result_text)
                logger.info("✓ JSON parsed successfully")
            except json.JSONDecodeError as e:
                logger.error(f"JSON parse error: {e}")
                logger.error(f"Response (first 500 chars): {result_text[:500]}")
                
                # Try to fix common issues
                import re
                fixed_text = re.sub(r',(\s*[}\]])', r'\1', result_text)
                try:
                    analysis = json.loads(fixed_text)
                    logger.info("✓ JSON parsed after fixing trailing commas")
                except json.JSONDecodeError as e2:
                    logger.error(f"JSON parse still failed after fixing: {e2}")
                    raise ValueError(f"Failed to parse LLM response as JSON: {e}")
        
        # Validate and set defaults
        if analysis.get("industry") not in VALID_INDUSTRIES:
            analysis["industry"] = "other"
        
        state["company_name"] = analysis.get("company_name", provided_name or "Unknown")
        state["company_description"] = analysis.get("company_description", provided_description or "")
        state["industry"] = analysis.get("industry", "other")
        state["product_category"] = analysis.get("product_category", "")
        state["market_keywords"] = analysis.get("market_keywords", [])
        state["target_audience"] = analysis.get("target_audience", "")
        state["brand_positioning"] = analysis.get("brand_positioning", {})
        state["buyer_intent_signals"] = analysis.get("buyer_intent_signals", {})
        state["industry_specific"] = analysis.get("industry_specific", {})
        
        # Process competitors
        competitors = analysis.get("competitors", [])
        if competitors and isinstance(competitors[0], dict):
            validated = []
            for comp in competitors:
                if comp.get("name"):
                    validated.append({
                        "name": comp.get("name", ""),
                        "description": comp.get("description", ""),
                        "products": comp.get("products", ""),
                        "positioning": comp.get("positioning", ""),
                        "price_tier": comp.get("price_tier", "mid")
                    })
            state["competitors"] = [c["name"] for c in validated]
            state["competitors_data"] = validated
        else:
            state["competitors"] = []
            state["competitors_data"] = []
        
        logger.info(f"✓ Analysis complete: {state['industry']}")
        
    except Exception as e:
        import traceback
        logger.error(f"LLM analysis failed: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        state["industry"] = fallback_keyword_detection(provided_name, combined_content[:MAX_FALLBACK_CONTENT_LENGTH])
        state["errors"] = errors + [f"LLM analysis error: {str(e)}"]
    
    return state


def enrich_competitors(state: IndustryDetectorState) -> IndustryDetectorState:
    """Node: Enrich competitor data with scraped content."""
    competitor_pages = state.get("competitor_pages", {})
    competitors_data = state.get("competitors_data", [])
    
    if not competitor_pages or not competitors_data:
        logger.info("⏭️  No competitor data to enrich")
        return state
    
    logger.info(f"💎 Enriching {len(competitor_pages)} competitors...")
    
    llm_provider = state.get("llm_provider", "openai")
    llm = get_analysis_llm(llm_provider)
    
    if not llm:
        logger.warning("Cannot enrich competitors without LLM")
        return state
    
    enriched = []
    for comp in competitors_data:
        comp_name = comp["name"]
        enriched_comp = comp.copy()
        
        if comp_name in competitor_pages:
            try:
                prompt = f"""Analyze this competitor's website and extract key positioning information.

Competitor: {comp_name}
Content: {competitor_pages[comp_name][:1000]}

Provide a JSON response:
{{
    "value_proposition": "Their main value prop",
    "unique_features": ["feature1", "feature2"],
    "price_tier": "premium|mid|budget"
}}"""
                
                messages = [
                    SystemMessage(content="You are a competitive intelligence analyst. Respond with valid JSON only, no markdown."),
                    HumanMessage(content=prompt)
                ]
                
                response = llm.invoke(messages)
                result_text = response.content
                
                # Clean markdown if present
                if "```json" in result_text:
                    result_text = result_text.split("```json")[1].split("```")[0].strip()
                elif "```" in result_text:
                    result_text = result_text.split("```")[1].split("```")[0].strip()
                
                comp_analysis = json.loads(result_text)
                
                enriched_comp["value_proposition"] = comp_analysis.get("value_proposition", "")
                enriched_comp["unique_features"] = comp_analysis.get("unique_features", [])
                enriched_comp["price_tier"] = comp_analysis.get("price_tier", comp["price_tier"])
                
                logger.info(f"✓ Enriched: {comp_name}")
            except Exception as e:
                logger.warning(f"✗ Failed to enrich {comp_name}: {e}")
        
        enriched.append(enriched_comp)
    
    state["competitors_data"] = enriched
    return state


def finalize(state: IndustryDetectorState) -> IndustryDetectorState:
    """Node: Finalize and mark as completed."""
    logger.info("✅ Industry detection workflow complete")
    state["completed"] = True
    return state
