"""
Industry Detection Controller

Handles business logic for company analysis and industry detection.
"""
from typing import Optional, AsyncGenerator
import asyncio
import json
from queue import Queue
from app.core.config.settings import settings
import logging
from app.services.agents.industry_detection_agent import run_industry_detection_workflow


async def analyze_company_stream(
    company_url: str,
    company_name: Optional[str] = None,
    target_region: str = "India"
) -> AsyncGenerator[str, None]:
    """
    Stream company analysis with step-by-step updates using the new modular agent.
    
    Args:
        company_url: Company website URL
        company_name: Optional company name
        target_region: Target region for AI model context (default: "United States")
        
    Yields:
        JSON string events with step, status, message, and optional data
    """
   
    logger = logging.getLogger(__name__)
    
    try:
        # Step 1: Initialize
        yield json.dumps({
            "step": "initialize",
            "status": "started",
            "message": f"Starting analysis for {company_url}",
            "data": None
        })
        await asyncio.sleep(0.1)
        
        # Step 2: Scraping
        yield json.dumps({
            "step": "scraping",
            "status": "in_progress",
            "message": "Scraping website...",
            "data": None
        })
        
        # Step 3: Analyzing
        yield json.dumps({
            "step": "analyzing",
            "status": "in_progress",
            "message": "Analyzing company with AI...",
            "data": None
        })
        
        # Create thread-safe queue for real-time streaming
        event_queue = Queue()
        result_container = {}
        error_container = {}
        
        def progress_callback(step, status, message, data):
            """Callback to capture progress events and put them in queue (thread-safe)."""
            event = {
                "step": step,
                "status": status,
                "message": message,
                "data": data
            }
            event_queue.put(event)  # Thread-safe put
        
        # Run workflow in background thread
        async def run_workflow():
            try:
                result = await asyncio.to_thread(
                    run_industry_detection_workflow,
                    company_url=company_url,
                    company_name=company_name or "",
                    company_description="",
                    competitor_urls={},
                    llm_provider=settings.INDUSTRY_ANALYSIS_PROVIDER,
                    target_region=target_region,
                    progress_callback=progress_callback
                )
                result_container['result'] = result
            except Exception as e:
                logger.error(f"Error in industry detection workflow: {str(e)}", exc_info=True)
                error_container['error'] = e
            finally:
                # Signal completion
                event_queue.put(None)
        
        # Start workflow task
        workflow_task = asyncio.create_task(run_workflow())
        
        # Stream events as they arrive
        while True:
            # Check queue in non-blocking way
            try:
                event = event_queue.get_nowait()
                if event is None:  # Workflow completed
                    break
                yield json.dumps(event)
            except:
                # Queue empty, wait a bit and check again
                await asyncio.sleep(0.05)
                # Check if workflow is done
                if workflow_task.done():
                    # Drain any remaining events
                    while not event_queue.empty():
                        event = event_queue.get_nowait()
                        if event is not None:
                            yield json.dumps(event)
                    break
        
        # Wait for workflow to complete
        await workflow_task
        
        # Check if there was an error
        if 'error' in error_container:
            error = error_container['error']
            error_message = "Analysis failed. Please try again."
            
            # Provide more specific error messages
            error_str = str(error).lower()
            if "api" in error_str or "rate limit" in error_str:
                error_message = "AI service temporarily unavailable. Please try again in a few moments."
            elif "timeout" in error_str:
                error_message = "Request timed out. Please try again with a different URL."
            elif "scraping" in error_str or "firecrawl" in error_str:
                error_message = "Unable to access website. Please check the URL and try again."
            elif "connection" in error_str:
                error_message = "Connection error. Please check your network and try again."
            
            logger.error(f"Company analysis failed for {company_url}: {error_message}")
            
            yield json.dumps({
                "step": "error",
                "status": "failed",
                "message": error_message,
                "data": None
            })
            return
        
        result = result_container.get('result')
        
        if not result:
            logger.error(f"No result returned from workflow for {company_url}")
            yield json.dumps({
                "step": "error",
                "status": "failed",
                "message": "Analysis failed. No data returned. Please try again.",
                "data": None
            })
            return
        
        logger.info(f"✅ Analysis complete for {company_url}")
        
        # Format response with all fields in data object (consistent with cache)
        data = {
            "industry": result.get("industry"),
            "broad_category": result.get("broad_category"),
            "industry_description": result.get("industry_description"),
            "company_name": result.get("company_name"),
            "company_description": result.get("company_description"),
            "competitors": result.get("competitors", []),
            "target_region": result.get("target_region", "United States"),
            "extraction_template": result.get("extraction_template", {}),
            "query_categories_template": result.get("query_categories_template", {}),
            "product_category": result.get("product_category"),
            "market_keywords": result.get("market_keywords", []),
            "target_audience": result.get("target_audience"),
            "brand_positioning": result.get("brand_positioning", {}),
            "buyer_intent_signals": result.get("buyer_intent_signals", {}),
            "industry_specific": result.get("industry_specific", {}),
            "competitors_data": result.get("competitors_data", [])
        }
        
        yield json.dumps({
            "step": "complete",
            "status": "success",
            "message": "Company analysis completed successfully",
            "data": data,
            "cached": False
        })
        
    except Exception as e:
        logger.error(f"Unexpected error in analyze_company_stream: {str(e)}", exc_info=True)
        yield json.dumps({
            "step": "error",
            "status": "failed",
            "message": "Analysis failed. Please try again.",
            "data": None
        })


# No legacy cache functions - using route-level slug-based caching only
