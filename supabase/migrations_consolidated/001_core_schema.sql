-- ==========================================
-- FLIO Core Database Schema
-- ==========================================
-- Consolidates: 001_initial_schema + 002_upgrade_embeddings + 004_ai_backend_functions
--               + 006_daily_match_tracking + 011_add_daily_match_limit
-- Core tables with correct dimensions from the start + AI utility functions + Match tracking
-- ==========================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;

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
-- INDEXES
-- ==========================================

-- Profile embeddings for similarity search
CREATE INDEX idx_profiles_profile_embedding
ON public.profiles
USING ivfflat (profile_embedding vector_cosine_ops)
WITH (lists = 100);

CREATE INDEX idx_profiles_face_embedding
ON public.profiles
USING ivfflat (face_embedding vector_cosine_ops)
WITH (lists = 100);

-- Profile indexes
CREATE INDEX idx_profiles_user_id ON public.profiles(user_id);
CREATE INDEX idx_profiles_gender ON public.profiles(gender);
CREATE INDEX idx_profiles_is_active ON public.profiles(is_active);
CREATE INDEX idx_profiles_trust_tier ON public.profiles(trust_tier);
CREATE INDEX idx_profiles_paid_tier ON public.profiles(paid_tier);
CREATE INDEX idx_profiles_subscription_status ON public.profiles(subscription_status);
CREATE INDEX idx_profiles_tier_preferences ON public.profiles USING GIN(tier_preferences);
CREATE INDEX idx_profiles_has_embedding ON public.profiles(user_id) WHERE profile_embedding IS NOT NULL;

-- Match indexes
CREATE INDEX idx_matches_user_a ON public.matches(user_a_id);
CREATE INDEX idx_matches_user_b ON public.matches(user_b_id);
CREATE INDEX idx_matches_matched_at ON public.matches(matched_at);

-- Message indexes
CREATE INDEX idx_messages_match_id ON public.messages(match_id);
CREATE INDEX idx_messages_created_at ON public.messages(created_at);

-- ==========================================
-- ROW LEVEL SECURITY
-- ==========================================

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.matches ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.meeting_feedback ENABLE ROW LEVEL SECURITY;

-- Profiles: Users can read others' profiles, but only edit their own
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

-- Matches: Users can see matches they're part of
CREATE POLICY "Users can view own matches"
ON public.matches FOR SELECT
TO authenticated
USING (auth.uid() IN (user_a_id, user_b_id));

-- Messages: Users can see messages in their matches
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

-- ==========================================
-- TRIGGERS
-- ==========================================

-- Update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

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

-- ==========================================
-- AI BACKEND FUNCTIONS
-- ==========================================
-- Includes: 004_ai_backend_functions
-- Essential AI matching and profile functions
-- ==========================================

-- Find Similar Profiles (1024D Embeddings)
DROP FUNCTION IF EXISTS find_similar_profiles(vector, UUID, INTEGER, VARCHAR, INTEGER, INTEGER);

CREATE FUNCTION find_similar_profiles(
    query_embedding vector(1024),
    exclude_user_id UUID,
    match_limit INTEGER DEFAULT 20,
    gender_filter VARCHAR(10) DEFAULT NULL,
    min_age INTEGER DEFAULT NULL,
    max_age INTEGER DEFAULT NULL
)
RETURNS TABLE (
    user_id UUID,
    similarity FLOAT,
    nickname VARCHAR(50),
    birth_date DATE,
    gender VARCHAR(10),
    photos TEXT[]
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.user_id,
        (1 - (p.profile_embedding <=> query_embedding))::FLOAT AS similarity,
        p.nickname,
        p.birth_date,
        p.gender,
        p.photos
    FROM public.profiles p
    WHERE p.user_id != exclude_user_id
        AND p.is_active = TRUE
        AND p.profile_embedding IS NOT NULL
        AND (gender_filter IS NULL OR p.gender = gender_filter)
        AND (min_age IS NULL OR DATE_PART('year', AGE(p.birth_date)) >= min_age)
        AND (max_age IS NULL OR DATE_PART('year', AGE(p.birth_date)) <= max_age)
    ORDER BY p.profile_embedding <=> query_embedding
    LIMIT match_limit;
END;
$$ LANGUAGE plpgsql;

-- Store Profile Embedding
DROP FUNCTION IF EXISTS store_profile_embedding(UUID, vector, TEXT);

CREATE FUNCTION store_profile_embedding(
    p_user_id UUID,
    p_embedding vector(1024),
    p_profile_text TEXT DEFAULT NULL
)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE public.profiles
    SET
        profile_embedding = p_embedding,
        updated_at = NOW()
    WHERE user_id = p_user_id;

    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- Get User Profile Summary
DROP FUNCTION IF EXISTS get_user_profile_summary(UUID);

CREATE FUNCTION get_user_profile_summary(p_user_id UUID)
RETURNS TABLE (
    user_id UUID,
    nickname VARCHAR,
    age INTEGER,
    gender VARCHAR,
    bio TEXT,
    photos TEXT[],
    has_embedding BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.user_id,
        p.nickname,
        DATE_PART('year', AGE(p.birth_date))::INTEGER as age,
        p.gender,
        p.bio,
        p.photos,
        (p.profile_embedding IS NOT NULL) as has_embedding
    FROM public.profiles p
    WHERE p.user_id = p_user_id;
END;
$$ LANGUAGE plpgsql;

-- Grant Permissions
GRANT EXECUTE ON FUNCTION find_similar_profiles(vector, UUID, INTEGER, VARCHAR, INTEGER, INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION store_profile_embedding(UUID, vector, TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION get_user_profile_summary(UUID) TO authenticated;

GRANT EXECUTE ON FUNCTION find_similar_profiles(vector, UUID, INTEGER, VARCHAR, INTEGER, INTEGER) TO service_role;
GRANT EXECUTE ON FUNCTION store_profile_embedding(UUID, vector, TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION get_user_profile_summary(UUID) TO service_role;
-- ==========================================
-- DAILY MATCH TRACKING
-- ==========================================
-- Consolidated from: 006_daily_match_tracking (now part of core schema)
-- Tracks match views for daily limits and history
-- ==========================================

-- Daily Match Views (for tier-based daily limits)
CREATE TABLE IF NOT EXISTS daily_match_views (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    match_user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Date tracking (for daily reset)
    view_date DATE NOT NULL DEFAULT CURRENT_DATE,
    view_timestamp TIMESTAMPTZ DEFAULT NOW(),

    -- Match details
    compatibility_score FLOAT,
    match_action VARCHAR(20), -- 'viewed', 'liked', 'skipped', 'messaged'

    -- User's trust tier at time of match
    user_trust_tier VARCHAR(20), -- diamond, coral, pearl, shell, pebble

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Match History (long-term tracking)
CREATE TABLE IF NOT EXISTS match_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    match_user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Match details
    compatibility_score FLOAT NOT NULL,
    similarity_score FLOAT,
    importance_bonus FLOAT,
    trust_bonus FLOAT,
    final_score FLOAT,

    -- Metadata
    algorithm_version VARCHAR(20) DEFAULT 'v2.0',
    trust_tiers JSONB, -- {"user_tier": "gold", "match_tier": "silver"}

    -- User actions
    last_action VARCHAR(20), -- 'viewed', 'liked', 'skipped', 'messaged', 'blocked'
    last_action_at TIMESTAMPTZ DEFAULT NOW(),

    -- Timestamps
    first_matched_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for daily_match_views
CREATE INDEX IF NOT EXISTS idx_daily_match_views_user ON daily_match_views(user_id);
CREATE INDEX IF NOT EXISTS idx_daily_match_views_date ON daily_match_views(view_date);
CREATE INDEX IF NOT EXISTS idx_daily_match_views_user_date ON daily_match_views(user_id, view_date);
CREATE INDEX IF NOT EXISTS idx_daily_match_views_timestamp ON daily_match_views(view_timestamp);

-- Unique constraint: one user can't view the same match multiple times per day
CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_daily_match
    ON daily_match_views(user_id, match_user_id, view_date);

-- Indexes for match_history
CREATE INDEX IF NOT EXISTS idx_match_history_user ON match_history(user_id);
CREATE INDEX IF NOT EXISTS idx_match_history_match_user ON match_history(match_user_id);
CREATE INDEX IF NOT EXISTS idx_match_history_action ON match_history(last_action);
CREATE INDEX IF NOT EXISTS idx_match_history_score ON match_history(final_score);

-- Unique constraint: one match pair per history entry
CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_match_pair
    ON match_history(user_id, match_user_id);

-- Enable RLS
ALTER TABLE daily_match_views ENABLE ROW LEVEL SECURITY;
ALTER TABLE match_history ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view own match views"
    ON daily_match_views FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Service can insert match views"
    ON daily_match_views FOR INSERT
    WITH CHECK (true);

CREATE POLICY "Users can view own match history"
    ON match_history FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Service can manage match history"
    ON match_history FOR ALL
    USING (true);

-- ==========================================
-- DAILY MATCH FUNCTIONS
-- ==========================================

-- Get daily match count
CREATE OR REPLACE FUNCTION get_daily_match_count(p_user_id UUID, p_date DATE DEFAULT CURRENT_DATE)
RETURNS INTEGER AS $$
DECLARE
    v_count INTEGER;
BEGIN
    SELECT COUNT(DISTINCT match_user_id)
    INTO v_count
    FROM daily_match_views
    WHERE user_id = p_user_id
    AND view_date = p_date;

    RETURN COALESCE(v_count, 0);
END;
$$ LANGUAGE plpgsql;

-- Check if user can view more matches
CREATE OR REPLACE FUNCTION can_view_more_matches(p_user_id UUID)
RETURNS JSONB AS $$
DECLARE
    v_trust_tier VARCHAR(20);
    v_daily_count INTEGER;
    v_daily_limit INTEGER;
    v_can_view BOOLEAN;
    v_remaining INTEGER;
BEGIN
    -- Get user's trust tier from profiles
    SELECT trust_tier INTO v_trust_tier
    FROM profiles
    WHERE user_id = p_user_id;

    -- If no trust tier found, default to pebble
    IF v_trust_tier IS NULL THEN
        v_trust_tier := 'pebble';
    END IF;

    -- Get today's count
    v_daily_count := get_daily_match_count(p_user_id, CURRENT_DATE);

    -- Determine daily limit based on trust tier (Ocean Pearl Theme)
    v_daily_limit := CASE v_trust_tier
        WHEN 'diamond' THEN 30  -- Diamond: 30 matches/day
        WHEN 'coral' THEN 20    -- Coral: 20 matches/day
        WHEN 'pearl' THEN 15    -- Pearl: 15 matches/day
        WHEN 'shell' THEN 10    -- Shell: 10 matches/day
        WHEN 'pebble' THEN 5    -- Pebble: 5 matches/day
        ELSE 5
    END;

    -- Check if can view more
    v_can_view := v_daily_count < v_daily_limit;
    v_remaining := GREATEST(0, v_daily_limit - v_daily_count);

    RETURN jsonb_build_object(
        'can_view', v_can_view,
        'daily_count', v_daily_count,
        'daily_limit', v_daily_limit,
        'remaining', v_remaining,
        'trust_tier', v_trust_tier,
        'is_unlimited', false
    );
END;
$$ LANGUAGE plpgsql;

-- Log match view
CREATE OR REPLACE FUNCTION log_match_view(
    p_user_id UUID,
    p_match_user_id UUID,
    p_compatibility_score FLOAT,
    p_action VARCHAR(20) DEFAULT 'viewed'
)
RETURNS UUID AS $$
DECLARE
    v_trust_tier VARCHAR(20);
    v_view_id UUID;
BEGIN
    -- Get user's trust tier
    SELECT trust_tier INTO v_trust_tier
    FROM profiles
    WHERE user_id = p_user_id;

    -- Insert or update daily match view
    INSERT INTO daily_match_views (
        user_id,
        match_user_id,
        view_date,
        compatibility_score,
        match_action,
        user_trust_tier
    ) VALUES (
        p_user_id,
        p_match_user_id,
        CURRENT_DATE,
        p_compatibility_score,
        p_action,
        COALESCE(v_trust_tier, 'unverified')
    )
    ON CONFLICT (user_id, match_user_id, view_date)
    DO UPDATE SET
        match_action = EXCLUDED.match_action,
        view_timestamp = NOW()
    RETURNING id INTO v_view_id;

    RETURN v_view_id;
END;
$$ LANGUAGE plpgsql;

-- Get match view statistics
CREATE OR REPLACE FUNCTION get_match_view_stats(p_user_id UUID, p_days INTEGER DEFAULT 7)
RETURNS JSONB AS $$
DECLARE
    v_stats JSONB;
BEGIN
    WITH date_range AS (
        SELECT generate_series(
            CURRENT_DATE - (p_days - 1),
            CURRENT_DATE,
            '1 day'::interval
        )::date AS view_date
    ),
    daily_counts AS (
        SELECT
            dr.view_date,
            COALESCE(COUNT(DISTINCT dmv.match_user_id), 0) AS count
        FROM date_range dr
        LEFT JOIN daily_match_views dmv
            ON dmv.user_id = p_user_id
            AND dmv.view_date = dr.view_date
        GROUP BY dr.view_date
        ORDER BY dr.view_date DESC
    )
    SELECT jsonb_build_object(
        'user_id', p_user_id,
        'period_days', p_days,
        'total_views', SUM(count),
        'average_per_day', ROUND(AVG(count)::numeric, 1),
        'max_per_day', MAX(count),
        'daily_breakdown', jsonb_agg(
            jsonb_build_object(
                'date', view_date,
                'count', count
            )
            ORDER BY view_date DESC
        )
    )
    INTO v_stats
    FROM daily_counts;

    RETURN v_stats;
END;
$$ LANGUAGE plpgsql;

-- Cleanup old match views (keep last 30 days)
CREATE OR REPLACE FUNCTION cleanup_old_match_views()
RETURNS INTEGER AS $$
DECLARE
    v_deleted_count INTEGER;
BEGIN
    DELETE FROM daily_match_views
    WHERE view_date < CURRENT_DATE - INTERVAL '30 days';
    
    GET DIAGNOSTICS v_deleted_count = ROW_COUNT;
    RETURN v_deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT EXECUTE ON FUNCTION get_daily_match_count TO authenticated;
GRANT EXECUTE ON FUNCTION can_view_more_matches TO authenticated;
GRANT EXECUTE ON FUNCTION log_match_view TO authenticated;
GRANT EXECUTE ON FUNCTION get_match_view_stats TO authenticated;
GRANT EXECUTE ON FUNCTION cleanup_old_match_views TO service_role;

-- ==========================================
-- HELPFUL VIEWS
-- ==========================================

-- Current day match counts by trust tier
CREATE OR REPLACE VIEW v_daily_match_counts_by_tier AS
SELECT
    p.trust_tier,
    COUNT(DISTINCT dmv.user_id) AS users_matching_today,
    SUM(CASE WHEN dmv.view_date = CURRENT_DATE THEN 1 ELSE 0 END) AS total_views_today,
    ROUND(AVG(CASE WHEN dmv.view_date = CURRENT_DATE THEN 1 ELSE 0 END)::numeric, 2) AS avg_views_per_user
FROM profiles p
LEFT JOIN daily_match_views dmv ON dmv.user_id = p.user_id AND dmv.view_date = CURRENT_DATE
WHERE p.trust_tier IS NOT NULL
GROUP BY p.trust_tier
ORDER BY
    CASE p.trust_tier
        WHEN 'diamond' THEN 1
        WHEN 'coral' THEN 2
        WHEN 'pearl' THEN 3
        WHEN 'shell' THEN 4
        WHEN 'pebble' THEN 5
        ELSE 6
    END;

COMMENT ON TABLE daily_match_views IS 'Tracks daily match views for tier-based limits (Diamond=30, Coral=20, Pearl=15, Shell=10, Pebble=5)';
COMMENT ON TABLE match_history IS 'Long-term match history and user actions';
