-- ==========================================
-- FLIO Matching and Tracking System
-- ==========================================
-- Migration: 003_matching_and_tracking.sql
-- Description: Comprehensive matching system with AI embeddings, daily limits, and preference tracking
-- Dependencies: 001_users_and_profiles.sql, 002_questions_and_answers.sql
-- Version: 2.0 (2026)
-- ==========================================
-- Consolidated from:
--   - 007_ai_matching_functions.sql
--   - 008_daily_match_tracking.sql
--   - 009_reshuffle_system.sql
-- ==========================================

-- ==========================================
-- TABLE: daily_match_views
-- ==========================================
-- Tracks daily match views for tier-based limits (Diamond=30, Coral=20, Pearl=15, Shell=10, Pebble=5)

CREATE TABLE IF NOT EXISTS daily_match_views (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    match_user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Date tracking (for daily reset)
    view_date DATE NOT NULL DEFAULT CURRENT_DATE,
    view_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Match details
    compatibility_score FLOAT,
    match_action VARCHAR(20) CHECK (match_action IN ('viewed', 'liked', 'skipped', 'messaged', 'blocked')),

    -- User's trust tier at time of match
    user_trust_tier VARCHAR(20) CHECK (user_trust_tier IN ('diamond', 'coral', 'pearl', 'shell', 'pebble', 'unverified')),

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT daily_match_views_users_different CHECK (user_id != match_user_id),
    CONSTRAINT daily_match_views_score_range CHECK (compatibility_score IS NULL OR (compatibility_score >= 0 AND compatibility_score <= 1))
);

-- ==========================================
-- TABLE: match_history
-- ==========================================
-- Long-term match history and user actions with algorithm versioning

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
    algorithm_version VARCHAR(20) NOT NULL DEFAULT 'v2.0',
    trust_tiers JSONB, -- {"user_tier": "coral", "match_tier": "pearl"}

    -- User actions
    last_action VARCHAR(20) CHECK (last_action IN ('viewed', 'liked', 'skipped', 'messaged', 'blocked', 'unmatched')),
    last_action_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Timestamps
    first_matched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT match_history_users_different CHECK (user_id != match_user_id),
    CONSTRAINT match_history_score_range CHECK (compatibility_score >= 0 AND compatibility_score <= 1),
    CONSTRAINT match_history_similarity_range CHECK (similarity_score IS NULL OR (similarity_score >= 0 AND similarity_score <= 1)),
    CONSTRAINT match_history_final_range CHECK (final_score IS NULL OR (final_score >= 0 AND final_score <= 1))
);

-- ==========================================
-- TABLE: reshuffle_feedback
-- ==========================================
-- Stores user feedback when requesting new matches to improve future recommendations

CREATE TABLE IF NOT EXISTS reshuffle_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(user_id) ON DELETE CASCADE,
    preference_text TEXT NOT NULL,
    rejected_match_ids UUID[] DEFAULT '{}',

    -- AI-analyzed preferences
    analyzed_preferences JSONB,
    preference_categories TEXT[],

    -- Matching context
    previous_match_count INTEGER,
    new_match_count INTEGER,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT reshuffle_feedback_text_length CHECK (char_length(preference_text) > 0 AND char_length(preference_text) <= 1000),
    CONSTRAINT reshuffle_feedback_counts_valid CHECK (
        (previous_match_count IS NULL OR previous_match_count >= 0) AND
        (new_match_count IS NULL OR new_match_count >= 0)
    )
);

-- ==========================================
-- TABLE: preference_analysis_cache
-- ==========================================
-- Caches AI analysis results for user preferences to reduce API costs and improve performance

CREATE TABLE IF NOT EXISTS preference_analysis_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    preference_text TEXT NOT NULL UNIQUE,
    analysis_data JSONB NOT NULL,
    usage_count INTEGER NOT NULL DEFAULT 1,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT preference_cache_text_length CHECK (char_length(preference_text) > 0),
    CONSTRAINT preference_cache_usage_positive CHECK (usage_count > 0)
);

-- ==========================================
-- INDEXES: Foreign Keys
-- ==========================================

-- daily_match_views indexes
CREATE INDEX IF NOT EXISTS idx_daily_match_views_user_id ON daily_match_views(user_id);
CREATE INDEX IF NOT EXISTS idx_daily_match_views_match_user_id ON daily_match_views(match_user_id);
CREATE INDEX IF NOT EXISTS idx_daily_match_views_date ON daily_match_views(view_date);
CREATE INDEX IF NOT EXISTS idx_daily_match_views_user_date ON daily_match_views(user_id, view_date);
CREATE INDEX IF NOT EXISTS idx_daily_match_views_timestamp ON daily_match_views(view_timestamp);
CREATE INDEX IF NOT EXISTS idx_daily_match_views_action ON daily_match_views(match_action) WHERE match_action IS NOT NULL;

-- Unique constraint: one user can't view the same match multiple times per day
CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_daily_match
    ON daily_match_views(user_id, match_user_id, view_date);

-- match_history indexes
CREATE INDEX IF NOT EXISTS idx_match_history_user_id ON match_history(user_id);
CREATE INDEX IF NOT EXISTS idx_match_history_match_user_id ON match_history(match_user_id);
CREATE INDEX IF NOT EXISTS idx_match_history_action ON match_history(last_action) WHERE last_action IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_match_history_score ON match_history(final_score DESC) WHERE final_score IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_match_history_updated_at ON match_history(updated_at DESC);

-- Unique constraint: one match pair per history entry
CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_match_pair
    ON match_history(user_id, match_user_id);

-- reshuffle_feedback indexes
CREATE INDEX IF NOT EXISTS idx_reshuffle_user_id ON reshuffle_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_reshuffle_user_created ON reshuffle_feedback(user_id, created_at DESC);

-- preference_analysis_cache indexes
CREATE INDEX IF NOT EXISTS idx_preference_text ON preference_analysis_cache(preference_text);
CREATE INDEX IF NOT EXISTS idx_preference_usage ON preference_analysis_cache(usage_count DESC, created_at DESC);

-- ==========================================
-- INDEXES: JSONB (GIN)
-- ==========================================

-- GIN index for trust_tiers in match_history
CREATE INDEX IF NOT EXISTS idx_match_history_trust_tiers_gin ON match_history USING GIN(trust_tiers);

-- GIN index for analyzed_preferences in reshuffle_feedback
CREATE INDEX IF NOT EXISTS idx_reshuffle_analyzed_preferences_gin ON reshuffle_feedback USING GIN(analyzed_preferences);

-- GIN index for analysis_data in preference_analysis_cache
CREATE INDEX IF NOT EXISTS idx_preference_analysis_data_gin ON preference_analysis_cache USING GIN(analysis_data);

-- ==========================================
-- FUNCTIONS: AI Matching (Vector Embeddings)
-- ==========================================

-- Find Similar Profiles (1024D Embeddings)
CREATE OR REPLACE FUNCTION find_similar_profiles(
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
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- Store Profile Embedding
CREATE OR REPLACE FUNCTION store_profile_embedding(
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
$$ LANGUAGE plpgsql VOLATILE SECURITY DEFINER;

-- Get User Profile Summary
CREATE OR REPLACE FUNCTION get_user_profile_summary(p_user_id UUID)
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
        DATE_PART('year', AGE(p.birth_date))::INTEGER AS age,
        p.gender,
        p.bio,
        p.photos,
        (p.profile_embedding IS NOT NULL) AS has_embedding
    FROM public.profiles p
    WHERE p.user_id = p_user_id;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- ==========================================
-- FUNCTIONS: Daily Match Tracking
-- ==========================================

-- Get daily match count
CREATE OR REPLACE FUNCTION get_daily_match_count(
    p_user_id UUID,
    p_date DATE DEFAULT CURRENT_DATE
)
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
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- Check if user can view more matches (tier-based limits)
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
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

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
$$ LANGUAGE plpgsql VOLATILE SECURITY DEFINER;

-- Get match view statistics
CREATE OR REPLACE FUNCTION get_match_view_stats(
    p_user_id UUID,
    p_days INTEGER DEFAULT 7
)
RETURNS JSONB AS $$
DECLARE
    v_stats JSONB;
BEGIN
    WITH date_range AS (
        SELECT generate_series(
            CURRENT_DATE - (p_days - 1),
            CURRENT_DATE,
            '1 day'::interval
        )::DATE AS view_date
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
        'average_per_day', ROUND(AVG(count)::NUMERIC, 1),
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
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

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
$$ LANGUAGE plpgsql VOLATILE SECURITY DEFINER;

-- ==========================================
-- FUNCTIONS: Reshuffle & Preference Analysis
-- ==========================================

-- Get user reshuffle context
CREATE OR REPLACE FUNCTION get_user_reshuffle_context(
    p_user_id UUID,
    p_limit INTEGER DEFAULT 3
)
RETURNS TABLE (
    preference_text TEXT,
    analyzed_preferences JSONB,
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        rf.preference_text,
        rf.analyzed_preferences,
        rf.created_at
    FROM reshuffle_feedback rf
    WHERE rf.user_id = p_user_id
    ORDER BY rf.created_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- Increment preference usage counter
CREATE OR REPLACE FUNCTION increment_preference_usage(p_preference_text TEXT)
RETURNS VOID AS $$
BEGIN
    UPDATE preference_analysis_cache
    SET
        usage_count = usage_count + 1,
        updated_at = NOW()
    WHERE preference_text = LOWER(TRIM(p_preference_text));
END;
$$ LANGUAGE plpgsql VOLATILE SECURITY DEFINER;

-- Clean preference cache (keep top 1000)
CREATE OR REPLACE FUNCTION clean_preference_cache()
RETURNS INTEGER AS $$
DECLARE
    v_deleted_count INTEGER;
BEGIN
    WITH ranked_preferences AS (
        SELECT
            id,
            ROW_NUMBER() OVER (ORDER BY usage_count DESC, updated_at DESC) AS rank
        FROM preference_analysis_cache
    )
    DELETE FROM preference_analysis_cache
    WHERE id IN (
        SELECT id FROM ranked_preferences WHERE rank > 1000
    );

    GET DIAGNOSTICS v_deleted_count = ROW_COUNT;
    RETURN v_deleted_count;
END;
$$ LANGUAGE plpgsql VOLATILE SECURITY DEFINER;

-- ==========================================
-- TRIGGERS: updated_at
-- ==========================================

-- Trigger for match_history
CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_updated_at_match_history
    BEFORE UPDATE ON match_history
    FOR EACH ROW
    EXECUTE FUNCTION trigger_set_updated_at();

-- Trigger for preference_analysis_cache
CREATE TRIGGER set_updated_at_preference_cache
    BEFORE UPDATE ON preference_analysis_cache
    FOR EACH ROW
    EXECUTE FUNCTION trigger_set_updated_at();

-- ==========================================
-- ROW LEVEL SECURITY (RLS)
-- ==========================================

ALTER TABLE daily_match_views ENABLE ROW LEVEL SECURITY;
ALTER TABLE match_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE reshuffle_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE preference_analysis_cache ENABLE ROW LEVEL SECURITY;

-- daily_match_views policies
CREATE POLICY "Users can view own match views"
    ON daily_match_views FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own match views"
    ON daily_match_views FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Service can manage all match views"
    ON daily_match_views FOR ALL
    USING (true)
    WITH CHECK (true);

-- match_history policies
CREATE POLICY "Users can view own match history"
    ON match_history FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can update own match history"
    ON match_history FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can insert own match history"
    ON match_history FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Service can manage all match history"
    ON match_history FOR ALL
    USING (true)
    WITH CHECK (true);

-- reshuffle_feedback policies
CREATE POLICY "Users can view own reshuffle feedback"
    ON reshuffle_feedback FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own reshuffle feedback"
    ON reshuffle_feedback FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Service can manage all reshuffle feedback"
    ON reshuffle_feedback FOR ALL
    USING (true)
    WITH CHECK (true);

-- preference_analysis_cache policies (read-only for authenticated users)
CREATE POLICY "Authenticated users can view preference cache"
    ON preference_analysis_cache FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Service can manage preference cache"
    ON preference_analysis_cache FOR ALL
    USING (true)
    WITH CHECK (true);

-- ==========================================
-- VIEWS: Analytics & Monitoring
-- ==========================================

-- Current day match counts by trust tier
CREATE OR REPLACE VIEW v_daily_match_counts_by_tier AS
SELECT
    p.trust_tier,
    COUNT(DISTINCT dmv.user_id) AS users_matching_today,
    SUM(CASE WHEN dmv.view_date = CURRENT_DATE THEN 1 ELSE 0 END) AS total_views_today,
    ROUND(AVG(CASE WHEN dmv.view_date = CURRENT_DATE THEN 1 ELSE 0 END)::NUMERIC, 2) AS avg_views_per_user
FROM profiles p
LEFT JOIN daily_match_views dmv
    ON dmv.user_id = p.user_id
    AND dmv.view_date = CURRENT_DATE
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

-- ==========================================
-- GRANT PERMISSIONS
-- ==========================================

-- AI Matching Functions
GRANT EXECUTE ON FUNCTION find_similar_profiles(vector, UUID, INTEGER, VARCHAR, INTEGER, INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION store_profile_embedding(UUID, vector, TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION get_user_profile_summary(UUID) TO authenticated;

GRANT EXECUTE ON FUNCTION find_similar_profiles(vector, UUID, INTEGER, VARCHAR, INTEGER, INTEGER) TO service_role;
GRANT EXECUTE ON FUNCTION store_profile_embedding(UUID, vector, TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION get_user_profile_summary(UUID) TO service_role;

-- Daily Match Tracking Functions
GRANT EXECUTE ON FUNCTION get_daily_match_count(UUID, DATE) TO authenticated;
GRANT EXECUTE ON FUNCTION can_view_more_matches(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION log_match_view(UUID, UUID, FLOAT, VARCHAR) TO authenticated;
GRANT EXECUTE ON FUNCTION get_match_view_stats(UUID, INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION cleanup_old_match_views() TO service_role;

-- Reshuffle & Preference Functions
GRANT EXECUTE ON FUNCTION get_user_reshuffle_context(UUID, INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION increment_preference_usage(TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION clean_preference_cache() TO service_role;

-- Views
GRANT SELECT ON v_daily_match_counts_by_tier TO authenticated;
GRANT SELECT ON v_daily_match_counts_by_tier TO service_role;

-- ==========================================
-- SEED DATA: Common Korean Preferences
-- ==========================================

INSERT INTO preference_analysis_cache (preference_text, analysis_data, usage_count) VALUES
('매운걸 좋아하는 사람', '{
    "preference_category": "음식",
    "search_keywords": ["매운", "맵", "매콤", "화끈"],
    "answer_patterns": ["매운 음식을 좋아한다", "맵게 먹는다", "매콤한 것을 선호"],
    "matching_criteria": {
        "must_have": ["매운음식선호"],
        "nice_to_have": ["요리관심", "외식선호"],
        "avoid": ["매운음식싫어", "순한맛선호"]
    },
    "confidence_score": 0.9,
    "explanation": "매운 음식을 좋아하는 사람을 찾는 명확한 요청"
}', 10),

('운동 좋아하는 사람', '{
    "preference_category": "활동",
    "search_keywords": ["운동", "헬스", "피트니스", "체육관", "요가"],
    "answer_patterns": ["운동을 즐긴다", "헬스장을 다닌다", "피트니스에 관심"],
    "matching_criteria": {
        "must_have": ["운동관심", "건강관리"],
        "nice_to_have": ["활동적성향", "규칙적생활"],
        "avoid": ["운동싫어", "집에만있기선호"]
    },
    "confidence_score": 0.9,
    "explanation": "활동적이고 운동을 좋아하는 사람을 원하는 요청"
}', 8),

('가족을 중시하는 사람', '{
    "preference_category": "가치관",
    "search_keywords": ["가족", "가정", "부모님", "효도", "가족모임"],
    "answer_patterns": ["가족을 중요하게 생각", "가정적인 사람", "부모님께 효도"],
    "matching_criteria": {
        "must_have": ["가족중시", "가정적성향"],
        "nice_to_have": ["책임감", "전통적가치관"],
        "avoid": ["개인주의", "가족무관심"]
    },
    "confidence_score": 0.85,
    "explanation": "가족을 중요하게 생각하는 전통적 가치관을 가진 사람을 원함"
}', 6)
ON CONFLICT (preference_text) DO NOTHING;

-- ==========================================
-- COMMENTS: Table Documentation
-- ==========================================

COMMENT ON TABLE daily_match_views IS 'Tracks daily match views for tier-based limits (Diamond=30, Coral=20, Pearl=15, Shell=10, Pebble=5). Records are kept for 30 days for analytics.';
COMMENT ON TABLE match_history IS 'Long-term match history with algorithm versioning and user actions. Stores comprehensive matching metadata for analytics and algorithm improvement.';
COMMENT ON TABLE reshuffle_feedback IS 'Stores user feedback when requesting new matches to improve future recommendations. Includes AI-analyzed preferences and rejection patterns.';
COMMENT ON TABLE preference_analysis_cache IS 'Caches AI analysis results for user preferences to reduce API costs and improve performance. Maintains top 1000 most-used entries.';

-- Column comments for daily_match_views
COMMENT ON COLUMN daily_match_views.view_date IS 'Date of the match view for daily limit enforcement (resets at midnight)';
COMMENT ON COLUMN daily_match_views.compatibility_score IS 'Final compatibility score between 0-1 calculated by matching algorithm';
COMMENT ON COLUMN daily_match_views.match_action IS 'User action taken: viewed, liked, skipped, messaged, blocked';
COMMENT ON COLUMN daily_match_views.user_trust_tier IS 'User trust tier at time of match (determines daily limit)';

-- Column comments for match_history
COMMENT ON COLUMN match_history.algorithm_version IS 'Version of matching algorithm used (for A/B testing and rollbacks)';
COMMENT ON COLUMN match_history.trust_tiers IS 'JSONB storing both users trust tiers at match time';
COMMENT ON COLUMN match_history.final_score IS 'Final weighted score after all bonuses and adjustments';
COMMENT ON COLUMN match_history.last_action IS 'Most recent action taken on this match';

-- Column comments for reshuffle_feedback
COMMENT ON COLUMN reshuffle_feedback.analyzed_preferences IS 'AI-parsed and structured preference data for matching enhancement';
COMMENT ON COLUMN reshuffle_feedback.rejected_match_ids IS 'Array of user IDs that were rejected (to avoid showing again)';

-- Column comments for preference_analysis_cache
COMMENT ON COLUMN preference_analysis_cache.usage_count IS 'Number of times this preference analysis has been reused (for cache retention)';
COMMENT ON COLUMN preference_analysis_cache.analysis_data IS 'Structured AI analysis with categories, keywords, and matching criteria';

-- Function comments
COMMENT ON FUNCTION find_similar_profiles IS 'Finds similar profiles using 1024D vector embeddings with cosine similarity. Supports gender and age filtering.';
COMMENT ON FUNCTION store_profile_embedding IS 'Stores or updates a user profile embedding vector (1024D) for matching';
COMMENT ON FUNCTION get_user_profile_summary IS 'Returns essential profile information including embedding status';
COMMENT ON FUNCTION get_daily_match_count IS 'Returns count of unique matches viewed by user on specified date';
COMMENT ON FUNCTION can_view_more_matches IS 'Checks if user has remaining daily match views based on trust tier limits';
COMMENT ON FUNCTION log_match_view IS 'Records a match view and updates daily tracking (idempotent for same-day views)';
COMMENT ON FUNCTION get_match_view_stats IS 'Returns match viewing statistics over specified number of days';
COMMENT ON FUNCTION cleanup_old_match_views IS 'Removes match view records older than 30 days (should run nightly)';
COMMENT ON FUNCTION get_user_reshuffle_context IS 'Retrieves recent reshuffle preferences for a user to provide context for new matches';
COMMENT ON FUNCTION increment_preference_usage IS 'Increments usage counter for preference cache analytics';
COMMENT ON FUNCTION clean_preference_cache IS 'Maintains cache size by removing least used entries (keeps top 1000)';

-- ==========================================
-- END OF MIGRATION
-- ==========================================
