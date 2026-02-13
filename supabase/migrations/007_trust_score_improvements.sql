-- ==========================================
-- Trust Score System Improvements
-- ==========================================
-- Migration: 007_trust_score_improvements.sql
-- Description: Add missing trust score components and history tracking
-- Dependencies: 005_trust_and_reputation.sql
-- Date: 2026-02-06
-- ==========================================

-- ==========================================
-- PART 1: Add Missing Trust Score Columns
-- ==========================================

-- Add photo_score, social_score, reputation_score to user_trust_scores table
-- Previously these were calculated on-the-fly, now we store them for consistency

ALTER TABLE user_trust_scores
ADD COLUMN IF NOT EXISTS photo_score FLOAT DEFAULT 0.0 CHECK (photo_score >= 0.0 AND photo_score <= 1.0),
ADD COLUMN IF NOT EXISTS social_score FLOAT DEFAULT 0.0 CHECK (social_score >= 0.0 AND social_score <= 1.0),
ADD COLUMN IF NOT EXISTS reputation_score FLOAT DEFAULT 1.0 CHECK (reputation_score >= 0.0 AND reputation_score <= 1.0);

-- Add index for faster lookups
CREATE INDEX IF NOT EXISTS idx_user_trust_scores_tier ON user_trust_scores(trust_tier);
CREATE INDEX IF NOT EXISTS idx_user_trust_scores_score ON user_trust_scores(total_trust_score DESC);

-- ==========================================
-- PART 2: Trust Score History Tracking
-- ==========================================

-- Track trust score changes over time for analytics and user feedback
CREATE TABLE IF NOT EXISTS user_trust_score_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Score snapshot at this point in time
    document_score FLOAT NOT NULL,
    photo_score FLOAT NOT NULL,
    consistency_score FLOAT NOT NULL,
    behavioral_score FLOAT NOT NULL,
    social_score FLOAT NOT NULL,
    completeness_score FLOAT NOT NULL,
    reputation_score FLOAT NOT NULL,
    total_trust_score FLOAT NOT NULL,
    trust_tier VARCHAR(20) NOT NULL,

    -- What triggered this calculation
    trigger_reason VARCHAR(50) NOT NULL CHECK (trigger_reason IN (
        'manual_recalculation',
        'document_verified',
        'photo_verified',
        'social_verified',
        'profile_updated',
        'behavior_logged',
        'report_received',
        'scheduled_daily',
        'tier_changed'
    )),

    -- Change tracking
    previous_total_score FLOAT,
    score_change FLOAT,
    previous_tier VARCHAR(20),
    tier_changed BOOLEAN DEFAULT FALSE,

    -- Timestamps
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT trust_history_score_range CHECK (total_trust_score >= 0.0 AND total_trust_score <= 1.0),
    CONSTRAINT trust_history_tier_valid CHECK (trust_tier IN ('diamond', 'coral', 'pearl', 'shell', 'pebble'))
);

-- Indexes for history queries
CREATE INDEX IF NOT EXISTS idx_trust_history_user_id ON user_trust_score_history(user_id);
CREATE INDEX IF NOT EXISTS idx_trust_history_calculated_at ON user_trust_score_history(calculated_at DESC);
CREATE INDEX IF NOT EXISTS idx_trust_history_tier_changed ON user_trust_score_history(tier_changed) WHERE tier_changed = TRUE;

-- ==========================================
-- PART 3: Update calculate_trust_score Function
-- ==========================================

-- Update the function to store all 7 components and log history
CREATE OR REPLACE FUNCTION calculate_trust_score(p_user_id UUID)
RETURNS JSONB AS $$
DECLARE
    v_document_score FLOAT;
    v_photo_score FLOAT;
    v_consistency_score FLOAT;
    v_behavioral_score FLOAT;
    v_social_score FLOAT;
    v_completeness_score FLOAT;
    v_reputation_score FLOAT;
    v_total_score FLOAT;
    v_trust_tier VARCHAR(20);
    v_previous_score FLOAT;
    v_previous_tier VARCHAR(20);
    v_tier_changed BOOLEAN;
BEGIN
    -- Get previous score for comparison
    SELECT total_trust_score, trust_tier
    INTO v_previous_score, v_previous_tier
    FROM user_trust_scores
    WHERE user_id = p_user_id;

    -- Calculate all 7 components (using existing helper functions)
    v_document_score := calculate_document_verification_score(p_user_id);
    v_photo_score := calculate_photo_verification_score(p_user_id);
    v_consistency_score := calculate_consistency_score(p_user_id);
    v_behavioral_score := calculate_behavioral_score(p_user_id);
    v_social_score := calculate_social_verification_score(p_user_id);
    v_completeness_score := calculate_completeness_score(p_user_id);
    v_reputation_score := calculate_reputation_score(p_user_id);

    -- Calculate weighted total (7 components)
    v_total_score := (
        (v_document_score * 0.25) +
        (v_photo_score * 0.20) +
        (v_consistency_score * 0.15) +
        (v_behavioral_score * 0.15) +
        (v_social_score * 0.10) +
        (v_completeness_score * 0.10) +
        (v_reputation_score * 0.05)
    );

    -- Determine tier
    v_trust_tier := calculate_tier_from_score(v_total_score);
    v_tier_changed := (v_previous_tier IS NULL OR v_previous_tier != v_trust_tier);

    -- Upsert into user_trust_scores (now with all 7 components)
    INSERT INTO user_trust_scores (
        user_id,
        document_score,
        photo_score,
        consistency_score,
        behavioral_score,
        social_score,
        completeness_score,
        reputation_score,
        total_trust_score,
        trust_tier,
        last_calculated_at,
        updated_at
    ) VALUES (
        p_user_id,
        v_document_score,
        v_photo_score,
        v_consistency_score,
        v_behavioral_score,
        v_social_score,
        v_completeness_score,
        v_reputation_score,
        v_total_score,
        v_trust_tier,
        NOW(),
        NOW()
    )
    ON CONFLICT (user_id) DO UPDATE SET
        document_score = EXCLUDED.document_score,
        photo_score = EXCLUDED.photo_score,
        consistency_score = EXCLUDED.consistency_score,
        behavioral_score = EXCLUDED.behavioral_score,
        social_score = EXCLUDED.social_score,
        completeness_score = EXCLUDED.completeness_score,
        reputation_score = EXCLUDED.reputation_score,
        total_trust_score = EXCLUDED.total_trust_score,
        trust_tier = EXCLUDED.trust_tier,
        last_calculated_at = EXCLUDED.last_calculated_at,
        updated_at = EXCLUDED.updated_at;

    -- Log to history
    INSERT INTO user_trust_score_history (
        user_id,
        document_score,
        photo_score,
        consistency_score,
        behavioral_score,
        social_score,
        completeness_score,
        reputation_score,
        total_trust_score,
        trust_tier,
        trigger_reason,
        previous_total_score,
        score_change,
        previous_tier,
        tier_changed,
        calculated_at
    ) VALUES (
        p_user_id,
        v_document_score,
        v_photo_score,
        v_consistency_score,
        v_behavioral_score,
        v_social_score,
        v_completeness_score,
        v_reputation_score,
        v_total_score,
        v_trust_tier,
        'manual_recalculation',
        v_previous_score,
        CASE WHEN v_previous_score IS NOT NULL THEN v_total_score - v_previous_score ELSE NULL END,
        v_previous_tier,
        v_tier_changed,
        NOW()
    );

    -- Update profile tier
    UPDATE profiles
    SET trust_tier = v_trust_tier,
        updated_at = NOW()
    WHERE user_id = p_user_id;

    -- Return full breakdown
    RETURN jsonb_build_object(
        'user_id', p_user_id,
        'document_score', v_document_score,
        'photo_score', v_photo_score,
        'consistency_score', v_consistency_score,
        'behavioral_score', v_behavioral_score,
        'social_score', v_social_score,
        'completeness_score', v_completeness_score,
        'reputation_score', v_reputation_score,
        'total_score', v_total_score,
        'trust_tier', v_trust_tier,
        'previous_score', v_previous_score,
        'score_change', CASE WHEN v_previous_score IS NOT NULL THEN v_total_score - v_previous_score ELSE NULL END,
        'tier_changed', v_tier_changed,
        'calculated_at', NOW()
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ==========================================
-- PART 4: RLS Policies
-- ==========================================

-- Allow users to view their own trust score history
CREATE POLICY "Users can view own trust history"
    ON user_trust_score_history
    FOR SELECT
    USING (auth.uid() = user_id);

-- Service role can insert history
CREATE POLICY "Service role can insert trust history"
    ON user_trust_score_history
    FOR INSERT
    WITH CHECK (auth.role() = 'service_role');

-- ==========================================
-- PART 5: Helper Function - Get Trust Trend
-- ==========================================

-- Get user's trust score trend over time
CREATE OR REPLACE FUNCTION get_trust_score_trend(
    p_user_id UUID,
    p_days INTEGER DEFAULT 30
)
RETURNS TABLE (
    date DATE,
    total_score FLOAT,
    trust_tier VARCHAR(20),
    score_change FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        DATE(calculated_at) as date,
        AVG(total_trust_score)::FLOAT as total_score,
        MODE() WITHIN GROUP (ORDER BY trust_tier) as trust_tier,
        AVG(score_change)::FLOAT as score_change
    FROM user_trust_score_history
    WHERE user_id = p_user_id
        AND calculated_at >= NOW() - INTERVAL '1 day' * p_days
    GROUP BY DATE(calculated_at)
    ORDER BY date DESC;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- ==========================================
-- PART 6: Comments
-- ==========================================

COMMENT ON TABLE user_trust_score_history IS 'Tracks trust score changes over time for analytics and user feedback. Helps users see their progress toward higher tiers.';
COMMENT ON FUNCTION calculate_trust_score IS 'UPDATED: Now stores all 7 components (document 25%, photo 20%, consistency 15%, behavioral 15%, social 10%, completeness 10%, reputation 5%) and logs to history';
COMMENT ON FUNCTION get_trust_score_trend IS 'Get user trust score trend over specified number of days. Useful for showing progress charts in UI.';

-- ==========================================
-- PART 7: Grants
-- ==========================================

GRANT SELECT ON user_trust_score_history TO authenticated;
GRANT EXECUTE ON FUNCTION get_trust_score_trend TO authenticated, service_role;
