"""
Parallel Analysis Routes

Endpoints for parallel batch testing and analysis workflow with streaming.
"""

import logging
import asyncio
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agents.industry_detector import detect_industry
from agents.query_generator import generate_queries
from agents.ai_model_tester import test_ai_models
from agents.scorer_analyzer import analyze_score

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/parallel", tags=["Parallel Analysis"])


class ParallelAnalysisRequest(BaseModel):
    """Request model for parallel analysis"""
    company_url: str
    company_name: Optional[str] = None
    company_description: Optional[str] = None
    num_queries: int = 20
    models: List[str] = ["llama", "gemini"]  # Models to test: chatgpt, gemini, llama, claude
    llm_provider: str = "gemini"  # For industry detection and query generation
    batch_size: int = 5
    llm_provider: str = "gemini"  # For industry detection and query generation
    batch_size: int = 5


async def parallel_analysis_stream(request: ParallelAnalysisRequest):
    """
    Stream parallel batch testing and analysis.
    
    Yields SSE events for:
    1. Industry detection
    2. Query generation
    3. Batch testing + analysis (parallel)
    4. Final aggregation
    """
    import json
    
    def emit(step: str, status: str, data: dict = None, message: str = ""):
        """Emit SSE event with proper formatting for real-time streaming"""
        event = {
            "step": step,
            "status": status,
            "message": message,
            "data": data or {}
        }
        # Use double newline to ensure browser processes event immediately
        return f"data: {json.dumps(event)}\n\n"
    
    try:
        # ====================================================================
        # STEP 1: Industry Detection
        # ====================================================================
        yield emit("step1", "started", message="Starting industry detection...")
        
        state = {
            "company_url": request.company_url,
            "company_name": request.company_name or "",
            "company_description": request.company_description or "",
            "errors": []
        }
        
        state = detect_industry(state, llm_provider=request.llm_provider)
        
        if state.get("errors"):
            yield emit("step1", "warning", {"errors": state["errors"]})
        
        logger.info(f"Industry detection completed: {state.get('industry')}, Company: {state.get('company_name')}")
        
        yield emit("step1", "completed", {
            "industry": state.get("industry"),
            "company_name": state.get("company_name"),
            "competitors": state.get("competitors", [])
        }, "Industry detection completed")
        
        # ====================================================================
        # STEP 2: Query Generation
        # ====================================================================
        yield emit("step2", "started", message="Starting query generation...")
        
        state["num_queries"] = request.num_queries
        state = generate_queries(state, num_queries=request.num_queries, llm_provider=request.llm_provider)
        
        if state.get("errors"):
            yield emit("step2", "warning", {"errors": state["errors"]})
        
        queries = state.get("queries", [])
        yield emit("step2", "completed", {
            "total_queries": len(queries),
            "categories": len(state.get("query_categories", {}))
        }, f"Generated {len(queries)} queries")
        
        # ====================================================================
        # STEP 3: Parallel Batch Testing + Analysis
        # ====================================================================
        yield emit("step3", "started", message="Starting parallel batch testing and analysis...")
        
        batch_size = request.batch_size
        all_batch_responses = {model: [] for model in request.models}
        all_analysis_results = []
        
        for batch_num, i in enumerate(range(0, len(queries), batch_size), 1):
            batch_queries = queries[i:i+batch_size]
            progress = (i / len(queries)) * 100
            
            yield emit("batch", "testing_started", {
                "batch_num": batch_num,
                "batch_size": len(batch_queries),
                "progress": progress
            }, f"Testing batch {batch_num}...")
            
            # Test batch
            batch_state = {
                "queries": batch_queries,
                "models": request.models,
                "model_responses": {},
                "errors": []
            }
            
            batch_state = test_ai_models(batch_state)
            batch_responses = batch_state.get("model_responses", {})
            
            # Store responses
            for model in request.models:
                if model in batch_responses:
                    all_batch_responses[model].extend(batch_responses[model])
            
            yield emit("batch", "testing_completed", {
                "batch_num": batch_num,
                "responses_count": sum(len(r) for r in batch_responses.values())
            }, f"Batch {batch_num} testing completed")
            
            # Analyze batch
            yield emit("batch", "analysis_started", {
                "batch_num": batch_num
            }, f"Analyzing batch {batch_num}...")
            
            analysis_state = {
                "company_name": state.get("company_name"),
                "queries": batch_queries,
                "model_responses": batch_responses,
                "errors": []
            }
            
            analysis_state = analyze_score(analysis_state)
            
            batch_analysis = {
                "batch_num": batch_num,
                "visibility_score": analysis_state.get("visibility_score", 0),
                "total_mentions": analysis_state.get("analysis_report", {}).get("total_mentions", 0),
                "by_model": analysis_state.get("analysis_report", {}).get("by_model", {}),
            }
            
            all_analysis_results.append(batch_analysis)
            
            logger.info(f"Batch {batch_num} analysis: score={batch_analysis['visibility_score']:.1f}%, mentions={batch_analysis['total_mentions']}")
            
            yield emit("batch", "analysis_completed", batch_analysis, f"Batch {batch_num} analysis completed")
        
        # ====================================================================
        # STEP 4: Aggregation
        # ====================================================================
        yield emit("step4", "started", message="Aggregating results...")
        
        final_state = {
            "company_name": state.get("company_name"),
            "queries": queries,
            "model_responses": all_batch_responses,
            "errors": []
        }
        
        final_state = analyze_score(final_state)
        
        final_report = final_state.get("analysis_report", {})
        
        yield emit("step4", "completed", {
            "visibility_score": final_state.get("visibility_score", 0),
            "total_mentions": final_report.get("total_mentions", 0),
            "by_model": final_report.get("by_model", {}),
            "sample_mentions": final_report.get("sample_mentions", [])
        }, "Aggregation completed")
        
        # ====================================================================
        # FINAL RESULTS
        # ====================================================================
        yield emit("complete", "success", {
            "industry": state.get("industry"),
            "company_name": state.get("company_name"),
            "competitors": state.get("competitors", []),
            "total_queries": len(queries),
            "total_responses": sum(len(r) for r in all_batch_responses.values()),
            "visibility_score": final_state.get("visibility_score", 0),
            "analysis_report": final_report,
            "batch_results": all_analysis_results
        }, "Parallel analysis completed successfully!")
        
    except Exception as e:
        logger.error(f"Error in parallel analysis: {str(e)}", exc_info=True)
        yield emit("error", "failed", {"error": str(e)}, f"Error: {str(e)}")


@router.post("/test-and-analyze")
async def parallel_test_and_analyze(request: ParallelAnalysisRequest):
    """
    Parallel batch testing and analysis with streaming output.
    
    Executes the complete workflow with parallel batch processing:
    1. Industry detection
    2. Query generation
    3. Parallel batch testing + analysis
    4. Final aggregation
    
    Returns Server-Sent Events (SSE) stream with real-time progress.
    
    Args:
        request: ParallelAnalysisRequest with company info and settings
        
    Returns:
        StreamingResponse with SSE events
    """
    try:
        if not request.company_url:
            raise ValueError("company_url is required")
        
        return StreamingResponse(
            parallel_analysis_stream(request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            }
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error creating stream: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )
