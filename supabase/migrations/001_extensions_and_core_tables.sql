-- ==========================================
-- FLIO Database Schema - Core Tables
-- ==========================================
-- Version: 2.0
-- Date: 2026-02-05
-- Description: PostgreSQL extensions, utility functions, and core tables
-- ==========================================

-- ==========================================
-- EXTENSIONS
-- ==========================================

CREATE EXTENSION IF NOT EXISTS vector;

COMMENT ON EXTENSION vector IS 'pgvector extension for similarity search (1024D embeddings)';

-- ==========================================
-- UTILITY FUNCTIONS
-- ==========================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION update_updated_at IS 'Trigger function to automatically update updated_at timestamps';

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
    face_verified_at TIMESTAMPTZ,
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
    has_children BOOLEAN DEFAULT FALSE,
    children_count INTEGER DEFAULT 0,

    -- Trust & Tier System
    trust_tier VARCHAR(20) CHECK (trust_tier IN ('diamond', 'coral', 'pearl', 'shell', 'pebble') OR trust_tier IS NULL),
    tier_preferences TEXT[],
    paid_tier VARCHAR(20) DEFAULT 'pebble' CHECK (paid_tier IN ('diamond', 'coral', 'pearl', 'shell', 'pebble')),
    paid_tier_expires_at TIMESTAMPTZ,
    daily_match_limit INTEGER DEFAULT 5,

    -- Subscription
    subscription_status VARCHAR(20) DEFAULT 'none' CHECK (subscription_status IN ('none', 'active', 'expired', 'cancelled', 'suspended')),
    subscription_started_at TIMESTAMPTZ,
    subscription_renewed_at TIMESTAMPTZ,

    -- Settings
    is_active BOOLEAN DEFAULT TRUE,
    last_active_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Profile indexes
CREATE INDEX idx_profiles_gender ON public.profiles(gender);
CREATE INDEX idx_profiles_is_active ON public.profiles(is_active);
CREATE INDEX idx_profiles_trust_tier ON public.profiles(trust_tier);
CREATE INDEX idx_profiles_paid_tier ON public.profiles(paid_tier);
CREATE INDEX idx_profiles_subscription_status ON public.profiles(subscription_status);
CREATE INDEX idx_profiles_tier_preferences ON public.profiles USING GIN(tier_preferences);
CREATE INDEX idx_profiles_photos ON public.profiles USING GIN(photos);
CREATE INDEX idx_profiles_has_embedding ON public.profiles(user_id) WHERE profile_embedding IS NOT NULL;

-- Vector indexes for similarity search
CREATE INDEX idx_profiles_profile_embedding
ON public.profiles
USING ivfflat (profile_embedding vector_cosine_ops)
WITH (lists = 100);

CREATE INDEX idx_profiles_face_embedding
ON public.profiles
USING ivfflat (face_embedding vector_cosine_ops)
WITH (lists = 100);

-- Triggers
CREATE TRIGGER profiles_updated_at
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Comments
COMMENT ON TABLE public.profiles IS 'User profiles with 1024D embeddings for AI matching';
COMMENT ON COLUMN public.profiles.profile_embedding IS 'Azure OpenAI text-embedding-3-large 1024D for profile matching';
COMMENT ON COLUMN public.profiles.face_embedding IS 'InsightFace/ArcFace 512D for face verification';
COMMENT ON COLUMN public.profiles.trust_tier IS 'Eligibility tier: diamond(80%+), coral(60-79%), pearl(40-59%), shell(20-39%), pebble(0-19%)';
COMMENT ON COLUMN public.profiles.paid_tier IS 'Paid subscription tier (what user purchased)';
COMMENT ON COLUMN public.profiles.tier_preferences IS 'Tiers user wants to match with';
COMMENT ON COLUMN public.profiles.daily_match_limit IS 'Daily match limit based on paid tier';

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
    user_a_liked BOOLEAN DEFAULT FALSE,
    user_b_liked BOOLEAN DEFAULT FALSE,

    -- Match timestamp (when both liked)
    matched_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT unique_match_pair UNIQUE (user_a_id, user_b_id),
    CONSTRAINT different_users CHECK (user_a_id != user_b_id)
);

-- Indexes
CREATE INDEX idx_matches_user_a ON public.matches(user_a_id);
CREATE INDEX idx_matches_user_b ON public.matches(user_b_id);
CREATE INDEX idx_matches_matched_at ON public.matches(matched_at);

COMMENT ON TABLE public.matches IS 'Match pairs with compatibility scores';

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
    read_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_messages_match_id ON public.messages(match_id);
CREATE INDEX idx_messages_sender_id ON public.messages(sender_id);
CREATE INDEX idx_messages_created_at ON public.messages(created_at);

COMMENT ON TABLE public.messages IS 'End-to-end encrypted messages between matched users';

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

    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- One feedback per meeting
    CONSTRAINT unique_feedback UNIQUE (reviewer_id, reviewed_id, meeting_date)
);

-- Indexes
CREATE INDEX idx_meeting_feedback_reviewer_id ON public.meeting_feedback(reviewer_id);
CREATE INDEX idx_meeting_feedback_reviewed_id ON public.meeting_feedback(reviewed_id);

COMMENT ON TABLE public.meeting_feedback IS 'Post-meeting feedback for trust score calculation';

-- ==========================================
-- ROW LEVEL SECURITY
-- ==========================================

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.matches ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.meeting_feedback ENABLE ROW LEVEL SECURITY;

-- Profiles policies
CREATE POLICY "Profiles are viewable by authenticated users"
ON public.profiles FOR SELECT
TO authenticated
USING (is_active = TRUE);

CREATE POLICY "Users can update own profile"
ON public.profiles FOR UPDATE
TO authenticated
USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own profile"
ON public.profiles FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = user_id);

-- Matches policies
CREATE POLICY "Users can view own matches"
ON public.matches FOR SELECT
TO authenticated
USING (auth.uid() IN (user_a_id, user_b_id));

-- Messages policies
CREATE POLICY "Users can view messages in their matches"
ON public.messages FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM public.matches
        WHERE matches.id = messages.match_id
        AND auth.uid() IN (matches.user_a_id, matches.user_b_id)
    )
);

CREATE POLICY "Users can send messages in their matches"
ON public.messages FOR INSERT
TO authenticated
WITH CHECK (
    auth.uid() = sender_id
    AND EXISTS (
        SELECT 1 FROM public.matches
        WHERE matches.id = match_id
        AND matches.matched_at IS NOT NULL
        AND auth.uid() IN (matches.user_a_id, matches.user_b_id)
    )
);

-- Meeting feedback policies
CREATE POLICY "Users can view feedback they gave or received"
ON public.meeting_feedback FOR SELECT
TO authenticated
USING (auth.uid() IN (reviewer_id, reviewed_id));

CREATE POLICY "Users can insert own feedback"
ON public.meeting_feedback FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = reviewer_id);

-- ==========================================
-- SCHEMA DOCUMENTATION
-- ==========================================

COMMENT ON SCHEMA public IS 'FLIO Dating App - Core Schema v2.0
Created: 2026-02-05
Features:
- 1024D embeddings for AI matching
- 5-tier trust score system (Ocean Pearl Theme)
- End-to-end encrypted messaging
- Comprehensive verification system
- Hybrid subscription model (trust-based eligibility + payment)
';
