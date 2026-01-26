/**
 * FLIO Trust Score Types
 *
 * Type definitions for the 5-tier trust score system
 * Matches backend and database schema
 */

// ==========================================
// TRUST TIERS (Ocean Pearl Theme)
// ==========================================

export type TrustTier = 'diamond' | 'coral' | 'pearl' | 'shell' | 'pebble';

export interface TierInfo {
  tier: TrustTier;
  tier_korean: string;
  min_score: number;
  daily_matches: number;
  monthly_price_krw: number;
  can_see_tiers: TrustTier[];
  badge: string;
  priority_matching: boolean;
}

export const TIER_INFO: Record<TrustTier, TierInfo> = {
  diamond: {
    tier: 'diamond',
    tier_korean: '다이아',
    min_score: 0.80,
    daily_matches: 30,
    monthly_price_krw: 59900,
    can_see_tiers: ['diamond', 'coral', 'pearl', 'shell', 'pebble'],
    badge: '💎',
    priority_matching: true,
  },
  coral: {
    tier: 'coral',
    tier_korean: '산호',
    min_score: 0.60,
    daily_matches: 20,
    monthly_price_krw: 39900,
    can_see_tiers: ['coral', 'pearl', 'shell', 'pebble'],
    badge: '🪸',
    priority_matching: true,
  },
  pearl: {
    tier: 'pearl',
    tier_korean: '진주',
    min_score: 0.40,
    daily_matches: 15,
    monthly_price_krw: 19900,
    can_see_tiers: ['pearl', 'shell', 'pebble'],
    badge: '🦪',
    priority_matching: false,
  },
  shell: {
    tier: 'shell',
    tier_korean: '조개',
    min_score: 0.20,
    daily_matches: 10,
    monthly_price_krw: 9900,
    can_see_tiers: ['shell', 'pebble'],
    badge: '🐚',
    priority_matching: false,
  },
  pebble: {
    tier: 'pebble',
    tier_korean: '조약돌',
    min_score: 0.00,
    daily_matches: 5,
    monthly_price_krw: 0,
    can_see_tiers: ['pebble'],
    badge: '🪨',
    priority_matching: false,
  },
};

// ==========================================
// TRUST SCORE COMPONENTS (7 Total)
// ==========================================

export interface TrustScoreComponents {
  document: number;        // 25% - ID, diploma, income, employment verification
  photo: number;           // 20% - REQUIRED - Photo verification
  consistency: number;     // 15% - Answer consistency (NLI checks)
  behavioral: number;      // 15% - Account age + engagement
  social: number;          // 10% - LinkedIn, Instagram, Kakao, Naver
  completeness: number;    // 10% - Profile completion
  reputation: number;      // 5%  - Reports, ghosting, positive outcomes
}

export const SCORE_WEIGHTS: TrustScoreComponents = {
  document: 0.25,
  photo: 0.20,
  consistency: 0.15,
  behavioral: 0.15,
  social: 0.10,
  completeness: 0.10,
  reputation: 0.05,
};

// ==========================================
// TRUST SCORE API RESPONSES
// ==========================================

export interface TrustScoreDetail {
  user_id: string;
  total_trust_score: number;
  trust_tier: TrustTier;
  component_scores: TrustScoreComponents;
  tier_benefits: TierInfo;
  calculation_details: Record<string, any>;
  last_calculated_at: string;
}

export interface TrustSummary {
  trust_score: number;
  trust_tier: TrustTier;
  trust_tier_korean: string;
  verified_items: string[];
  profile_completeness: number;
  is_matching_enabled: boolean;
  daily_match_limit: number;
}

export interface ComponentBreakdown {
  score: number;
  weight: number;
  contribution: number;
}

export interface UpgradePath {
  user_id: string;
  current_tier: TrustTier;
  current_tier_korean: string;
  current_score: number;
  next_tier: TrustTier | null;
  next_tier_korean: string | null;
  next_threshold: number | null;
  score_gap: number;
  recommendations: string[];
  component_breakdown: Record<keyof TrustScoreComponents, ComponentBreakdown>;
  is_max_tier: boolean;
}

// ==========================================
// VERIFICATION STATUS
// ==========================================

export interface VerificationStatus {
  photo_verified: boolean;
  photo_verified_at?: string;
  id_verified: boolean;
  education_verified: boolean;
  income_verified: boolean;
  employment_verified: boolean;
  phone_verified: boolean;
  social_verifications: SocialVerification[];
}

export interface SocialVerification {
  platform: 'linkedin' | 'instagram' | 'kakao' | 'naver';
  is_verified: boolean;
  verified_at?: string;
  account_age_days?: number;
  follower_count?: number;
  is_verified_account?: boolean;
}

export interface PhotoVerification {
  id: string;
  user_id: string;
  challenge_pose: string;
  verification_status: 'pending' | 'verified' | 'flagged' | 'rejected';
  verification_score?: number;
  verified_at?: string;
  expires_at?: string;
}

export interface DocumentVerification {
  id: string;
  user_id: string;
  document_type: 'id_card' | 'diploma' | 'income_cert' | 'employment_cert';
  verification_status: 'pending' | 'verified' | 'flagged' | 'rejected';
  match_score?: number;
  verified_at?: string;
}

// ==========================================
// SUBSCRIPTION & PAYMENT
// ==========================================

export interface SubscriptionStatus {
  paid_tier: TrustTier;
  subscription_status: 'none' | 'active' | 'expired' | 'cancelled' | 'trial';
  subscription_started_at?: string;
  subscription_renewed_at?: string;
  paid_tier_expires_at?: string;
}

export interface SubscriptionPlan {
  tier_name: TrustTier;
  tier_name_korean: string;
  monthly_price_krw: number;
  daily_matches: number;
  features: string[];
  min_trust_score: number;
}

// ==========================================
// USER REPORTS & REPUTATION
// ==========================================

export interface UserReport {
  id: string;
  reporter_user_id: string;
  reported_user_id: string;
  report_type: 'harassment' | 'scam' | 'fake_profile' | 'ghosting';
  status: 'pending' | 'investigating' | 'confirmed' | 'dismissed';
  severity_level: number; // 1-5
  created_at: string;
}

export interface ConversationAnalytics {
  conversation_id: string;
  user_id: string;
  total_messages: number;
  avg_response_time_hours?: number;
  end_reason?: 'mutual' | 'ghosting' | 'met_in_person' | 'started_relationship';
  ghosting_pattern: boolean;
  positive_outcome: boolean;
  created_at: string;
}

// ==========================================
// HELPER FUNCTIONS
// ==========================================

export function getTierInfo(tier: TrustTier): TierInfo {
  return TIER_INFO[tier];
}

export function getTierFromScore(score: number): TrustTier {
  if (score >= 0.80) return 'diamond';
  if (score >= 0.60) return 'coral';
  if (score >= 0.40) return 'pearl';
  if (score >= 0.20) return 'shell';
  return 'pebble';
}

export function formatTierKorean(tier: TrustTier): string {
  return TIER_INFO[tier].tier_korean;
}

export function formatPrice(priceKrw: number): string {
  if (priceKrw === 0) return '무료';
  return `₩${priceKrw.toLocaleString()}`;
}

export function canAccessMatches(photoVerified: boolean): boolean {
  return photoVerified;
}

export function canMatchWithTier(userTier: TrustTier, targetTier: TrustTier): boolean {
  return TIER_INFO[userTier].can_see_tiers.includes(targetTier);
}
