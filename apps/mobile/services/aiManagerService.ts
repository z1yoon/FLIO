/**
 * FLIO AI Manager Service
 * Frontend client for the AI manager API endpoints:
 *   - Conversational chat
 *   - Follow-up question generation
 *   - Profile diagnostics
 *   - Match feedback submission
 */

const BASE_URL = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface FollowupResult {
  is_ambiguous: boolean;
  ambiguity_score: number;
  followup_question: string | null;
  followup_example?: string | null;
  reason: string;
  log_id: string | null;
}

export interface DiagnosticIssue {
  severity: 'high' | 'medium' | 'low';
  issue: string;
  impact: string;
  solution: string;
}

export interface ProfileDiagnosis {
  overall_score: number;
  issues: DiagnosticIssue[];
  recommendations: string[];
  estimated_improvement_pct: number;
  market_percentile: number;
  summary_message: string;
}

export interface MatchFeedbackPayload {
  user_id: string;
  match_user_id: string;
  overall_rating: number;
  dimension_ratings?: {
    values_alignment?: number;
    lifestyle_match?: number;
    conversation_comfort?: number;
    marriage_seriousness?: number;
  };
  positive_aspects?: string[];
  dealbreaker_aspects?: string[];
  free_text_feedback?: string;
  implicit_signals?: {
    view_duration?: number;
    conversation_started?: boolean;
    photos_viewed?: number;
  };
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export interface ChatResponse {
  session_id: string;
  message: string;
  suggested_actions: string[];
  intent_detected: string;
}

export interface SessionHistory {
  session_id: string | null;
  messages: ChatMessage[];
  has_history: boolean;
  session_type: string;
  last_message_at: string | null;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function apiPost<T>(path: string, body: object): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const errText = await response.text();
    throw new Error(`API ${path} failed (${response.status}): ${errText}`);
  }
  return response.json();
}

async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`);
  if (!response.ok) {
    const errText = await response.text();
    throw new Error(`API ${path} failed (${response.status}): ${errText}`);
  }
  return response.json();
}

// ---------------------------------------------------------------------------
// AIManagerService
// ---------------------------------------------------------------------------

class AIManagerService {

  /**
   * Check whether a user's open-ended answer is ambiguous.
   * If ambiguous, returns a follow-up question.
   * Only triggers for open-ended / text-type questions.
   */
  async checkForFollowup(
    userId: string,
    questionId: string,
    questionText: string,
    answer: string,
    questionCategory: string,
    previousAnswers: { question_id: string; question_text?: string; answer_value: string }[] = [],
  ): Promise<FollowupResult> {
    return apiPost<FollowupResult>('/ai-manager/followup-question', {
      user_id: userId,
      question_id: questionId,
      question_text: questionText,
      answer,
      question_category: questionCategory,
      previous_answers: previousAnswers,
    });
  }

  /**
   * Save user's answer to a previously generated follow-up question.
   */
  async saveFollowupAnswer(logId: string, answer: string): Promise<void> {
    await apiPost('/ai-manager/followup-question/answer', { log_id: logId, answer });
  }

  /**
   * Run a full AI profile quality diagnosis.
   * Pass forceRefresh=true to bypass cache.
   */
  async diagnoseProfile(userId: string, forceRefresh = false): Promise<ProfileDiagnosis> {
    return apiPost<ProfileDiagnosis>('/ai-manager/diagnose-profile', {
      user_id: userId,
      force_refresh: forceRefresh,
    });
  }

  /**
   * Submit structured feedback after viewing a match.
   */
  async submitMatchFeedback(payload: MatchFeedbackPayload): Promise<{ success: boolean; message: string; needs_diagnosis: boolean }> {
    return apiPost('/ai-manager/feedback', payload);
  }

  /**
   * Send a message to the AI manager and receive a conversational response.
   */
  async chat(userId: string, message: string, sessionId?: string): Promise<ChatResponse> {
    return apiPost<ChatResponse>('/ai-manager/chat', {
      user_id: userId,
      message,
      session_id: sessionId ?? null,
    });
  }

  /**
   * Load conversation history for the current user.
   */
  async getSessionHistory(userId: string, limit = 30): Promise<SessionHistory> {
    return apiGet<SessionHistory>(`/ai-manager/session/${userId}?limit=${limit}`);
  }
}

export const aiManagerService = new AIManagerService();
