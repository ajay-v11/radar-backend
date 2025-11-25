"""
Main FastAPI Application

Unified API server with all routes organized cleanly.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.settings import settings
from storage.rag_store import get_rag_store

from src.routes import health_routes, analysis_routes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)


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
    app.include_router(analysis_routes.router)
    app.include_router(analysis_routes.report_router)
    
    @app.on_event("startup")
    async def startup_event():
        """Initialize application resources on startup."""
        import logging
        logger = logging.getLogger(__name__)
        
        # Initialize RAG Store
        rag_store = get_rag_store()
        logger.info(f"RAGStore initialized with {len(rag_store.query_templates)} industry templates")
        logger.info(f"Supported industries: {', '.join(rag_store.query_templates.keys())}")
        
        # Initialize databases
        try:
            from config.database import initialize_chroma_collections, test_connections
            
            # Test connections
            status = test_connections()
            
            if status["chromadb"]["connected"]:
                logger.info("✅ ChromaDB: Connected")
                # Initialize collections
                companies_col, competitors_col = initialize_chroma_collections()
                logger.info(f"✅ Initialized ChromaDB collections: {companies_col.name}, {competitors_col.name}")
            else:
                logger.warning(f"⚠️  ChromaDB: Not connected - {status['chromadb']['error']}")
            
            if status["redis"]["connected"]:
                logger.info("✅ Redis: Connected")
            else:
                logger.warning(f"⚠️  Redis: Not connected - {status['redis']['error']}")
                
        except Exception as e:
            logger.error(f"❌ Database initialization error: {e}")
            logger.warning("Application will continue but some features may not work")
    
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
