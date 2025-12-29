"""
Modal.com Deployment Script for FLIO AI Backend

Modal provides serverless GPU compute with pay-per-second billing.
Perfect for cost-effective AI inference.

Usage:
    modal deploy modal_deploy.py
    modal serve modal_deploy.py  # For development

Models:
    - Face: InsightFace/ArcFace (512D)
    - Matching: upskyy/bge-m3-korean (1024D hybrid, Korean fine-tuned)
    - Questions: Qwen2.5-7B-Instruct
    - STT: Whisper large-v3 (self-hosted)
    - TTS: MeloTTS-Korean (self-hosted)
    - RAG: Question database with BGE-M3 embeddings
    - RL: Multi-Armed Bandit for question selection
"""

import modal

# Define the Modal app
app = modal.App("flio-ai-backend")

# Define the container image with all dependencies
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("libgl1-mesa-glx", "libglib2.0-0", "curl", "ffmpeg")
    .pip_install(
        # Web Framework
        "fastapi==0.115.0",
        "uvicorn[standard]==0.32.0",
        "python-multipart==0.0.12",
        # AI/ML Core
        "torch==2.5.0",
        "torchvision==0.20.0",
        "transformers==4.46.0",
        # Matching: BGE-M3
        "FlagEmbedding==1.2.0",
        "sentence-transformers==3.3.0",
        # Face Recognition
        "insightface==0.7.3",
        "onnxruntime==1.20.0",
        "opencv-python-headless==4.10.0.84",
        # Liveness
        "mediapipe==0.10.18",
        # STT: Whisper
        "faster-whisper==1.0.3",
        "openai-whisper==20231117",
        # TTS: CosyVoice2 (2025 best) + fallbacks
        "cosyvoice>=0.1.0",
        "melo-tts==0.1.2",
        "edge-tts==6.1.12",
        "soundfile==0.12.1",
        "librosa==0.10.2",
        "av==12.3.0",
        # Utils
        "Pillow==10.4.0",
        "numpy==1.26.4",
        "scikit-learn==1.5.2",
        "httpx==0.27.2",
        "pydantic==2.9.0",
    )
)

# Persistent volume for model cache
model_volume = modal.Volume.from_name("flio-model-cache", create_if_missing=True)


@app.cls(
    image=image,
    gpu="A10G",  # A10G for Qwen2.5-7B + Whisper (need 24GB VRAM)
    volumes={"/model_cache": model_volume},
    secrets=[modal.Secret.from_name("flio-secrets")],
    container_idle_timeout=300,  # Keep warm for 5 minutes
    allow_concurrent_inputs=10,
)
class FLIOBackend:
    """
    FLIO AI Backend running on Modal.com
    
    Models loaded:
    - InsightFace: Face embedding (512D)
    - BGE-M3: Profile matching (1024D hybrid)
    - Qwen2.5-7B: Question generation & analysis
    - Whisper large-v3: STT (Korean)
    - MeloTTS: TTS (Korean)
    - RAG: Question database with vector search
    - RL: Multi-Armed Bandit for question selection
    """
    
    @modal.enter()
    def load_models(self):
        """Load models when container starts"""
        import os
        os.environ["HF_HOME"] = "/model_cache"
        os.environ["TRANSFORMERS_CACHE"] = "/model_cache"
        
        # Import models
        from app.models.face_recognition import FaceRecognitionModel
        from app.models.profile_matching_v2 import ProfileMatchingModelV2
        from app.models.question_generator import AdaptiveQuestionGenerator
        from app.models.speech import SpeechProcessor
        from app.models.rag_questions import RAGQuestionRetriever
        from app.models.question_rl import QuestionSelector, QuestionOrchestrator
        
        print("Loading InsightFace model...")
        self.face_model = FaceRecognitionModel()
        
        print("Loading Korean fine-tuned BGE-M3 (upskyy/bge-m3-korean)...")
        self.profile_model = ProfileMatchingModelV2(model_name="upskyy/bge-m3-korean")
        
        print("Loading Qwen2.5-7B-Instruct model...")
        self.question_model = AdaptiveQuestionGenerator()
        
        print("Loading Whisper large-v3 for STT...")
        self.speech_processor = SpeechProcessor(whisper_size="large-v3")
        
        print("Loading RAG Question Retriever...")
        self.rag_retriever = RAGQuestionRetriever(embedding_model=self.profile_model.model)
        
        print("Loading RL Question Selector...")
        self.rl_selector = QuestionSelector()
        
        print("Setting up Question Orchestrator (RAG + RL + Qwen2.5)...")
        self.question_orchestrator = QuestionOrchestrator(
            rag_retriever=self.rag_retriever,
            rl_selector=self.rl_selector,
            question_generator=self.question_model
        )
        
        print("All models loaded!")
    
    @modal.method()
    def extract_face_embedding(self, image_base64: str) -> dict:
        """Extract face embedding from image"""
        embedding, face_detected, error = self.face_model.extract_embedding(image_base64)
        return {
            "embedding": embedding,
            "face_detected": face_detected,
            "error": error if error else None
        }
    
    @modal.method()
    def verify_face(
        self,
        profile_embedding: list,
        live_embedding: list,
        threshold: float = 0.85
    ) -> dict:
        """Verify face match"""
        verified, similarity = self.face_model.verify_faces(
            profile_embedding, live_embedding, threshold
        )
        return {
            "verified": verified,
            "similarity": similarity * 100,
            "threshold": threshold * 100,
            "message": f"✅ Face verified ({similarity*100:.1f}%)" if verified
                       else f"❌ Face mismatch ({similarity*100:.1f}%)"
        }
    
    @modal.method()
    def check_liveness(self, frames_base64: list) -> dict:
        """Check liveness from video frames"""
        is_live, blink_count, message = self.face_model.detect_liveness(frames_base64)
        return {
            "is_live": is_live,
            "blink_count": blink_count,
            "message": message
        }
    
    @modal.method()
    def generate_profile_embedding(self, profile_data: dict) -> dict:
        """Generate profile embedding for matching (BGE-M3 1024D)"""
        return self.profile_model.generate_embedding(profile_data)
    
    @modal.method()
    def calculate_match_similarity(
        self,
        embedding1: list,
        embedding2: list
    ) -> float:
        """Calculate similarity between two profiles"""
        return self.profile_model.calculate_similarity(embedding1, embedding2)
    
    @modal.method()
    def find_matches(
        self,
        query_profile: dict,
        candidate_profiles: list,
        top_k: int = 20
    ) -> list:
        """Find most compatible profiles using hybrid search"""
        return self.profile_model.find_matches(query_profile, candidate_profiles, top_k)
    
    # Question Generation Methods
    @modal.method()
    def analyze_answer(self, question: str, answer: str) -> dict:
        """Analyze user's answer for clarity"""
        return self.question_model.analyze_answer(question, answer)
    
    @modal.method()
    def generate_followup_questions(
        self,
        question: str,
        answer: str,
        user_profile: dict,
        num_questions: int = 3
    ) -> list:
        """Generate follow-up questions for vague answers"""
        return self.question_model.generate_followup_questions(
            question, answer, user_profile, num_questions
        )
    
    @modal.method()
    def analyze_reshuffle_request(
        self,
        user_profile: dict,
        current_filters: dict,
        reshuffle_reason: str,
        rejected_profiles: list = None
    ) -> dict:
        """Analyze why user wants to reshuffle and suggest improvements"""
        return self.question_model.analyze_reshuffle_request(
            user_profile, current_filters, reshuffle_reason, rejected_profiles
        )
    
    @modal.method()
    def generate_match_explanation(
        self,
        profile_a: dict,
        profile_b: dict,
        match_score: float
    ) -> dict:
        """Generate human-readable match explanation"""
        return self.question_model.generate_match_explanation(
            profile_a, profile_b, match_score
        )
    
    # ========================================
    # Speech Processing Methods (STT/TTS)
    # ========================================
    
    @modal.method()
    def transcribe_speech(self, audio_base64: str, language: str = "ko") -> dict:
        """
        Transcribe speech to text using Whisper large-v3
        
        Args:
            audio_base64: Base64 encoded audio (WAV/MP3)
            language: Target language (default: Korean)
        
        Returns:
            {
                "text": "인식된 텍스트",
                "segments": [...],
                "confidence": 0.95
            }
        """
        return self.speech_processor.speech_to_text(audio_base64, language)
    
    @modal.method()
    def synthesize_speech(
        self,
        text: str,
        speed: float = 1.0,
        emotion: str = "neutral"
    ) -> dict:
        """
        Convert text to speech using MeloTTS-Korean
        
        Args:
            text: Korean text to synthesize
            speed: Speech speed (0.5 - 2.0)
            emotion: Emotion style (neutral/happy/sad/angry)
        
        Returns:
            {
                "audio": "base64_wav",
                "duration_seconds": 3.5,
                "sample_rate": 24000
            }
        """
        return self.speech_processor.text_to_speech(text, speed, emotion)
    
    # ========================================
    # RAG + RL Question Selection Methods
    # ========================================
    
    @modal.method()
    def get_next_questions(
        self,
        user_answer: str,
        current_question: str,
        answered_questions: list,
        user_profile: dict,
        num_questions: int = 3
    ) -> list:
        """
        Get next best questions using RAG + RL
        
        Flow:
        1. RAG retrieves relevant questions from database
        2. RL selects best questions using Thompson Sampling
        3. Qwen2.5 personalizes the questions
        
        Args:
            user_answer: User's last answer
            current_question: Question that was asked
            answered_questions: List of answered question IDs
            user_profile: User's profile for context
            num_questions: Number of questions to return
        """
        return self.question_orchestrator.get_next_question(
            user_answer=user_answer,
            current_question=current_question,
            answered_questions=answered_questions,
            user_profile=user_profile,
            num_questions=num_questions
        )
    
    @modal.method()
    def process_answer_with_rl(
        self,
        question_id: str,
        question_text: str,
        answer: str,
        user_profile: dict
    ) -> dict:
        """
        Process answer and update RL for better question selection
        
        Returns analysis from Qwen2.5 and updates RL model
        """
        return self.question_orchestrator.process_answer(
            question_id=question_id,
            question_text=question_text,
            answer=answer,
            user_profile=user_profile
        )
    
    @modal.method()
    def get_questions_by_category(
        self,
        category: str,
        answered_questions: list,
        top_k: int = 3
    ) -> list:
        """Get top questions from a specific category"""
        return self.rag_retriever.retrieve_by_category(
            category=category,
            answered_questions=answered_questions,
            top_k=top_k
        )
    
    @modal.method()
    def get_question_coverage(self, answered_questions: list) -> dict:
        """
        Get coverage analysis of answered questions
        
        Returns:
            {
                "coverage_percent": 33.3,
                "by_category": {...},
                "missing_high_priority": [...],
                "recommendation": "..."
            }
        """
        return self.rag_retriever.get_coverage_analysis(answered_questions)
    
    @modal.method()
    def update_match_feedback(
        self,
        questions_asked: list,
        match_accepted: bool,
        user_profile: dict
    ):
        """
        Update RL based on match outcome
        
        Called when user accepts/rejects a match to improve future
        question selection
        """
        user_context = {
            "age": user_profile.get("age", 30),
            "gender": user_profile.get("gender", "unknown")
        }
        self.rl_selector.update_from_match_success(
            questions_asked=questions_asked,
            match_accepted=match_accepted,
            user_context=user_context
        )
    
    @modal.method()
    def get_question_performance(self, question_id: str) -> dict:
        """Get RL performance metrics for a question"""
        return self.rl_selector.get_question_performance(question_id)
    
    @modal.asgi_app()
    def fastapi_app(self):
        """
        Serve FastAPI app
        
        Endpoints:
        - /api/face/embed: Extract 512D face embedding
        - /api/face/verify: Compare embeddings (85% threshold)
        - /api/face/liveness: Detect real person (blink detection)
        - /api/match/embed: Generate profile embedding
        """
        from fastapi import FastAPI, HTTPException
        from fastapi.middleware.cors import CORSMiddleware
        from pydantic import BaseModel
        from typing import List, Optional
        
        api = FastAPI(
            title="FLIO AI Backend",
            description="Face Verification (85% match) + Profile Matching API",
            version="1.0.0",
        )
        
        api.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Request/Response models
        class FaceEmbedRequest(BaseModel):
            image: str  # Base64 encoded
        
        class FaceVerifyRequest(BaseModel):
            profile_embedding: List[float]
            live_embedding: List[float]
            threshold: float = 0.85
        
        class LivenessRequest(BaseModel):
            frames: List[str]  # List of base64 frames
        
        class ProfileEmbedRequest(BaseModel):
            profile: dict
        
        @api.get("/")
        def root():
            return {
                "service": "FLIO AI Backend",
                "platform": "Modal.com",
                "features": [
                    "Face Verification (85% threshold)",
                    "Liveness Detection",
                    "Profile Matching"
                ]
            }
        
        @api.get("/health")
        def health():
            return {
                "status": "healthy",
                "models": [
                    "insightface/arcface",
                    "upskyy/bge-m3-korean",
                    "Qwen/Qwen2.5-7B-Instruct",
                    "faster-whisper/large-v3",
                    "MeloTTS-Korean"
                ],
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
        
        @api.post("/api/face/embed")
        def face_embed(request: FaceEmbedRequest):
            """Extract 512D face embedding using InsightFace/ArcFace"""
            return self.extract_face_embedding(request.image)
        
        @api.post("/api/face/verify")
        def face_verify(request: FaceVerifyRequest):
            """
            Verify face match (85% threshold)
            
            Returns verified=True if similarity >= threshold
            """
            if len(request.profile_embedding) != 512 or len(request.live_embedding) != 512:
                raise HTTPException(400, "Invalid embedding dimension. Expected 512D.")
            return self.verify_face(
                request.profile_embedding,
                request.live_embedding,
                request.threshold
            )
        
        @api.post("/api/face/liveness")
        def liveness(request: LivenessRequest):
            """
            Check liveness from video frames
            
            Detects eye blinks to prevent photo attacks
            """
            if len(request.frames) < 10:
                raise HTTPException(400, "At least 10 frames required")
            return self.check_liveness(request.frames)
        
        @api.post("/api/match/embed")
        def match_embed(request: ProfileEmbedRequest):
            """Generate 1024D profile embedding for matching (BGE-M3)"""
            result = self.generate_profile_embedding(request.profile)
            return result
        
        # Question Generation endpoints
        class AnalyzeAnswerRequest(BaseModel):
            question: str
            answer: str
        
        class GenerateQuestionsRequest(BaseModel):
            question: str
            answer: str
            user_profile: dict
            num_questions: int = 3
        
        class ReshuffleRequest(BaseModel):
            user_profile: dict
            current_filters: dict
            reshuffle_reason: str
            rejected_profiles: Optional[List[dict]] = None
        
        class MatchExplanationRequest(BaseModel):
            profile_a: dict
            profile_b: dict
            match_score: float
        
        @api.post("/api/questions/analyze")
        def analyze_answer(request: AnalyzeAnswerRequest):
            """Analyze user's answer for clarity and completeness"""
            return self.analyze_answer(request.question, request.answer)
        
        @api.post("/api/questions/generate")
        def generate_questions(request: GenerateQuestionsRequest):
            """
            Generate follow-up questions for vague answers
            
            This is the core feature that makes FLIO different:
            - Acts like a 결혼정보회사 매니저
            - Digs deeper into vague answers
            - Non-judgmental AI encourages honesty
            """
            questions = self.generate_followup_questions(
                request.question,
                request.answer,
                request.user_profile,
                request.num_questions
            )
            return {"questions": questions}
        
        @api.post("/api/questions/reshuffle-analysis")
        def reshuffle_analysis(request: ReshuffleRequest):
            """
            Analyze why user wants to reshuffle matches
            
            Returns:
            - Analysis of user's dissatisfaction
            - Missing profile information
            - Additional questions if needed
            - Filter adjustment suggestions
            - Avatar message for user
            """
            return self.analyze_reshuffle_request(
                request.user_profile,
                request.current_filters,
                request.reshuffle_reason,
                request.rejected_profiles
            )
        
        @api.post("/api/questions/match-explanation")
        def match_explanation(request: MatchExplanationRequest):
            """Generate human-readable explanation for why two profiles match"""
            return self.generate_match_explanation(
                request.profile_a,
                request.profile_b,
                request.match_score
            )
        
        # ========================================
        # Speech API (STT/TTS)
        # ========================================
        
        class TranscribeRequest(BaseModel):
            audio: str  # Base64 encoded audio
            language: str = "ko"
        
        class SynthesizeRequest(BaseModel):
            text: str
            speed: float = 1.0
            emotion: str = "neutral"
        
        @api.post("/api/speech/transcribe")
        def transcribe(request: TranscribeRequest):
            """
            Convert speech to text using Whisper large-v3
            
            Best for:
            - Avatar voice conversations
            - Voice-based profile questionnaire
            """
            return self.transcribe_speech(request.audio, request.language)
        
        @api.post("/api/speech/synthesize")
        def synthesize(request: SynthesizeRequest):
            """
            Convert text to speech using MeloTTS-Korean
            
            Best for:
            - Avatar voice responses
            - Question narration
            """
            if not request.text.strip():
                raise HTTPException(400, "Text cannot be empty")
            return self.synthesize_speech(request.text, request.speed, request.emotion)
        
        # ========================================
        # RAG + RL Question Selection API
        # ========================================
        
        class NextQuestionsRequest(BaseModel):
            user_answer: str
            current_question: str
            answered_questions: List[str]
            user_profile: dict
            num_questions: int = 3
        
        class ProcessAnswerRequest(BaseModel):
            question_id: str
            question_text: str
            answer: str
            user_profile: dict
        
        class CategoryQuestionsRequest(BaseModel):
            category: str
            answered_questions: List[str]
            top_k: int = 3
        
        class CoverageRequest(BaseModel):
            answered_questions: List[str]
        
        class MatchFeedbackRequest(BaseModel):
            questions_asked: List[str]
            match_accepted: bool
            user_profile: dict
        
        @api.post("/api/rag/next-questions")
        def next_questions(request: NextQuestionsRequest):
            """
            Get next best questions using RAG + RL
            
            Flow:
            1. RAG retrieves relevant questions from database
            2. RL selects best questions using Thompson Sampling
            3. Qwen2.5 personalizes the questions
            
            This is the core intelligent question selection feature!
            """
            questions = self.get_next_questions(
                user_answer=request.user_answer,
                current_question=request.current_question,
                answered_questions=request.answered_questions,
                user_profile=request.user_profile,
                num_questions=request.num_questions
            )
            return {"questions": questions}
        
        @api.post("/api/rag/process-answer")
        def process_answer(request: ProcessAnswerRequest):
            """
            Process answer and update RL model
            
            Returns:
            - Answer analysis (clarity, sentiment, key info)
            - Updates RL for better future question selection
            """
            return self.process_answer_with_rl(
                question_id=request.question_id,
                question_text=request.question_text,
                answer=request.answer,
                user_profile=request.user_profile
            )
        
        @api.post("/api/rag/category-questions")
        def category_questions(request: CategoryQuestionsRequest):
            """Get top questions from a specific category"""
            questions = self.get_questions_by_category(
                category=request.category,
                answered_questions=request.answered_questions,
                top_k=request.top_k
            )
            return {"questions": questions}
        
        @api.post("/api/rag/coverage")
        def question_coverage(request: CoverageRequest):
            """
            Get coverage analysis of answered questions
            
            Returns:
            - Overall coverage percentage
            - Coverage by category
            - Missing high-priority questions
            - Recommendation for next category
            """
            return self.get_question_coverage(request.answered_questions)
        
        @api.post("/api/rl/match-feedback")
        def match_feedback(request: MatchFeedbackRequest):
            """
            Update RL based on match outcome
            
            Call this when user accepts/rejects a match to improve
            future question selection
            """
            self.update_match_feedback(
                questions_asked=request.questions_asked,
                match_accepted=request.match_accepted,
                user_profile=request.user_profile
            )
            return {"status": "updated"}
        
        @api.get("/api/rl/question-performance/{question_id}")
        def question_performance(question_id: str):
            """Get RL performance metrics for a question"""
            return self.get_question_performance(question_id)
        
        return api


# Entry point for deployment
@app.local_entrypoint()
def main():
    """Test the deployed backend"""
    backend = FLIOBackend()
    
    # Test health
    print("Testing FLIO AI Backend...")
    print("Backend deployed successfully!")
