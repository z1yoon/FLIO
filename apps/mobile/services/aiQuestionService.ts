/**
 * AI Question Service
 * 
 * Connects to FLIO AI Backend for adaptive questionnaire
 * Handles 40 questions with conditional logic and user context
 */

export interface Question {
  id: string;
  text: string;
  category: string;
  type: 'choice' | 'text' | 'scale';
  options?: string[];
  effectiveness_score?: number;
  placeholder?: string;
  maxLength?: number;
}

export interface Answer {
  question_id: string;
  answer_value: string;
  importance?: number;
  is_dealbreaker?: boolean;
  timestamp: string;
  question_text?: string;
  category?: string;
}

export interface UserProfile {
  user_id: string;
  answers: Answer[];
  total_answers: number;
  embedding_status: {
    has_embedding: boolean;
    embedding_dimension?: number;
    created_at?: string;
    message: string;
  };
  profile_completion: {
    total_questions: number;
    answered_questions: number;
    completion_percentage: number;
    can_start_matching: boolean;
  };
}

export interface AnswerAnalysis {
  clarity_score: number;
  is_vague: boolean;
  key_insights: string[];
  analysis: string;
}

export interface UserContext {
  user_id: string;
  previous_answers: Answer[];
  demographics: {
    age?: number;
    gender?: string;
    location?: string;
    education?: string;
    occupation?: string;
  };
}

export interface MatchResult {
  user_id: string;
  compatibility_score: number;
  similarity_score: number;
  cultural_bonus: number;
  name?: string;
  nickname?: string;
  age?: number;
}

export interface MatchExplanation {
  compatibility_score: number;
  summary: string;
  statistical_insights: string[];
  compatibility_graphs: { [key: string]: { match_percentage: number; total_questions: number; matching_questions: number; high_importance_matches: number } };
  personalized_insights: {
    user_a_personality: { name: string; key_traits: string[]; description: string };
    user_b_personality: { name: string; key_traits: string[]; description: string };
    why_you_match: string[];
    complementary_strengths: string[];
    match_summary: string;
  };
  ai_analysis?: {
    summary: string;
    compatibility_reasons: string[];
    conversation_starters: string[];
    match_percentage: number;
  };
  conversation_starters: string[];
  detailed_scores: { [key: string]: number };
  score_breakdown: { [key: string]: string };
}

export interface AIQuestionResponse {
  questions: Question[];
  next_question?: Question;
  completion_status: {
    total_questions: number;
    answered_questions: number;
    remaining_questions: number;
    progress_percentage: number;
  };
}

class AIQuestionService {
  private baseUrl: string;
  
  constructor() {
    this.baseUrl = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
  }

  /**
   * Get initial 40 questions from backend
   * Returns all questions ordered by effectiveness score
   */
  async getInitialQuestions(): Promise<Question[]> {
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000);
    
    const response = await fetch(`${this.baseUrl}/questions/initial`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      signal: controller.signal,
    });
    
    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new Error(`Failed to load questions: ${response.status}`);
    }

    const data = await response.json();
    
    return data.questions.map((q: any) => ({
      id: q.id,
      text: q.text,
      category: q.category,
      type: q.type,
      options: q.options,
      effectiveness_score: q.effectiveness_score,
      placeholder: q.placeholder,
      maxLength: q.maxLength
    }));
  }

  /**
   * Submit answer with AI analysis
   * Returns analysis and whether follow-up questions are needed
   */
  async submitAnswer(
    userId: string,
    questionId: string,
    answerValue: string,
    importance: number = 3,
    isDealbreaker: boolean = false
  ): Promise<{
    success: boolean;
    analysis?: AnswerAnalysis;
    needs_followup?: boolean;
    message: string;
  }> {
    
    const response = await fetch(`${this.baseUrl}/questions/answer`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_id: userId,
        question_id: questionId,
        answer_value: answerValue,
        importance,
        is_dealbreaker: isDealbreaker
      })
    });
    
    if (!response.ok) {
      throw new Error(`Failed to submit answer: ${response.status}`);
    }

    const data = await response.json();
    
    return {
      success: data.success,
      analysis: data.analysis,
      needs_followup: data.needs_followup,
      message: data.message
    };
  }

  /**
   * Create user profile embedding after questionnaire completion
   * This enables AI-powered matching
   */
  async createProfileEmbedding(userId: string): Promise<{
    success: boolean;
    message: string;
    profile_summary?: {
      nickname: string;
      age: number;
      answer_count: number;
      embedding_dimension: number;
    };
  }> {
    
    const response = await fetch(`${this.baseUrl}/matching/profile/create-embedding?user_id=${userId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      }
    });
    
    if (!response.ok) {
      throw new Error(`Failed to create embedding: ${response.status}`);
    }

    const data = await response.json();
    
    return {
      success: data.success,
      message: data.message,
      profile_summary: data.profile_summary
    };
  }

  /**
   * Find compatible matches using AI similarity
   */
  async findMatches(
    userId: string, 
    limit: number = 10, 
    minCompatibility: number = 0.3
  ): Promise<{
    matches: MatchResult[];
    total_found: number;
    error?: string;
  }> {
    
    const response = await fetch(`${this.baseUrl}/matching/matches/${userId}?limit=${limit}&min_compatibility=${minCompatibility}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      }
    });
    
    if (!response.ok) {
      throw new Error(`Failed to find matches: ${response.status}`);
    }

    const data = await response.json();
    
    return {
      matches: data.matches,
      total_found: data.total_found
    };
  }

  /**
   * Get detailed explanation for why two users match
   */
  async getMatchExplanation(userAId: string, userBId: string): Promise<{
    explanation?: MatchExplanation;
    error?: string;
  }> {
    
    const response = await fetch(`${this.baseUrl}/matching/match-explanation/${userAId}/${userBId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      }
    });
    
    if (!response.ok) {
      throw new Error(`Failed to get explanation: ${response.status}`);
    }

    const data = await response.json();
    
    return {
      explanation: {
        compatibility_score: data.compatibility_score,
        summary: data.summary,
        statistical_insights: data.statistical_insights || [],
        compatibility_graphs: data.compatibility_graphs || {},
        personalized_insights: data.personalized_insights || {
          user_a_personality: { name: '', key_traits: [], description: '' },
          user_b_personality: { name: '', key_traits: [], description: '' },
          why_you_match: [],
          complementary_strengths: [],
          match_summary: ''
        },
        ai_analysis: data.ai_analysis,
        conversation_starters: data.conversation_starters || [],
        detailed_scores: data.detailed_scores || {},
        score_breakdown: data.score_breakdown || {}
      }
    };
  }

  /**
   * Check if user has a valid profile embedding for matching
   */
  async checkEmbeddingStatus(userId: string): Promise<{
    has_embedding: boolean;
    embedding_dimension?: number;
    message: string;
  }> {
    const response = await fetch(`${this.baseUrl}/matching/profile/${userId}/embedding-status`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      }
    });
    
    if (!response.ok) {
      throw new Error(`Failed to check status: ${response.status}`);
    }

    return await response.json();
  }

  /**
   * Find matches with specific user preference for reshuffling
   */
  async findMatchesWithPreference(
    userId: string,
    preference: string,
    limit: number = 10,
    minCompatibility: number = 0.3
  ): Promise<{
    matches: MatchResult[];
    total_found: number;
    error?: string;
  }> {
    
    const response = await fetch(`${this.baseUrl}/matching/reshuffle-matches`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_id: userId,
        preference: preference,
        limit,
        min_compatibility: minCompatibility
      })
    });
    
    if (!response.ok) {
      throw new Error(`Failed to find preference matches: ${response.status}`);
    }

    const data = await response.json();
    
    return {
      matches: data.matches,
      total_found: data.total_found
    };
  }

  /**
   * Test full system connectivity: Frontend -> Backend -> Database -> AI
   */
  async testSystemConnectivity(): Promise<{
    frontend: boolean;
    backend: boolean;
    database: boolean;
    ai_services: boolean;
    errors: string[];
  }> {
    const result = {
      frontend: true,
      backend: false,
      database: false,
      ai_services: false,
      errors: [] as string[]
    };

    const healthResponse = await fetch(`${this.baseUrl.replace('/api/v1', '')}/health`, {
      method: 'GET',
      timeout: 5000
    });
    
    if (healthResponse.ok) {
      result.backend = true;
      const healthData = await healthResponse.json();
      
      if (healthData.services?.supabase?.status === 'connected') {
        result.database = true;
      } else {
        result.errors.push('Database not connected');
      }
      
      if (healthData.services?.azure_openai?.status === 'connected') {
        result.ai_services = true;
      } else {
        result.errors.push('Azure OpenAI not connected');
      }
    } else {
      result.errors.push(`Backend health check failed: ${healthResponse.status}`);
    }

    return result;
  }

  /**
   * Get user's complete profile including answers and AI status
   */
  async getUserProfile(userId: string): Promise<UserProfile | null> {
    
    const response = await fetch(`${this.baseUrl}/questions/user/${userId}/profile`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      }
    });
    
    if (!response.ok) {
      throw new Error(`Failed to load profile: ${response.status}`);
    }

    const data = await response.json();
    
    return data as UserProfile;
  }

  /**
   * Delete a specific answer from user's profile
   */
  async deleteUserAnswer(userId: string, questionId: string): Promise<{
    success: boolean;
    message: string;
  }> {
    
    const response = await fetch(`${this.baseUrl}/questions/user/${userId}/answer/${questionId}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      }
    });
    
    if (!response.ok) {
      throw new Error(`Failed to delete answer: ${response.status}`);
    }

    const data = await response.json();
    
    return {
      success: data.success || true,
      message: data.message || '답변이 삭제되었습니다.'
    };
  }

  /**
   * Get user's progress and completion status
   */
  async getUserProgress(userId: string): Promise<{
    answered: number;
    total: number;
    percentage: number;
  }> {
    try {
      const profile = await this.getUserProfile(userId);
      
      if (profile) {
        return {
          answered: profile.total_answers,
          total: profile.profile_completion.total_questions,
          percentage: profile.profile_completion.completion_percentage
        };
      }
      
      return { answered: 0, total: 40, percentage: 0 };
    } catch (error) {
      console.error('Failed to get user progress:', error);
      return { answered: 0, total: 40, percentage: 0 };
    }
  }

}

// Export singleton instance
export const aiQuestionService = new AIQuestionService();