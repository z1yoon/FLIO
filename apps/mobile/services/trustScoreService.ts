/**
 * Trust Score Service
 *
 * Frontend service for interacting with trust score backend APIs
 */

import { supabase } from './supabase/client';
import {
  TrustScoreDetail,
  TrustSummary,
  UpgradePath,
  TrustTier,
  VerificationStatus,
  getTierInfo,
  getTierFromScore,
} from '../types/trust';

const AI_BACKEND_URL = process.env.EXPO_PUBLIC_AI_BACKEND_URL || 'http://localhost:8000';

export class TrustScoreService {
  /**
   * Get detailed trust score breakdown
   */
  async getTrustScore(userId: string): Promise<TrustScoreDetail | null> {
    try {
      const response = await fetch(`${AI_BACKEND_URL}/api/v1/trust/score/${userId}`);

      if (!response.ok) {
        if (response.status === 404) {
          return null;
        }
        throw new Error(`Failed to get trust score: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching trust score:', error);
      throw error;
    }
  }

  /**
   * Get simplified trust summary
   */
  async getTrustSummary(userId: string): Promise<TrustSummary> {
    try {
      const response = await fetch(`${AI_BACKEND_URL}/api/v1/trust/summary/${userId}`);

      if (!response.ok) {
        throw new Error(`Failed to get trust summary: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching trust summary:', error);
      throw error;
    }
  }

  /**
   * Force recalculation of trust score
   */
  async recalculateTrustScore(userId: string): Promise<{
    success: boolean;
    message: string;
    previous_score?: number;
    new_score: number;
    previous_tier?: TrustTier;
    new_tier: TrustTier;
  }> {
    try {
      const response = await fetch(`${AI_BACKEND_URL}/api/v1/trust/recalculate/${userId}`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error(`Failed to recalculate trust score: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error recalculating trust score:', error);
      throw error;
    }
  }

  /**
   * Get upgrade path recommendations
   */
  async getUpgradePath(userId: string): Promise<UpgradePath> {
    try {
      const response = await fetch(`${AI_BACKEND_URL}/api/v1/trust/upgrade-path/${userId}`);

      if (!response.ok) {
        throw new Error(`Failed to get upgrade path: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching upgrade path:', error);
      throw error;
    }
  }

  /**
   * Get verification status from Supabase
   */
  async getVerificationStatus(userId: string): Promise<VerificationStatus> {
    try {
      // Get photo verification
      const { data: photoVerif, error: photoError } = await supabase
        .from('photo_verifications')
        .select('*')
        .eq('user_id', userId)
        .eq('verification_status', 'verified')
        .order('verified_at', { ascending: false })
        .limit(1)
        .single();

      // Get document verifications
      const { data: docs, error: docsError } = await supabase
        .from('user_documents')
        .select('document_type, verification_status')
        .eq('user_id', userId)
        .eq('verification_status', 'verified');

      // Get social verifications
      const { data: socials, error: socialsError } = await supabase
        .from('social_verifications')
        .select('platform, is_verified, verified_at, account_age_days, follower_count, is_verified_account')
        .eq('user_id', userId);

      // Get phone verification
      const { data: phone, error: phoneError } = await supabase
        .from('phone_verifications')
        .select('is_verified, verified_at')
        .eq('user_id', userId)
        .order('created_at', { ascending: false })
        .limit(1)
        .single();

      const docTypes = docs?.map((d) => d.document_type) || [];

      return {
        photo_verified: !!photoVerif && !photoError,
        photo_verified_at: photoVerif?.verified_at,
        id_verified: docTypes.includes('id_card'),
        education_verified: docTypes.includes('diploma'),
        income_verified: docTypes.includes('income_cert'),
        employment_verified: docTypes.includes('employment_cert'),
        phone_verified: phone?.is_verified || false,
        social_verifications: socials || [],
      };
    } catch (error) {
      console.error('Error fetching verification status:', error);
      throw error;
    }
  }

  /**
   * Check if user can access matches (photo verification required)
   */
  async canAccessMatches(userId: string): Promise<boolean> {
    try {
      const { data, error } = await supabase
        .rpc('can_user_access_matches', { p_user_id: userId });

      if (error) throw error;
      return data || false;
    } catch (error) {
      console.error('Error checking match access:', error);
      return false;
    }
  }

  /**
   * Get daily match limit info
   */
  async getDailyMatchLimit(userId: string): Promise<{
    daily_limit: number;
    daily_count: number;
    remaining: number;
    can_view: boolean;
    trust_tier: TrustTier;
  }> {
    try {
      const { data, error } = await supabase
        .rpc('can_view_more_matches', { p_user_id: userId });

      if (error) throw error;
      return data;
    } catch (error) {
      console.error('Error checking daily match limit:', error);
      throw error;
    }
  }

  /**
   * Log user behavior for trust scoring
   */
  async logBehavior(
    userId: string,
    eventType: string,
    eventData?: Record<string, any>,
    fieldChanged?: string,
    oldValue?: string,
    newValue?: string
  ): Promise<void> {
    try {
      const response = await fetch(`${AI_BACKEND_URL}/api/v1/trust/behavior/log`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId,
          event_type: eventType,
          event_data: eventData,
          field_changed: fieldChanged,
          old_value: oldValue,
          new_value: newValue,
        }),
      });

      if (!response.ok) {
        console.warn('Failed to log behavior:', response.statusText);
      }
    } catch (error) {
      // Silent fail - behavior logging shouldn't block user actions
      console.warn('Error logging behavior:', error);
    }
  }

  /**
   * Get all tier info
   */
  async getAllTierInfo() {
    try {
      const response = await fetch(`${AI_BACKEND_URL}/api/v1/trust/tiers/info`);

      if (!response.ok) {
        throw new Error(`Failed to get tier info: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching tier info:', error);
      throw error;
    }
  }
}

// Singleton instance
export const trustScoreService = new TrustScoreService();
