#!/usr/bin/env python3
"""
Development server runner for Strategic Build Planner API

Usage:
    python run_server.py
    
Or with custom port:
    python run_server.py --port 8080
"""

import sys
import argparse
import uvicorn

def main():
    parser = argparse.ArgumentParser(description="Run Strategic Build Planner API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8001, help="Port to bind to (default: 8001)")
    parser.add_argument("--reload", action="store_true", default=True, help="Enable auto-reload (default: True)")
    parser.add_argument("--no-reload", dest="reload", action="store_false", help="Disable auto-reload")
    args = parser.parse_args()
    
    print(f"""
╔════════════════════════════════════════════════════════════════╗
║      Strategic Build Planner API Server                       ║
╚════════════════════════════════════════════════════════════════╝

Starting server at http://{args.host}:{args.port}

Available endpoints:
  - GET  /                   - API information
  - GET  /health             - Health check
  - GET  /docs               - Interactive API documentation
  - POST /ingest             - Upload files for plan generation
  - POST /draft              - Generate Strategic Build Plan
  - POST /agents/run         - Run specialist agents (QMA, PMA, SCA, EMA, SBP-QA)
  - POST /publish            - Publish plan to Confluence
  - POST /meeting/apply      - Apply meeting notes to plan
  - POST /qa/grade           - Grade plan quality

Press CTRL+C to stop the server.
    """)
    
    uvicorn.run(
        "server.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )

if __name__ == "__main__":
    main()
