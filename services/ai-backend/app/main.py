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
from app.routers import questions, matching, auth, voice, trust, verification, profiles
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
        
        # Test Azure OpenAI connection
        test_response = await azure_openai_service.generate_profile_embedding("Test connection")
        logger.info(f"Azure OpenAI connected - embedding dimension: {len(test_response.embedding)}")
        
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
app.include_router(profiles.router, prefix="/api/v1/profiles", tags=["Profile Management"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(voice.router, prefix="/api/v1/voice", tags=["Voice Processing"])
app.include_router(trust.router, prefix="/api/v1/trust", tags=["Trust Score System"])
app.include_router(verification.router, prefix="/api/v1/verification", tags=["Document Verification"])
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
    """Detailed health check for monitoring all Azure services"""
    try:
        from datetime import datetime

        # 1. Check Azure OpenAI connectivity with actual connection test
        azure_openai_health = {"status": "disconnected", "error": None}
        if "azure_openai" in services:
            try:
                connection_test = await azure_openai_service.test_connection()
                azure_openai_health = {
                    "status": connection_test.get("status", "disconnected"),
                    "embedding_model": os.getenv("AZURE_OPENAI_EMBEDDING_MODEL", "text-embedding-3-large"),
                    "chat_model": os.getenv("AZURE_OPENAI_CHAT_MODEL", "gpt-4o-mini"),
                    "whisper_model": os.getenv("AZURE_OPENAI_WHISPER_MODEL", "whisper-1"),
                    "embedding_available": connection_test.get("embedding_available", False),
                    "chat_available": connection_test.get("chat_available", False),
                    "whisper_available": connection_test.get("whisper_available", False),
                    "features": ["embeddings", "chat_completion", "answer_analysis", "voice_transcription"]
                }
            except Exception as e:
                azure_openai_health = {
                    "status": "error",
                    "error": str(e),
                    "features": []
                }

        # 2. Check Azure AI Vision connectivity
        azure_vision_health = {"status": "not_configured", "error": None}
        vision_endpoint = os.getenv("AZURE_VISION_ENDPOINT")
        vision_key = os.getenv("AZURE_VISION_KEY")

        if vision_endpoint and vision_key:
            try:
                # Simple connectivity check to Azure Vision endpoint
                import httpx
                async with httpx.AsyncClient(timeout=5.0) as client:
                    # Just check if endpoint is reachable
                    response = await client.get(
                        f"{vision_endpoint}/computervision/imageanalysis:analyze",
                        params={"api-version": "2024-02-01"},
                        headers={"Ocp-Apim-Subscription-Key": vision_key}
                    )
                    # Endpoint exists if we get any response (even 400/401 means it's reachable)
                    if response.status_code in [200, 400, 401]:
                        azure_vision_health = {
                            "status": "connected",
                            "endpoint": vision_endpoint,
                            "features": ["ocr", "document_verification", "korean_text_recognition"]
                        }
                    else:
                        azure_vision_health = {
                            "status": "error",
                            "error": f"Unexpected status code: {response.status_code}"
                        }
            except Exception as e:
                azure_vision_health = {
                    "status": "error",
                    "error": str(e)
                }

        # 3. Check Supabase connectivity
        supabase_health = {"status": "disconnected", "error": None}
        if "supabase" in services:
            try:
                # Test actual database connection
                supabase_client = get_supabase_client()
                # Simple query to test connection
                test_result = supabase_client.table('questions').select('id').limit(1).execute()
                supabase_health = {
                    "status": "connected",
                    "database": "PostgreSQL with pgvector",
                    "features": ["questions_db", "user_answers", "profile_embeddings", "user_documents"]
                }
            except Exception as e:
                supabase_health = {
                    "status": "error",
                    "error": str(e)
                }

        # Overall health status
        all_services_healthy = (
            azure_openai_health.get("status") == "connected" and
            azure_vision_health.get("status") in ["connected", "not_configured"] and
            supabase_health.get("status") == "connected"
        )

        overall_status = "healthy" if all_services_healthy else "degraded"

        return {
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "services": {
                "azure_openai": azure_openai_health,
                "azure_vision": azure_vision_health,
                "supabase": supabase_health
            },
            "features": [
                "✅ Korean compatibility questions (40 questions)",
                "✅ Azure OpenAI text analysis",
                "✅ Profile embedding generation",
                "✅ Similarity-based matching",
                "✅ Match explanations in Korean",
                "✅ Answer quality analysis",
                "✅ Voice transcription (Whisper)",
                "✅ Document verification (OCR)"
            ],
            "architecture": {
                "embedding_model": f"Azure OpenAI {os.getenv('AZURE_OPENAI_EMBEDDING_MODEL', 'text-embedding-3-large')}",
                "chat_model": f"Azure OpenAI {os.getenv('AZURE_OPENAI_CHAT_MODEL', 'gpt-4o-mini')}",
                "whisper_model": f"Azure OpenAI {os.getenv('AZURE_OPENAI_WHISPER_MODEL', 'whisper-1')}",
                "vision_ocr": "Azure AI Vision (2024-02-01)",
                "database": "Supabase PostgreSQL with pgvector",
                "matching_algorithm": "Cosine similarity + cultural scoring"
            }
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "services": list(services.keys()) if services else []
        }


@app.get("/api/v1/system/info")
async def system_info():
    """System information for debugging"""
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
