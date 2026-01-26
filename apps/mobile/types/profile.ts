/**
 * FLIO Profile Types
 *
 * Complete profile schema matching database migrations
 */

import { TrustTier } from './trust';

export interface Profile {
  user_id: string;

  // Basic info
  nickname: string;
  birth_date: string;
  gender: 'male' | 'female' | 'other';
  bio?: string;
  photos: string[];

  // Embeddings for AI matching
  profile_embedding?: number[]; // 1024D Azure OpenAI
  face_embedding?: number[];    // 512D InsightFace/ArcFace

  // Verification status
  face_verified: boolean;
  face_verified_at?: string;
  face_similarity_score?: number;
  photo_verified: boolean;
  photo_verified_at?: string;
  education_verified: boolean;
  job_verified: boolean;

  // Identity fields
  real_name?: string;
  real_name_verified: boolean;
  height_cm?: number;
  weight_kg?: number;

  // Education fields
  education_level?: string;
  university_name?: string;
  major?: string;
  graduation_year?: number;

  // Career & Income fields
  employment_status?: string;
  company_name?: string;
  job_title?: string;
  industry?: string;
  annual_income_range?: string;

  // Marital History
  marital_status: string; // Default: '미혼'
  divorce_reason?: string;
  has_children: boolean;
  children_count: number;

  // Trust & Tier System
  trust_tier?: TrustTier;
  tier_preferences?: TrustTier[];
  paid_tier: TrustTier; // Default: 'pebble'
  paid_tier_expires_at?: string;
  daily_match_limit: number; // Default: 5

  // Subscription
  subscription_status: 'none' | 'active' | 'expired' | 'cancelled' | 'trial';
  subscription_started_at?: string;
  subscription_renewed_at?: string;

  // Settings
  is_active: boolean;
  last_active_at?: string;

  // Timestamps
  created_at: string;
  updated_at: string;
}

export interface FamilyBackground {
  id: string;
  user_id: string;

  // Parents
  parents_status: string;
  father_name?: string;
  father_age?: number;
  father_occupation?: string;
  mother_name?: string;
  mother_age?: number;
  mother_occupation?: string;

  // Siblings
  number_of_siblings?: number;
  birth_order?: number;

  // Additional info
  family_religion?: string;
  hometown?: string;
  father_education?: string;
  mother_education?: string;

  created_at: string;
  updated_at: string;
}

export interface ProfileCompleteness {
  total_fields: number;
  filled_fields: number;
  completion_percentage: number;
  missing_critical_fields: string[];
  missing_optional_fields: string[];
}

export interface ProfileUpdate {
  nickname?: string;
  bio?: string;
  photos?: string[];
  height_cm?: number;
  weight_kg?: number;
  education_level?: string;
  university_name?: string;
  major?: string;
  graduation_year?: number;
  employment_status?: string;
  company_name?: string;
  job_title?: string;
  industry?: string;
  annual_income_range?: string;
  marital_status?: string;
  has_children?: boolean;
  children_count?: number;
}

export interface ProfileSummary {
  user_id: string;
  nickname: string;
  age: number;
  gender: string;
  bio?: string;
  photos: string[];
  trust_tier?: TrustTier;
  trust_tier_korean?: string;
  photo_verified: boolean;
  has_embedding: boolean;
}
