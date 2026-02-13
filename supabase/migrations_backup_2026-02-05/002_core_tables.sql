-- ==========================================
-- FLIO Core Tables
-- ==========================================
-- Description: Core application tables (profiles, matches, messages, meeting_feedback)
-- Consolidated from: 001_core_schema.sql (lines 13-157)
-- ==========================================

-- ==========================================
-- PROFILES TABLE
-- ==========================================

CREATE TABLE public.profiles (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Basic info
    nickname VARCHAR(50) NOT NULL,
    birth_date DATE NOT NULL,
    gender VARCHAR(10) NOT NULL CHECK (gender IN ('male', 'female', 'other')),
    bio TEXT,

    -- Photos (Supabase Storage URLs)
    photos TEXT[] DEFAULT '{}',

    -- Embeddings for AI matching (1024D from start)
    profile_embedding vector(1024),  -- Azure OpenAI text-embedding-3-large
    face_embedding vector(512),      -- InsightFace/ArcFace embedding

    -- Verification status
    face_verified BOOLEAN DEFAULT FALSE,
    face_verified_at TIMESTAMP WITH TIME ZONE,
    face_similarity_score FLOAT,
    photo_verified BOOLEAN DEFAULT FALSE,
    photo_verified_at TIMESTAMPTZ,
    education_verified BOOLEAN DEFAULT FALSE,
    job_verified BOOLEAN DEFAULT FALSE,

    -- Identity fields
    real_name VARCHAR(50),
    real_name_verified BOOLEAN DEFAULT FALSE,
    height_cm INTEGER,
    weight_kg INTEGER,

    -- Education fields
    education_level VARCHAR(50),
    university_name VARCHAR(100),
    major VARCHAR(100),
    graduation_year INTEGER,

    -- Career & Income fields
    employment_status VARCHAR(50),
    company_name VARCHAR(100),
    job_title VARCHAR(100),
    industry VARCHAR(100),
    annual_income_range VARCHAR(50),

    -- Marital History
    marital_status VARCHAR(20) DEFAULT '미혼',
    divorce_reason TEXT,
    has_children BOOLEAN DEFAULT false,
    children_count INTEGER DEFAULT 0,

    -- Trust & Tier System
    trust_tier VARCHAR(20),
    tier_preferences TEXT[],
    paid_tier VARCHAR(20) DEFAULT 'pebble',
    paid_tier_expires_at TIMESTAMPTZ,
    daily_match_limit INTEGER DEFAULT 5,

    -- Subscription
    subscription_status VARCHAR(20) DEFAULT 'none',
    subscription_started_at TIMESTAMPTZ,
    subscription_renewed_at TIMESTAMPTZ,

    -- Settings
    is_active BOOLEAN DEFAULT TRUE,
    last_active_at TIMESTAMP WITH TIME ZONE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ==========================================
-- MATCHES TABLE
-- ==========================================

CREATE TABLE public.matches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_a_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    user_b_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Match score and explanation
    score FLOAT NOT NULL,
    explanation TEXT,

    -- Like status
    user_a_liked BOOLEAN,
    user_b_liked BOOLEAN,

    -- Match timestamp (when both liked)
    matched_at TIMESTAMP WITH TIME ZONE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Ensure unique pairs
    CONSTRAINT unique_match_pair UNIQUE (user_a_id, user_b_id),
    CONSTRAINT different_users CHECK (user_a_id != user_b_id)
);

-- ==========================================
-- MESSAGES TABLE
-- ==========================================

CREATE TABLE public.messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id UUID NOT NULL REFERENCES public.matches(id) ON DELETE CASCADE,
    sender_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Encrypted message content
    content TEXT NOT NULL,
    encrypted BOOLEAN DEFAULT TRUE,

    -- Read status
    read_at TIMESTAMP WITH TIME ZONE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ==========================================
-- MEETING FEEDBACK TABLE
-- ==========================================

CREATE TABLE public.meeting_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    reviewer_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    reviewed_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    meeting_date DATE NOT NULL,

    -- Feedback fields (focus on face authenticity)
    face_matched_profile BOOLEAN,
    overall_authentic BOOLEAN,
    would_recommend BOOLEAN,

    notes TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- One feedback per meeting
    CONSTRAINT unique_feedback UNIQUE (reviewer_id, reviewed_id, meeting_date)
);

-- ==========================================
-- TRIGGERS
-- ==========================================

CREATE TRIGGER profiles_updated_at
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- ==========================================
-- COMMENTS
-- ==========================================

COMMENT ON TABLE public.profiles IS 'User profiles with 1024D embeddings for matching';
COMMENT ON COLUMN public.profiles.profile_embedding IS 'Azure OpenAI text-embedding-3-large 1024D embedding for profile matching';
COMMENT ON COLUMN public.profiles.trust_tier IS 'Eligibility tier based on trust score: pebble(0-19%), shell(20-39%), pearl(40-59%), coral(60-79%), diamond(80-100%)';
COMMENT ON COLUMN public.profiles.paid_tier IS 'Paid subscription tier (what user actually purchased)';
COMMENT ON COLUMN public.profiles.tier_preferences IS 'Ocean Pearl Theme tiers user wants to match with';
COMMENT ON COLUMN public.profiles.daily_match_limit IS 'Daily match limit based on paid tier';
