#!/bin/bash

# Start the API server
echo "Starting AI Visibility Scoring System API..."
echo "Server will be available at: http://localhost:8000"
echo ""
echo "Test clients:"
echo "  - Industry Detector: tests/clients/test_api_browser.html"
echo "  - Query Generator: tests/clients/test_query_generator.html"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python -m uvicorn src.app:app --reload --host 0.0.0.0 --port 8000
