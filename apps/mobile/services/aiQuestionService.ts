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

export interface VerificationStatus {
  id_verified?: boolean;
  education_verified?: boolean;
  income_verified?: boolean;
  employment_verified?: boolean;
}

export interface MatchResult {
  user_id: string;
  compatibility_score: number;
  similarity_score: number;
  cultural_bonus: number;
  name?: string;
  nickname?: string;
  age?: number;
  trust_tier?: string;
  trust_score?: number;
  verification_status?: VerificationStatus;
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
    console.log('🔗 Connecting to backend at:', this.baseUrl);
  }

  /**
   * Get initial 40 questions from backend
   * Returns all questions ordered by effectiveness score
   */
  async getInitialQuestions(): Promise<Question[]> {
    console.log('🔄 Loading initial questions from backend...');
    
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
    console.log('✅ Successfully loaded questions from backend');
    
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
    console.log('📤 Submitting answer with AI analysis:', { questionId, answerValue });
    
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
    console.log('✅ Answer submitted successfully');
    
    if (data.analysis) {
      console.log('🧠 AI Analysis:', data.analysis.analysis);
      console.log(`📊 Clarity Score: ${data.analysis.clarity_score}/10`);
    }
    
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
    console.log('🧠 Creating AI profile embedding for matching...');
    
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
    console.log('✅ Profile embedding created successfully');
    console.log(`📊 Embedding dimension: ${data.profile_summary?.embedding_dimension}`);
    
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
    console.log('💕 Finding AI-powered compatibility matches...');
    
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
    console.log(`✅ Found ${data.total_found} compatible matches`);
    
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
    console.log('📋 Generating AI match explanation...');
    
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
    console.log('✅ Match explanation generated');
    console.log(`💖 Compatibility: ${(data.compatibility_score * 100).toFixed(1)}%`);
    
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
    minCompatibility: number = 0.3,
    rejectedMatchIds: string[] = []
  ): Promise<{
    matches: MatchResult[];
    total_found: number;
    error?: string;
  }> {
    console.log('🔄 Finding matches with AI preference analysis...');
    
    const response = await fetch(`${this.baseUrl}/matching/reshuffle-matches`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_id: userId,
        preference: preference,
        limit,
        min_compatibility: minCompatibility,
        rejected_match_ids: rejectedMatchIds
      })
    });
    
    if (!response.ok) {
      throw new Error(`Failed to find preference matches: ${response.status}`);
    }

    const data = await response.json();
    console.log(`✨ Found ${data.total_found} preference-based matches`);
    
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

    console.log('🔍 Testing backend connectivity...');
    const healthAbort = new AbortController();
    const healthTimeout = setTimeout(() => healthAbort.abort(), 5000);
    const healthResponse = await fetch(`${this.baseUrl.replace('/api/v1', '')}/health`, {
      method: 'GET',
      signal: healthAbort.signal,
    });
    clearTimeout(healthTimeout);
    
    if (healthResponse.ok) {
      result.backend = true;
      const healthData = await healthResponse.json();
      
      if (healthData.services?.supabase?.status === 'connected') {
        result.database = true;
        console.log('✅ Database connection verified');
      } else {
        result.errors.push('Database not connected');
      }
      
      if (healthData.services?.azure_openai?.status === 'connected') {
        result.ai_services = true;
        console.log('✅ AI services connection verified');
      } else {
        result.errors.push('Azure OpenAI not connected');
      }
      
      console.log('✅ Backend connectivity verified');
    } else {
      result.errors.push(`Backend health check failed: ${healthResponse.status}`);
    }

    return result;
  }

  /**
   * Get user's complete profile including answers and AI status
   */
  async getUserProfile(userId: string): Promise<UserProfile | null> {
    console.log('📋 Loading user profile from backend...');
    
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
    console.log('✅ User profile loaded successfully');
    console.log(`📊 Profile: ${data.total_answers} answers, ${data.profile_completion?.completion_percentage?.toFixed(1)}% complete`);
    
    return data as UserProfile;
  }

  /**
   * Delete a specific answer from user's profile
   */
  async deleteUserAnswer(userId: string, questionId: string): Promise<{
    success: boolean;
    message: string;
  }> {
    console.log('🗑️ Deleting user answer:', questionId);
    
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
    console.log('✅ Answer deleted successfully');
    
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

      // Fallback: fetch total from backend if profile unavailable
      try {
        const statsResponse = await fetch(`${this.baseUrl}/questions/stats`);
        if (statsResponse.ok) {
          const stats = await statsResponse.json();
          return { answered: 0, total: stats.total_questions, percentage: 0 };
        }
      } catch (statsError) {
        console.error('Failed to fetch question stats:', statsError);
      }
      return { answered: 0, total: 40, percentage: 0 }; // Fallback default if stats unavailable
    } catch (error) {
      console.error('Failed to get user progress:', error);
      // Fallback: try to get total from stats endpoint
      try {
        const statsResponse = await fetch(`${this.baseUrl}/questions/stats`);
        if (statsResponse.ok) {
          const stats = await statsResponse.json();
          return { answered: 0, total: stats.total_questions, percentage: 0 };
        }
      } catch (statsError) {
        console.error('Failed to fetch question stats:', statsError);
      }
      return { answered: 0, total: 40, percentage: 0 }; // Fallback default if stats unavailable
    }
  }

  // ========================================
  // Document Verification & Trust Score APIs
  // ========================================

  /**
   * Upload document for OCR verification
   */
  async uploadDocumentForVerification(
    userId: string,
    documentType: string,
    fileUrl: string
  ): Promise<{
    success: boolean;
    document_id?: string;
    verification_status?: string;
    match_score?: number;
    flags?: string[];
    error?: string;
  }> {
    console.log('📤 Uploading document for verification:', documentType);

    try {
      const response = await fetch(`${this.baseUrl}/verification/document/verify`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId,
          document_type: documentType,
          image_url: fileUrl,
          claimed_data: {}, // Backend requires this; populate with actual claimed data when available
        }),
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.status}`);
      }

      const data = await response.json();
      console.log('✅ Document uploaded successfully');
      console.log(`📊 Verification status: ${data.verification_status}`);

      return data;
    } catch (error: any) {
      console.error('Failed to upload document:', error);
      return {
        success: false,
        error: error.message,
      };
    }
  }

  /**
   * Get verification status for a specific document
   */
  async getDocumentStatus(documentId: string): Promise<{
    status: string;
    match_score?: number;
    flags?: string[];
    error?: string;
  }> {
    try {
      const response = await fetch(`${this.baseUrl}/verification/document/${documentId}/status`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Status check failed: ${response.status}`);
      }

      return await response.json();
    } catch (error: any) {
      console.error('Failed to get document status:', error);
      return {
        status: 'error',
        error: error.message,
      };
    }
  }

  /**
   * Get overall verification status for a user
   */
  async getVerificationStatus(userId: string): Promise<{
    id_verified: boolean;
    education_verified: boolean;
    income_verified: boolean;
    employment_verified: boolean;
    phone_verified: boolean;
    total_documents_uploaded: number;
    verified_documents_count: number;
  }> {
    try {
      const response = await fetch(`${this.baseUrl}/verification/status/${userId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Verification status check failed: ${response.status}`);
      }

      const data = await response.json();
      console.log(`✅ Verification status: ${data.verified_documents_count}/${data.total_documents_uploaded} verified`);

      return data;
    } catch (error: any) {
      console.error('Failed to get verification status:', error);
      return {
        id_verified: false,
        education_verified: false,
        income_verified: false,
        employment_verified: false,
        phone_verified: false,
        total_documents_uploaded: 0,
        verified_documents_count: 0,
      };
    }
  }

  /**
   * Get user's trust score and tier
   */
  async getTrustScore(userId: string): Promise<{
    user_id: string;
    total_trust_score: number;
    trust_tier: string;
    document_score: number;
    consistency_score: number;
    behavioral_score: number;
    completeness_score: number;
    last_calculated_at: string;
    calculation_details?: any;
  } | null> {
    console.log('🏆 Loading trust score for user:', userId);

    const response = await fetch(`${this.baseUrl}/trust/score/${userId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Trust score check failed: ${response.status}`);
    }

    const data = await response.json();
    console.log(`✅ Trust tier: ${data.trust_tier} (${(data.total_trust_score * 100).toFixed(1)}%)`);

    return data;
  }

  /**
   * Get user's trust tier (simpler version)
   */
  async getTrustTier(userId: string): Promise<{
    tier: string;
    score: number;
  }> {
    try {
      const response = await fetch(`${this.baseUrl}/trust/tier/${userId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        return { tier: 'unverified', score: 0 };
      }

      return await response.json();
    } catch (error) {
      console.error('Failed to get trust tier:', error);
      return { tier: 'unverified', score: 0 };
    }
  }

  /**
   * Manually recalculate trust score
   */
  async recalculateTrustScore(userId: string): Promise<{
    success: boolean;
    new_score?: number;
    new_tier?: string;
    error?: string;
  }> {
    console.log('🔄 Recalculating trust score...');

    try {
      const response = await fetch(`${this.baseUrl}/trust/recalculate/${userId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Recalculation failed: ${response.status}`);
      }

      const data = await response.json();
      console.log(`✅ New trust tier: ${data.new_tier} (${(data.new_score * 100).toFixed(1)}%)`);

      return data;
    } catch (error: any) {
      console.error('Failed to recalculate trust score:', error);
      return {
        success: false,
        error: error.message,
      };
    }
  }

  /**
   * Get trust score history
   */
  async getTrustScoreHistory(userId: string): Promise<{
    history: Array<{
      score: number;
      tier: string;
      timestamp: string;
    }>;
  } | null> {
    try {
      const response = await fetch(`${this.baseUrl}/trust/history/${userId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        return null;
      }

      return await response.json();
    } catch (error) {
      console.error('Failed to get trust score history:', error);
      return null;
    }
  }

}

// Export singleton instance
export const aiQuestionService = new AIQuestionService();