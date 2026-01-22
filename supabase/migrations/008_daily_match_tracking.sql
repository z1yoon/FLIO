-- ==========================================
-- FLIO Daily Match Tracking
-- ==========================================
-- This migration adds match view tracking for daily limits
-- based on trust tiers (Diamond/Coral/Pearl/Shell/Pebble)
-- ==========================================

-- ===================
-- 1. DAILY MATCH VIEW TRACKING TABLE
-- ===================

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

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_daily_match_views_user ON daily_match_views(user_id);
CREATE INDEX IF NOT EXISTS idx_daily_match_views_date ON daily_match_views(view_date);
CREATE INDEX IF NOT EXISTS idx_daily_match_views_user_date ON daily_match_views(user_id, view_date);
CREATE INDEX IF NOT EXISTS idx_daily_match_views_timestamp ON daily_match_views(view_timestamp);

-- Unique constraint: one user can't view the same match multiple times per day
CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_daily_match
    ON daily_match_views(user_id, match_user_id, view_date);

-- ===================
-- 2. MATCH HISTORY TABLE (Long-term tracking)
-- ===================

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

-- Indexes
CREATE INDEX IF NOT EXISTS idx_match_history_user ON match_history(user_id);
CREATE INDEX IF NOT EXISTS idx_match_history_match_user ON match_history(match_user_id);
CREATE INDEX IF NOT EXISTS idx_match_history_action ON match_history(last_action);
CREATE INDEX IF NOT EXISTS idx_match_history_score ON match_history(final_score);

-- Unique constraint: one match pair per history entry
CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_match_pair
    ON match_history(user_id, match_user_id);

-- ===================
-- 3. DATABASE FUNCTIONS
-- ===================

-- Function to get daily match count for a user
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

-- Function to check if user can view more matches today
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

-- Function to log match view
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

-- Function to get match view statistics
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

-- ===================
-- 4. ROW LEVEL SECURITY
-- ===================

-- Enable RLS on new tables
ALTER TABLE daily_match_views ENABLE ROW LEVEL SECURITY;
ALTER TABLE match_history ENABLE ROW LEVEL SECURITY;

-- Users can view their own match views
CREATE POLICY "Users can view own match views"
    ON daily_match_views FOR SELECT
    USING (auth.uid() = user_id);

-- Users can insert their own match views (system inserts via service role)
CREATE POLICY "Service can insert match views"
    ON daily_match_views FOR INSERT
    WITH CHECK (true);  -- Service role handles this

-- Users can view their own match history
CREATE POLICY "Users can view own match history"
    ON match_history FOR SELECT
    USING (auth.uid() = user_id);

-- Service can manage match history
CREATE POLICY "Service can manage match history"
    ON match_history FOR ALL
    USING (true);

-- ===================
-- 5. AUTOMATIC CLEANUP (Optional)
-- ===================

-- Function to clean up old daily match views (keep last 30 days)
CREATE OR REPLACE FUNCTION cleanup_old_match_views()
RETURNS INTEGER AS $$
DECLARE
    v_deleted_count INTEGER;
BEGIN
    DELETE FROM daily_match_views
    WHERE view_date < CURRENT_DATE - INTERVAL '30 days'
    RETURNING COUNT(*) INTO v_deleted_count;

    RETURN v_deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Comment: You can schedule this function to run daily via pg_cron or external scheduler
-- Example: SELECT cleanup_old_match_views();

-- ===================
-- 6. HELPFUL VIEWS
-- ===================

-- View: Current day match counts by trust tier
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

-- ===================
-- MIGRATION COMPLETE
-- ===================

-- Verify migration
DO $$
BEGIN
    RAISE NOTICE 'Migration 008 completed successfully';
    RAISE NOTICE 'Created tables: daily_match_views, match_history';
    RAISE NOTICE 'Created functions: get_daily_match_count, can_view_more_matches, log_match_view, get_match_view_stats';
    RAISE NOTICE 'Created view: v_daily_match_counts_by_tier';
    RAISE NOTICE 'Daily match limits (Ocean Pearl Theme): Diamond=30, Coral=20, Pearl=15, Shell=10, Pebble=5';
END $$;
