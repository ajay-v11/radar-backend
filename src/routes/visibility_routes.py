"""
Visibility Analysis Routes

Endpoints for full visibility scoring workflow.
"""

from fastapi import APIRouter, HTTPException, status
from models.schemas import AnalyzeRequest, AnalyzeResponse

from src.controllers.visibility_controller import analyze_visibility


router = APIRouter(prefix="/visibility", tags=["Visibility Analysis"])


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_company_visibility(request: AnalyzeRequest) -> AnalyzeResponse:
    """
    Analyze a company's visibility across AI models.
    
    Accepts company information and triggers the complete analysis workflow:
    1. Detect industry category
    2. Generate industry-specific queries
    3. Test queries across multiple AI models
    4. Calculate visibility score
    
    Args:
        request: AnalyzeRequest containing company_url and optional company details
        
    Returns:
        AnalyzeResponse with visibility score and detailed analysis results
        
    Raises:
        HTTPException 400: If company_url is invalid
        HTTPException 500: If internal processing error occurs
    """
    try:
        company_url_str = str(request.company_url)
        
        result = analyze_visibility(
            company_url=company_url_str,
            company_name=request.company_name or "",
            company_description=request.company_description or "",
            models=request.models
        )
        
        return AnalyzeResponse(**result)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )
