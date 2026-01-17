"""
FastAPI Application Entry Point
Strategic Build Planner MVP
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Import routers
from app.routers import ingest, draft, publish, meeting, qa, checklist, confluence, quote, lessons

app = FastAPI(
    title="Strategic Build Planner API",
    description="AI-powered APQP Strategic Build Plan generator for Northern Manufacturing",
    version="0.1.0",
)

# Configure CORS - allow common dev ports
default_origins = "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://localhost:3000"
origins = os.getenv("CORS_ORIGINS", default_origins).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Strategic Build Planner API",
        "version": "0.1.0",
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Strategic Build Planner API",
        "version": "0.1.0",
        "docs": "/docs",
        "endpoints": {
            "ingest": "/api/ingest",
            "checklist": "/api/checklist",
            "confluence": "/api/confluence",
            "quote": "/api/quote",
            "lessons": "/api/lessons",
            "draft": "/api/draft",
            "publish": "/api/publish",
            "meeting": "/api/meeting/apply",
            "qa": "/api/qa/grade",
        },
    }


# Include routers
app.include_router(ingest.router, prefix="/api", tags=["ingest"])
app.include_router(draft.router, prefix="/api", tags=["draft"])
app.include_router(publish.router, prefix="/api", tags=["publish"])
app.include_router(meeting.router, prefix="/api/meeting", tags=["meeting"])
app.include_router(qa.router, prefix="/api/qa", tags=["qa"])
app.include_router(checklist.router, tags=["checklist"])
app.include_router(confluence.router, tags=["confluence"])
app.include_router(quote.router, tags=["quote"])
app.include_router(lessons.router, tags=["lessons"])

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
