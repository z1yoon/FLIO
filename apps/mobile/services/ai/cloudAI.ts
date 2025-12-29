/**
 * Cloud AI Services
 * 
 * Calls to Modal.com hosted AI services
 * Used for heavy ML tasks that require GPU
 * 
 * Models:
 * - Face: InsightFace/ArcFace (512D)
 * - Matching: BGE-M3 (1024D hybrid)
 * - Questions: Qwen2.5-7B-Instruct
 */

const AI_BASE_URL = process.env.EXPO_PUBLIC_AI_API_URL || 'http://localhost:8000';

// ========================================
// Types
// ========================================

interface FaceEmbeddingResponse {
  embedding: number[];
  face_detected: boolean;
  error?: string;
}

interface FaceVerifyResponse {
  verified: boolean;
  similarity: number;
  threshold: number;
  message: string;
}

interface LivenessResponse {
  is_live: boolean;
  blink_count: number;
  message: string;
}

interface ProfileEmbeddingResponse {
  dense: number[];
  sparse?: Record<string, number>;
  colbert?: number[][];
}

// Question Analysis Types
interface AnswerAnalysis {
  clarity_score: number;
  sentiment: 'positive' | 'neutral' | 'negative';
  key_info: string[];
  is_vague: boolean;
  needs_followup: boolean;
  followup_reason: string | null;
}

interface FollowupQuestion {
  question: string;
  category: string;
  priority: 'high' | 'medium' | 'low';
  goal: string;
}

interface SuggestedQuestion {
  question: string;
  category: string;
  reason: string;
}

interface FilterSuggestions {
  age_range?: [number, number];
  location_radius_km?: number;
  priority_changes?: string[];
}

interface ReshuffleAnalysis {
  analysis: string;
  user_intent: string;
  missing_info: string[];
  needs_questions: boolean;
  suggested_questions: SuggestedQuestion[];
  filter_suggestions: FilterSuggestions;
  avatar_message: string;
}

interface MatchPoint {
  category: string;
  type: 'match' | 'partial' | 'discuss';
  icon: string;
  description: string;
}

interface MatchExplanation {
  summary: string;
  match_points: MatchPoint[];
  conversation_starters: string[];
}

// ========================================
// Face Verification API
// ========================================

/**
 * Extract face embedding from image
 * Uses InsightFace/ArcFace model (512D vector)
 */
export async function extractFaceEmbedding(
  imageBase64: string
): Promise<FaceEmbeddingResponse> {
  const response = await fetch(`${AI_BASE_URL}/api/face/embed`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      image: imageBase64,
    }),
  });

  if (!response.ok) {
    throw new Error(`Face embedding failed: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Verify if two face embeddings match (85% threshold)
 */
export async function verifyFace(
  profileEmbedding: number[],
  liveEmbedding: number[],
  threshold: number = 0.85
): Promise<FaceVerifyResponse> {
  const response = await fetch(`${AI_BASE_URL}/api/face/verify`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      profile_embedding: profileEmbedding,
      live_embedding: liveEmbedding,
      threshold,
    }),
  });

  if (!response.ok) {
    throw new Error(`Face verification failed: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Check liveness from video frames
 * Detects blinks and head movement to prevent photo attacks
 */
export async function checkLiveness(
  framesBase64: string[]
): Promise<LivenessResponse> {
  const response = await fetch(`${AI_BASE_URL}/api/face/liveness`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      frames: framesBase64,
    }),
  });

  if (!response.ok) {
    throw new Error(`Liveness check failed: ${response.statusText}`);
  }

  return response.json();
}

// ========================================
// Profile Matching API (BGE-M3)
// ========================================

/**
 * Generate profile embedding for matching
 * Uses BGE-M3 model (1024D dense + sparse + colbert)
 */
export async function generateProfileEmbedding(
  profileData: Record<string, string>
): Promise<ProfileEmbeddingResponse> {
  const response = await fetch(`${AI_BASE_URL}/api/match/embed`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      profile: profileData,
    }),
  });

  if (!response.ok) {
    throw new Error(`Profile embedding failed: ${response.statusText}`);
  }

  return response.json();
}

// ========================================
// Adaptive Question API (Qwen2.5-7B)
// ========================================

/**
 * Analyze user's answer for clarity and completeness
 * 
 * Use this to determine if follow-up questions are needed
 */
export async function analyzeAnswer(
  question: string,
  answer: string
): Promise<AnswerAnalysis> {
  const response = await fetch(`${AI_BASE_URL}/api/questions/analyze`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      question,
      answer,
    }),
  });

  if (!response.ok) {
    throw new Error(`Answer analysis failed: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Generate follow-up questions for vague answers
 * 
 * This is the core feature that makes FLIO different:
 * - Acts like a 결혼정보회사 매니저
 * - Digs deeper into vague answers
 * - Non-judgmental AI encourages honesty
 */
export async function generateFollowupQuestions(
  question: string,
  answer: string,
  userProfile: Record<string, any>,
  numQuestions: number = 3
): Promise<FollowupQuestion[]> {
  const response = await fetch(`${AI_BASE_URL}/api/questions/generate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      question,
      answer,
      user_profile: userProfile,
      num_questions: numQuestions,
    }),
  });

  if (!response.ok) {
    throw new Error(`Question generation failed: ${response.statusText}`);
  }

  const data = await response.json();
  return data.questions;
}

/**
 * Analyze why user wants to reshuffle matches
 * 
 * Flow:
 * 1. User clicks "Reshuffle" button
 * 2. We ask why (predefined options + free text)
 * 3. AI analyzes the reason
 * 4. If needed, AI generates additional questions
 * 5. After questions answered, reshuffle with improved profile
 */
export async function analyzeReshuffleRequest(
  userProfile: Record<string, any>,
  currentFilters: Record<string, any>,
  reshuffleReason: string,
  rejectedProfiles?: Record<string, any>[]
): Promise<ReshuffleAnalysis> {
  const response = await fetch(`${AI_BASE_URL}/api/questions/reshuffle-analysis`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      user_profile: userProfile,
      current_filters: currentFilters,
      reshuffle_reason: reshuffleReason,
      rejected_profiles: rejectedProfiles,
    }),
  });

  if (!response.ok) {
    throw new Error(`Reshuffle analysis failed: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Generate human-readable match explanation
 * 
 * Returns:
 * - Summary of why they match
 * - List of match points (✅ match, 🔶 partial, 💬 discuss)
 * - Conversation starters
 */
export async function generateMatchExplanation(
  profileA: Record<string, any>,
  profileB: Record<string, any>,
  matchScore: number
): Promise<MatchExplanation> {
  const response = await fetch(`${AI_BASE_URL}/api/questions/match-explanation`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      profile_a: profileA,
      profile_b: profileB,
      match_score: matchScore,
    }),
  });

  if (!response.ok) {
    throw new Error(`Match explanation failed: ${response.statusText}`);
  }

  return response.json();
}

// ========================================
// Speech API (STT/TTS)
// ========================================

interface TranscriptionResponse {
  text: string;
  segments: Array<{ start: number; end: number; text: string }>;
  language: string;
  confidence: number;
  error?: string;
}

interface SpeechSynthesisResponse {
  audio: string;  // Base64 WAV
  duration_seconds: number;
  sample_rate: number;
  error?: string;
}

/**
 * Transcribe speech to text using Whisper large-v3
 * 
 * Use for:
 * - Avatar voice conversations
 * - Voice-based profile questionnaire
 */
export async function transcribeSpeech(
  audioBase64: string,
  language: string = 'ko'
): Promise<TranscriptionResponse> {
  const response = await fetch(`${AI_BASE_URL}/api/speech/transcribe`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ audio: audioBase64, language }),
  });

  if (!response.ok) {
    throw new Error(`Transcription failed: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Synthesize speech from text using MeloTTS-Korean
 * 
 * Use for:
 * - Avatar voice responses
 * - Question narration
 */
export async function synthesizeSpeech(
  text: string,
  speed: number = 1.0,
  emotion: 'neutral' | 'happy' | 'sad' | 'angry' = 'neutral'
): Promise<SpeechSynthesisResponse> {
  const response = await fetch(`${AI_BASE_URL}/api/speech/synthesize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, speed, emotion }),
  });

  if (!response.ok) {
    throw new Error(`Speech synthesis failed: ${response.statusText}`);
  }

  return response.json();
}

// ========================================
// RAG + RL Question Selection API
// ========================================

interface RAGQuestion {
  id: string;
  text: string;
  category: string;
  priority: 'high' | 'medium' | 'low';
  tags: string[];
  relevance_score: number;
  selection_method?: string;
  selection_score?: number;
  personalized_text?: string;
}

interface QuestionCoverage {
  total_questions: number;
  answered: number;
  coverage_percent: number;
  by_category: Record<string, { total: number; answered: number; percent: number }>;
  missing_high_priority: string[];
  recommendation: string;
}

interface QuestionPerformance {
  question_id: string;
  expected_success_rate: number;
  confidence: number;
  times_asked: number;
  times_answered: number;
  answer_rate: number;
  avg_clarity_score: number;
  led_to_matches: number;
  last_updated: string;
}

/**
 * Get next best questions using RAG + RL
 * 
 * This is the core intelligent question selection:
 * 1. RAG retrieves relevant questions from database
 * 2. RL selects best questions using Thompson Sampling
 * 3. Qwen2.5 personalizes the questions
 */
export async function getNextQuestions(
  userAnswer: string,
  currentQuestion: string,
  answeredQuestions: string[],
  userProfile: Record<string, any>,
  numQuestions: number = 3
): Promise<RAGQuestion[]> {
  const response = await fetch(`${AI_BASE_URL}/api/rag/next-questions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_answer: userAnswer,
      current_question: currentQuestion,
      answered_questions: answeredQuestions,
      user_profile: userProfile,
      num_questions: numQuestions,
    }),
  });

  if (!response.ok) {
    throw new Error(`Question selection failed: ${response.statusText}`);
  }

  const data = await response.json();
  return data.questions;
}

/**
 * Process answer and update RL model
 * 
 * Call this after user answers a question to:
 * 1. Get answer analysis
 * 2. Update RL for better future selection
 */
export async function processAnswerWithRL(
  questionId: string,
  questionText: string,
  answer: string,
  userProfile: Record<string, any>
): Promise<AnswerAnalysis> {
  const response = await fetch(`${AI_BASE_URL}/api/rag/process-answer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question_id: questionId,
      question_text: questionText,
      answer,
      user_profile: userProfile,
    }),
  });

  if (!response.ok) {
    throw new Error(`Answer processing failed: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get questions from a specific category
 */
export async function getQuestionsByCategory(
  category: string,
  answeredQuestions: string[],
  topK: number = 3
): Promise<RAGQuestion[]> {
  const response = await fetch(`${AI_BASE_URL}/api/rag/category-questions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      category,
      answered_questions: answeredQuestions,
      top_k: topK,
    }),
  });

  if (!response.ok) {
    throw new Error(`Category questions failed: ${response.statusText}`);
  }

  const data = await response.json();
  return data.questions;
}

/**
 * Get coverage analysis of answered questions
 * 
 * Use to show progress and suggest next category
 */
export async function getQuestionCoverage(
  answeredQuestions: string[]
): Promise<QuestionCoverage> {
  const response = await fetch(`${AI_BASE_URL}/api/rag/coverage`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ answered_questions: answeredQuestions }),
  });

  if (!response.ok) {
    throw new Error(`Coverage analysis failed: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Update RL based on match outcome
 * 
 * Call when user accepts/rejects a match to improve
 * future question selection
 */
export async function submitMatchFeedback(
  questionsAsked: string[],
  matchAccepted: boolean,
  userProfile: Record<string, any>
): Promise<void> {
  const response = await fetch(`${AI_BASE_URL}/api/rl/match-feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      questions_asked: questionsAsked,
      match_accepted: matchAccepted,
      user_profile: userProfile,
    }),
  });

  if (!response.ok) {
    throw new Error(`Match feedback failed: ${response.statusText}`);
  }
}

/**
 * Get RL performance metrics for a question
 */
export async function getQuestionPerformance(
  questionId: string
): Promise<QuestionPerformance> {
  const response = await fetch(`${AI_BASE_URL}/api/rl/question-performance/${questionId}`);

  if (!response.ok) {
    throw new Error(`Performance fetch failed: ${response.statusText}`);
  }

  return response.json();
}

// ========================================
// Feedback & Verification API
// ========================================

interface PostMeetingFeedback {
  met_user_id: string;
  overall: 'accurate' | 'somewhat_different' | 'very_different';
  photos: string;
  height: string;
  job?: string;
}

interface UserTrustStatus {
  user_id: string;
  status: 'verified' | 'flagged' | 'blocked';
  trust_score: number;
  is_blocked: boolean;
  blocked_until?: string;
  flagged_fields: string[];
}

interface ABVariant {
  id: string;
  name: string;
  config: Record<string, any>;
}

/**
 * Submit feedback after meeting someone in person
 * 
 * This is the SECRET verification system:
 * - User reports if profile info was accurate
 * - Reported user NEVER knows who reported them
 * - 2+ reports = user is blocked until they correct info
 */
export async function submitPostMeetingFeedback(
  reporterId: string,
  feedback: PostMeetingFeedback
): Promise<{ status: string; message: string }> {
  const response = await fetch(`${AI_BASE_URL}/api/feedback/post-meeting-feedback?reporter_id=${reporterId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(feedback),
  });

  if (!response.ok) {
    throw new Error(`Feedback submission failed: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Check if a user is blocked or has flagged fields
 * Call before showing user in matches
 */
export async function checkUserTrustStatus(userId: string): Promise<UserTrustStatus> {
  const response = await fetch(`${AI_BASE_URL}/api/feedback/user-status/${userId}`);

  if (!response.ok) {
    throw new Error(`Status check failed: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get notification if user needs to update their profile
 * Returns null if no action needed
 */
export async function getUserNotification(userId: string): Promise<{
  type: 'blocked' | 'warning';
  title: string;
  message: string;
  fields_to_update: string[];
  action_required: boolean;
} | null> {
  const response = await fetch(`${AI_BASE_URL}/api/feedback/user-notification/${userId}`);
  
  if (!response.ok) {
    return null;
  }

  return response.json();
}

/**
 * Record match outcome for RL learning
 */
export async function recordMatchOutcome(
  matchId: string,
  userAId: string,
  userBId: string,
  outcome: 'dating' | 'met' | 'chatting' | 'rejected' | 'no_response',
  questionsAskedA: string[] = [],
  questionsAskedB: string[] = [],
  daysActive: number = 0
): Promise<{ reward: number }> {
  const response = await fetch(`${AI_BASE_URL}/api/feedback/match-outcome`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      match_id: matchId,
      user_a_id: userAId,
      user_b_id: userBId,
      outcome,
      questions_asked_a: questionsAskedA,
      questions_asked_b: questionsAskedB,
      days_active: daysActive,
    }),
  });

  if (!response.ok) {
    throw new Error(`Match outcome recording failed: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get A/B test variant for a user
 */
export async function getABVariant(
  experimentId: string,
  userId: string
): Promise<{ variant: ABVariant | null; in_experiment: boolean }> {
  const response = await fetch(`${AI_BASE_URL}/api/feedback/ab/get-variant`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      experiment_id: experimentId,
      user_id: userId,
    }),
  });

  if (!response.ok) {
    throw new Error(`A/B variant fetch failed: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Record A/B test conversion
 */
export async function recordABConversion(
  experimentId: string,
  userId: string,
  metricName: string = 'conversion',
  metricValue: number = 1.0
): Promise<void> {
  await fetch(`${AI_BASE_URL}/api/feedback/ab/record-conversion`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      experiment_id: experimentId,
      user_id: userId,
      metric_name: metricName,
      metric_value: metricValue,
    }),
  });
}

// ========================================
// Export
// ========================================

export default {
  // Face Verification
  extractFaceEmbedding,
  verifyFace,
  checkLiveness,
  // Profile Matching
  generateProfileEmbedding,
  // Adaptive Questions (Qwen2.5)
  analyzeAnswer,
  generateFollowupQuestions,
  analyzeReshuffleRequest,
  generateMatchExplanation,
  // Speech (STT/TTS)
  transcribeSpeech,
  synthesizeSpeech,
  // RAG + RL Question Selection
  getNextQuestions,
  processAnswerWithRL,
  getQuestionsByCategory,
  getQuestionCoverage,
  submitMatchFeedback,
  getQuestionPerformance,
  // Feedback & Verification
  submitPostMeetingFeedback,
  checkUserTrustStatus,
  getUserNotification,
  recordMatchOutcome,
  // A/B Testing
  getABVariant,
  recordABConversion,
};

// Export types
export type {
  FaceEmbeddingResponse,
  FaceVerifyResponse,
  LivenessResponse,
  ProfileEmbeddingResponse,
  AnswerAnalysis,
  FollowupQuestion,
  SuggestedQuestion,
  FilterSuggestions,
  ReshuffleAnalysis,
  MatchPoint,
  MatchExplanation,
  TranscriptionResponse,
  SpeechSynthesisResponse,
  RAGQuestion,
  QuestionCoverage,
  QuestionPerformance,
};
