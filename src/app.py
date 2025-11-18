"""
Main FastAPI Application

Unified API server with all routes organized cleanly.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.settings import settings
from storage.rag_store import get_rag_store

from src.routes import health_routes, industry_routes, visibility_routes


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
    
    # Include routers
    app.include_router(health_routes.router)
    app.include_router(industry_routes.router)
    app.include_router(visibility_routes.router)
    
    @app.on_event("startup")
    async def startup_event():
        """Initialize application resources on startup."""
        rag_store = get_rag_store()
        print(f"RAGStore initialized with {len(rag_store.query_templates)} industry templates")
        print(f"Supported industries: {', '.join(rag_store.query_templates.keys())}")
    
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
