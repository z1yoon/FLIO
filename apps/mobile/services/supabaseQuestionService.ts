/**
 * Supabase Questions Service
 * 
 * Production-level service for loading questions directly from Supabase
 * Replaces mock/fallback logic with robust database integration
 */

import { supabase } from './supabase/client';

export interface Question {
  id: string;
  text: string;
  category: string;
  type: 'choice' | 'text' | 'scale';
  options?: string[];
  effectiveness_score?: number;
  placeholder?: string;
  maxLength?: number;
  can_be_dealbreaker?: boolean;
  base_weight?: number;
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

class SupabaseQuestionService {
  private readonly TOTAL_QUESTIONS = 45;
  private readonly MIN_QUESTIONS_FOR_MATCHING = 10;

  /**
   * Load all questions from Supabase database
   * Production implementation with proper error handling
   */
  async getAllQuestions(userId?: string): Promise<Question[]> {
    try {
      console.log('🔄 Loading questions from Supabase database...');

      // Use stored function if user ID provided for personalized questions
      if (userId) {
        const { data, error } = await supabase.rpc('get_questions_for_user', {
          p_user_id: userId,
          p_limit: this.TOTAL_QUESTIONS
        });

        if (error) {
          console.error('❌ Error calling get_questions_for_user:', error);
          throw new Error(`Database function error: ${error.message}`);
        }

        if (data && data.length > 0) {
          console.log(`✅ Loaded ${data.length} personalized questions for user`);
          return this.transformDatabaseQuestions(data);
        }
      }

      // Direct query for all active questions
      const { data, error } = await supabase
        .from('questions')
        .select(`
          id,
          category,
          text_ko,
          text_en,
          answer_type,
          options,
          base_weight,
          effectiveness_score,
          can_be_dealbreaker,
          placeholder,
          max_length
        `)
        .eq('is_active', true)
        .order('effectiveness_score', { ascending: false })
        .order('base_weight', { ascending: false });

      if (error) {
        console.error('❌ Supabase query error:', error);
        throw new Error(`Database query failed: ${error.message}`);
      }

      if (!data || data.length === 0) {
        throw new Error('No questions found in database');
      }

      console.log(`✅ Successfully loaded ${data.length} questions from Supabase`);
      return this.transformDatabaseQuestions(data);

    } catch (error) {
      console.error('❌ Failed to load questions from Supabase:', error);
      throw error;
    }
  }

  /**
   * Get questions excluding those already answered by user
   */
  async getUnansweredQuestions(userId: string, limit?: number): Promise<Question[]> {
    try {
      console.log(`🔄 Loading unanswered questions for user: ${userId}`);

      // Get user's answered questions
      const { data: answeredQuestions, error: answersError } = await supabase
        .from('user_answers')
        .select('question_id')
        .eq('user_id', userId);

      if (answersError) {
        console.error('❌ Error fetching user answers:', answersError);
        throw new Error(`Failed to fetch user answers: ${answersError.message}`);
      }

      const answeredIds = answeredQuestions?.map(a => a.question_id) || [];
      console.log(`📊 User has answered ${answeredIds.length} questions`);

      // Get unanswered questions
      let query = supabase
        .from('questions')
        .select(`
          id,
          category,
          text_ko,
          text_en,
          answer_type,
          options,
          base_weight,
          effectiveness_score,
          can_be_dealbreaker,
          placeholder,
          max_length
        `)
        .eq('is_active', true)
        .not('id', 'in', `(${answeredIds.map(id => `'${id}'`).join(',')})`);

      if (limit) {
        query = query.limit(limit);
      }

      // Order by answer_type first (choice before text), then by effectiveness_score
      query = query.order('answer_type', { ascending: true }).order('effectiveness_score', { ascending: false });

      const { data, error } = await query;

      if (error) {
        console.error('❌ Error fetching unanswered questions:', error);
        throw new Error(`Database query failed: ${error.message}`);
      }

      const questions = this.transformDatabaseQuestions(data || []);
      console.log(`✅ Found ${questions.length} unanswered questions`);
      
      return questions;

    } catch (error) {
      console.error('❌ Failed to get unanswered questions:', error);
      throw error;
    }
  }

  /**
   * Submit user answer to Supabase
   */
  async submitAnswer(
    userId: string,
    questionId: string,
    answerValue: string,
    importance: number = 3,
    isDealbreaker: boolean = false
  ): Promise<{
    success: boolean;
    message: string;
    answer?: Answer;
  }> {
    try {
      console.log(`📤 Submitting answer for question ${questionId}`);

      // Insert or update answer
      const { data, error } = await supabase
        .from('user_answers')
        .upsert({
          user_id: userId,
          question_id: questionId,
          answer_value: answerValue,
          importance,
          is_dealbreaker: isDealbreaker,
          updated_at: new Date().toISOString()
        }, {
          onConflict: 'user_id,question_id'
        })
        .select()
        .single();

      if (error) {
        console.error('❌ Error submitting answer:', error);
        throw new Error(`Failed to submit answer: ${error.message}`);
      }

      console.log('✅ Answer submitted successfully');

      // Get question details for response
      const { data: questionData, error: questionError } = await supabase
        .from('questions')
        .select('text_ko, category')
        .eq('id', questionId)
        .single();

      const answer: Answer = {
        question_id: questionId,
        answer_value: answerValue,
        importance,
        is_dealbreaker: isDealbreaker,
        timestamp: data.created_at || new Date().toISOString(),
        question_text: questionData?.text_ko,
        category: questionData?.category
      };

      return {
        success: true,
        message: 'Answer saved successfully',
        answer
      };

    } catch (error) {
      console.error('❌ Failed to submit answer:', error);
      return {
        success: false,
        message: error instanceof Error ? error.message : 'Failed to submit answer'
      };
    }
  }

  /**
   * Get user profile with all answers and completion status
   */
  async getUserProfile(userId: string): Promise<UserProfile | null> {
    try {
      console.log(`📋 Loading user profile: ${userId}`);

      // Use database function to get complete profile
      const { data, error } = await supabase.rpc('get_user_profile_summary', {
        p_user_id: userId
      });

      if (error) {
        console.error('❌ Error getting user profile:', error);
        throw new Error(`Failed to get user profile: ${error.message}`);
      }

      if (!data) {
        console.log('📭 No profile data found for user');
        return null;
      }

      const profileData = typeof data === 'string' ? JSON.parse(data) : data;
      
      // Calculate completion metrics
      const totalAnswers = profileData.total_answers || 0;
      const completionPercentage = Math.min(100, (totalAnswers / this.TOTAL_QUESTIONS) * 100);
      const canStartMatching = totalAnswers >= this.MIN_QUESTIONS_FOR_MATCHING;

      const profile: UserProfile = {
        user_id: userId,
        answers: profileData.answers || [],
        total_answers: totalAnswers,
        embedding_status: {
          has_embedding: profileData.embedding_status?.has_embedding || false,
          embedding_dimension: profileData.embedding_status?.embedding_dimension,
          created_at: profileData.embedding_status?.created_at,
          message: profileData.embedding_status?.has_embedding 
            ? 'Profile ready for matching'
            : 'Complete more questions to enable matching'
        },
        profile_completion: {
          total_questions: this.TOTAL_QUESTIONS,
          answered_questions: totalAnswers,
          completion_percentage: completionPercentage,
          can_start_matching: canStartMatching
        }
      };

      console.log(`✅ Profile loaded: ${totalAnswers}/${this.TOTAL_QUESTIONS} questions (${completionPercentage.toFixed(1)}%)`);
      
      return profile;

    } catch (error) {
      console.error('❌ Failed to get user profile:', error);
      return null;
    }
  }

  /**
   * Delete user answer
   */
  async deleteAnswer(userId: string, questionId: string): Promise<{
    success: boolean;
    message: string;
  }> {
    try {
      console.log(`🗑️ Deleting answer for question ${questionId}`);

      const { error } = await supabase
        .from('user_answers')
        .delete()
        .eq('user_id', userId)
        .eq('question_id', questionId);

      if (error) {
        console.error('❌ Error deleting answer:', error);
        throw new Error(`Failed to delete answer: ${error.message}`);
      }

      console.log('✅ Answer deleted successfully');
      
      return {
        success: true,
        message: 'Answer deleted successfully'
      };

    } catch (error) {
      console.error('❌ Failed to delete answer:', error);
      return {
        success: false,
        message: error instanceof Error ? error.message : 'Failed to delete answer'
      };
    }
  }

  /**
   * Check if user has embedding for AI matching
   */
  async checkEmbeddingStatus(userId: string): Promise<{
    has_embedding: boolean;
    embedding_dimension?: number;
    message: string;
  }> {
    try {
      console.log(`🔍 Checking embedding status for user: ${userId}`);

      const { data, error } = await supabase
        .from('user_embeddings')
        .select('user_id, created_at')
        .eq('user_id', userId)
        .single();

      if (error && error.code !== 'PGRST116') { // PGRST116 = no rows returned
        console.error('❌ Error checking embedding status:', error);
        throw new Error(`Failed to check embedding status: ${error.message}`);
      }

      const hasEmbedding = !!data;

      console.log(`📊 Embedding status: ${hasEmbedding ? 'EXISTS' : 'MISSING'}`);

      return {
        has_embedding: hasEmbedding,
        embedding_dimension: hasEmbedding ? 1024 : undefined,
        message: hasEmbedding 
          ? 'Profile ready for AI matching'
          : 'Complete questionnaire to enable AI matching'
      };

    } catch (error) {
      console.error('❌ Failed to check embedding status:', error);
      return {
        has_embedding: false,
        message: 'Unable to check profile status'
      };
    }
  }

  /**
   * Get user's question progress
   */
  async getUserProgress(userId: string): Promise<{
    answered: number;
    total: number;
    percentage: number;
  }> {
    try {
      const { count, error } = await supabase
        .from('user_answers')
        .select('id', { count: 'exact', head: true })
        .eq('user_id', userId);

      if (error) {
        console.error('❌ Error getting user progress:', error);
        throw new Error(`Failed to get progress: ${error.message}`);
      }

      const answered = count || 0;
      const percentage = (answered / this.TOTAL_QUESTIONS) * 100;

      return {
        answered,
        total: this.TOTAL_QUESTIONS,
        percentage
      };

    } catch (error) {
      console.error('❌ Failed to get user progress:', error);
      return {
        answered: 0,
        total: this.TOTAL_QUESTIONS,
        percentage: 0
      };
    }
  }

  /**
   * Transform database question data to frontend format
   */
  private transformDatabaseQuestions(dbQuestions: any[]): Question[] {
    return dbQuestions.map(q => {
      // Parse options from JSONB
      let options: string[] | undefined;
      if (q.options && Array.isArray(q.options)) {
        options = q.options.map((option: any) => option.text_ko || option.value);
      }

      return {
        id: q.id || q.question_id,
        text: q.text_ko || q.question_text, // Use Korean text by default
        category: q.category,
        type: this.mapAnswerType(q.answer_type),
        options,
        effectiveness_score: q.effectiveness_score,
        placeholder: q.placeholder,
        maxLength: q.max_length,
        can_be_dealbreaker: q.can_be_dealbreaker,
        base_weight: q.base_weight
      };
    });
  }

  /**
   * Map database answer types to frontend types
   */
  private mapAnswerType(dbType: string): 'choice' | 'text' | 'scale' {
    switch (dbType) {
      case 'choice':
        return 'choice';
      case 'text':
        return 'text';
      case 'scale':
        return 'scale';
      default:
        return 'choice';
    }
  }

  /**
   * Test Supabase connection and database access
   */
  async testConnection(): Promise<{
    connected: boolean;
    database: boolean;
    questions_available: boolean;
    error?: string;
  }> {
    try {
      console.log('🔍 Testing Supabase connection...');

      // Test basic connection
      const { data: healthData, error: healthError } = await supabase
        .from('questions')
        .select('count')
        .limit(1);

      if (healthError) {
        return {
          connected: false,
          database: false,
          questions_available: false,
          error: healthError.message
        };
      }

      // Test questions availability
      const { count, error: countError } = await supabase
        .from('questions')
        .select('id', { count: 'exact', head: true })
        .eq('is_active', true);

      if (countError) {
        return {
          connected: true,
          database: true,
          questions_available: false,
          error: countError.message
        };
      }

      const questionsAvailable = (count || 0) > 0;

      console.log(`✅ Connection test passed: ${count} questions available`);

      return {
        connected: true,
        database: true,
        questions_available: questionsAvailable
      };

    } catch (error) {
      console.error('❌ Connection test failed:', error);
      return {
        connected: false,
        database: false,
        questions_available: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }
}

// Export singleton instance
export const supabaseQuestionService = new SupabaseQuestionService();