"""
FLIO AI Backend Services
FastAPI server for face verification, matching, speech, and AI features
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.routers import face, matching, questions, speech
from app.models.face_recognition import FaceRecognitionModel
from app.models.profile_matching_v2 import ProfileMatchingModelV2
from app.models.question_generator import AdaptiveQuestionGenerator
from app.models.speech import SpeechProcessor
from app.models.rag_questions import RAGQuestionRetriever
from app.models.question_rl import QuestionSelector, QuestionOrchestrator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global model instances
models = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Load ML models on startup, cleanup on shutdown
    """
    logger.info("Loading AI models...")
    
    # Load face recognition model (InsightFace/ArcFace)
    logger.info("Loading InsightFace model...")
    models["face"] = FaceRecognitionModel()
    
    # Load profile embedding model (BGE-M3 Korean)
    logger.info("Loading BGE-M3 Korean model...")
    models["profile"] = ProfileMatchingModelV2(model_name="upskyy/bge-m3-korean")
    
    # Load question generator (Qwen2.5-7B)
    logger.info("Loading Qwen2.5-7B model...")
    models["questions"] = AdaptiveQuestionGenerator()
    
    # Load speech processor (Whisper + MeloTTS)
    logger.info("Loading Speech models (Whisper + MeloTTS)...")
    models["speech"] = SpeechProcessor(whisper_size="large-v3")
    
    # Load RAG retriever
    logger.info("Loading RAG Question Retriever...")
    models["rag"] = RAGQuestionRetriever(embedding_model=models["profile"].model)
    
    # Load RL selector
    logger.info("Loading RL Question Selector...")
    models["rl"] = QuestionSelector()
    
    # Setup orchestrator
    models["orchestrator"] = QuestionOrchestrator(
        rag_retriever=models["rag"],
        rl_selector=models["rl"],
        question_generator=models["questions"]
    )
    
    # Inject speech processor into router
    speech.set_speech_processor(models["speech"])
    
    logger.info("All models loaded successfully!")
    
    yield
    
    # Cleanup
    logger.info("Shutting down, cleaning up models...")
    models.clear()


app = FastAPI(
    title="FLIO AI Backend",
    description="AI services for FLIO dating app - Face verification, matching, speech, and more",
    version="2.0.0",
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
app.include_router(face.router, prefix="/api/face", tags=["Face Verification"])
app.include_router(matching.router, prefix="/api/match", tags=["Matching"])
app.include_router(questions.router, prefix="/api/questions", tags=["Adaptive Questions"])
app.include_router(speech.router, prefix="/api/speech", tags=["Speech (STT/TTS)"])


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "FLIO AI Backend",
        "status": "healthy",
        "models_loaded": list(models.keys()),
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "models": {
            "face_recognition": "face" in models,
            "profile_embedding": "profile" in models,
            "question_generator": "questions" in models,
            "speech": "speech" in models,
            "rag": "rag" in models,
            "rl": "rl" in models,
        },
        "features": [
            "Face Verification (85%)",
            "Profile Matching (BGE-M3)",
            "Adaptive Questions (Qwen2.5)",
            "STT (Whisper)",
            "TTS (MeloTTS)",
            "RAG (Question Database)",
            "RL (Thompson Sampling)"
        ]
    }


def get_face_model() -> FaceRecognitionModel:
    """Dependency to get face recognition model"""
    if "face" not in models:
        raise HTTPException(status_code=503, detail="Face model not loaded")
    return models["face"]


def get_profile_model() -> ProfileMatchingModelV2:
    """Dependency to get profile embedding model"""
    if "profile" not in models:
        raise HTTPException(status_code=503, detail="Profile model not loaded")
    return models["profile"]


def get_speech_processor() -> SpeechProcessor:
    """Dependency to get speech processor"""
    if "speech" not in models:
        raise HTTPException(status_code=503, detail="Speech model not loaded")
    return models["speech"]


def get_orchestrator() -> QuestionOrchestrator:
    """Dependency to get question orchestrator (RAG + RL + Qwen2.5)"""
    if "orchestrator" not in models:
        raise HTTPException(status_code=503, detail="Orchestrator not loaded")
    return models["orchestrator"]
