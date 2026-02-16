"""
Main FastAPI Application

Unified API server with all routes organized cleanly.
"""

import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.config.settings import settings


from app.api.routes import analysis_routes
from app.api.routes import health_routes
from app.api.routes import job_routes
from app.api import auth

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="API for analyzing company visibility across AI models"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # ============================================================================
    # Global Exception Handlers
    # ============================================================================
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle HTTP exceptions with user-friendly messages."""
        logger.error(f"HTTP error on {request.url.path}: {exc.status_code} - {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "message": exc.detail,
                "status_code": exc.status_code
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle request validation errors with clear messages."""
        logger.error(f"Validation error on {request.url.path}: {exc.errors()}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": True,
                "message": "Invalid request data. Please check your input.",
                "details": exc.errors(),
                "status_code": 422
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """
        Catch-all handler for unhandled exceptions.
        Prevents raw Python tracebacks from reaching users.
        """
        logger.error(
            f"Unhandled exception on {request.url.path}: {type(exc).__name__}: {str(exc)}",
            exc_info=True
        )
        
        # Determine if this is an LLM API error
        error_message = "Analysis failed. Please try again."
        if "API" in str(exc) or "rate limit" in str(exc).lower():
            error_message = "AI service temporarily unavailable. Please try again in a few moments."
        elif "timeout" in str(exc).lower():
            error_message = "Request timed out. Please try again."
        elif "connection" in str(exc).lower():
            error_message = "Connection error. Please check your network and try again."
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": True,
                "message": error_message,
                "status_code": 500
            }
        )
    
    # ============================================================================
    # Include Routers
    # ============================================================================
    
    app.include_router(health_routes.router)
    app.include_router(auth.router)
    app.include_router(job_routes.router)
    app.include_router(analysis_routes.router)
    app.include_router(analysis_routes.report_router)
    
    @app.on_event("startup")
    async def startup_event():
        """Initialize application resources on startup."""
        startup_logger = logging.getLogger(__name__)
        
        
        # Initialize databases
        try:
            from app.core.config.database import initialize_chroma_collections, test_connections
            
            # Test connections
            status = test_connections()
            
            if status["chromadb"]["connected"]:
                startup_logger.info("✅ ChromaDB: Connected")
                # Initialize collections
                companies_col, competitors_col = initialize_chroma_collections()
                startup_logger.info(f"✅ Initialized ChromaDB collections: {companies_col.name}, {competitors_col.name}")
            else:
                startup_logger.warning(f"⚠️  ChromaDB: Not connected - {status['chromadb']['error']}")
            
            if status["redis"]["connected"]:
                startup_logger.info("✅ Redis: Connected")
            else:
                startup_logger.warning(f"⚠️  Redis: Not connected - {status['redis']['error']}")

            if status["postgres"]["connected"]:
                startup_logger.info("✅ Postgres: Connected")
            else:
                startup_logger.warning(f"⚠️  Postgres: Not connected - {status['postgres']['error']}")
                
        except Exception as e:
            startup_logger.error(f"❌ Database initialization error: {e}")
            startup_logger.warning("Application will continue but some features may not work")
    
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
