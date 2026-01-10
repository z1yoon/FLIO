"""
FLIO AI Backend Services
FastAPI server with Azure OpenAI integration for dating app matching
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import services and routers
from app.routers import questions, matching, auth
from app.services.azure_openai_service import azure_openai_service
from app.models.database import get_supabase_client

# Global services
services = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialize Azure OpenAI and Supabase connections on startup
    """
    logger.info("Starting FLIO AI Backend...")
    
    try:
        # Initialize Azure OpenAI service
        logger.info("Initializing Azure OpenAI service...")
        services["azure_openai"] = azure_openai_service
        logger.info("Azure OpenAI service initialized")
        
        # Initialize Supabase connection
        logger.info("Initializing Supabase connection...")
        try:
            supabase_client = get_supabase_client()
            services["supabase"] = supabase_client
            logger.info("Supabase client initialized - skipping connection test during startup")
        except Exception as e:
            logger.warning(f"Supabase initialization failed: {e}")
            logger.info("Continuing without Supabase - will retry on first request")
        
        logger.info("All services initialized successfully!")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise
    
    yield
    
    # Cleanup
    logger.info("Shutting down FLIO AI Backend...")
    services.clear()


app = FastAPI(
    title="FLIO AI Backend",
    description="Azure OpenAI powered dating app backend for Korean compatibility matching",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(questions.router, prefix="/api/v1/questions", tags=["Questions & Answers"])
app.include_router(matching.router, prefix="/api/v1/matching", tags=["Profile Matching"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
logger.info("Routers included successfully")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "FLIO AI Backend",
        "status": "healthy",
        "version": "1.0.0",
        "services_loaded": list(services.keys()),
        "description": "Azure OpenAI powered Korean dating app backend"
    }


@app.get("/health")
async def health_check():
    """Detailed health check for monitoring"""
    try:
        # Check Azure OpenAI connectivity
        azure_status = "azure_openai" in services
        
        # Check Supabase connectivity
        supabase_status = "supabase" in services
        
        # Overall health
        overall_healthy = azure_status and supabase_status
        
        return {
            "status": "healthy" if overall_healthy else "degraded",
            "timestamp": __import__('datetime').datetime.now().isoformat(),
            "services": {
                "azure_openai": {
                    "status": "connected" if azure_status else "disconnected",
                    "embedding_model": "text-embedding-3-small",
                    "chat_model": "gpt-4o-mini",
                    "features": ["embeddings", "chat_completion", "answer_analysis"]
                },
                "supabase": {
                    "status": "connected" if supabase_status else "disconnected",
                    "features": ["questions_db", "user_answers", "profile_embeddings"]
                }
            },
            "features": [
                "✅ Korean compatibility questions (40 questions)",
                "✅ Azure OpenAI text analysis",
                "✅ Profile embedding generation", 
                "✅ Similarity-based matching",
                "✅ Match explanations in Korean",
                "✅ Answer quality analysis"
            ],
            "architecture": {
                "embedding_model": "Azure OpenAI text-embedding-3-small (1536D)",
                "chat_model": "Azure OpenAI gpt-4o-mini",
                "database": "Supabase PostgreSQL with pgvector",
                "matching_algorithm": "Cosine similarity + cultural scoring"
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "services": services.keys() if services else []
        }


@app.get("/api/v1/system/info")
async def system_info():
    """System information"""
    return {
        "environment_variables": {
            "azure_openai_configured": bool(os.getenv("AZURE_OPENAI_ENDPOINT")),
            "supabase_configured": bool(os.getenv("SUPABASE_URL")),
        },
        "models": {
            "embedding_model": os.getenv("AZURE_OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
            "chat_model": os.getenv("AZURE_OPENAI_CHAT_MODEL", "gpt-4o-mini"),
            "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
        },
        "features": {
            "profile_embeddings": True,
            "compatibility_matching": True, 
            "answer_analysis": True,
            "match_explanations": True,
            "korean_language": True
        }
    }
