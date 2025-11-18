#!/usr/bin/env python3
"""
Server startup script for AI Visibility Scoring System
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "src.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
