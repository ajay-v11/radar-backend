"""
Main entry point for the AI Visibility Scoring System API.
"""

import uvicorn
from app.app import app

__all__ = ["app"]

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
