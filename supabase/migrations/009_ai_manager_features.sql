-- ==========================================
-- FLIO AI Manager Features
-- ==========================================
-- Migration: 009_ai_manager_features.sql
-- Description: Tables and functions for AI manager conversations,
--              structured match feedback, and profile diagnostics
-- Dependencies: 001, 002, 003
-- ==========================================

-- ==========================================
-- TABLE: ai_manager_sessions
-- ==========================================
-- Stores conversation history with the AI manager

CREATE TABLE IF NOT EXISTS ai_manager_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Session context
    session_type VARCHAR(30) NOT NULL DEFAULT 'general'
        CHECK (session_type IN ('onboarding', 'match_coaching', 'profile_improvement', 'general')),

    -- Messages as JSONB array: [{role, content, timestamp}]
    messages JSONB NOT NULL DEFAULT '[]'::jsonb,

    -- AI-extracted insights from conversation
    extracted_insights JSONB DEFAULT '{}'::jsonb,

    -- Session state
    is_active BOOLEAN DEFAULT TRUE,
    last_message_at TIMESTAMPTZ DEFAULT NOW(),

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ai_manager_sessions_user_id ON ai_manager_sessions(user_id);
CREATE INDEX idx_ai_manager_sessions_active ON ai_manager_sessions(user_id, is_active);
CREATE INDEX idx_ai_manager_sessions_type ON ai_manager_sessions(session_type);

CREATE TRIGGER ai_manager_sessions_updated_at
    BEFORE UPDATE ON ai_manager_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

COMMENT ON TABLE ai_manager_sessions IS 'AI manager conversation sessions per user';
COMMENT ON COLUMN ai_manager_sessions.messages IS 'Ordered array of {role, content, timestamp} message objects';
COMMENT ON COLUMN ai_manager_sessions.extracted_insights IS 'AI-extracted preferences and constraints from conversation';

-- ==========================================
-- TABLE: followup_question_log
-- ==========================================
-- Tracks when and why follow-up questions were triggered

CREATE TABLE IF NOT EXISTS followup_question_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    question_id VARCHAR(100) NOT NULL,

    -- Original answer that triggered follow-up
    original_answer TEXT NOT NULL,
    ambiguity_score FLOAT NOT NULL CHECK (ambiguity_score >= 0 AND ambiguity_score <= 1),

    -- Generated follow-up
    followup_question TEXT NOT NULL,
    followup_answer TEXT,
    followup_answered_at TIMESTAMPTZ,

    -- Was the follow-up useful?
    followup_improved_clarity BOOLEAN,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_followup_log_user_id ON followup_question_log(user_id);
CREATE INDEX idx_followup_log_question_id ON followup_question_log(question_id);

COMMENT ON TABLE followup_question_log IS 'Log of AI-generated follow-up questions when answers are ambiguous';

-- ==========================================
-- TABLE: match_feedback
-- ==========================================
-- Structured feedback after viewing/interacting with a match

CREATE TABLE IF NOT EXISTS match_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    match_user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Overall rating
    overall_rating INTEGER CHECK (overall_rating >= 1 AND overall_rating <= 5),

    -- Dimension ratings (1-5)
    values_alignment_rating INTEGER CHECK (values_alignment_rating >= 1 AND values_alignment_rating <= 5),
    lifestyle_match_rating INTEGER CHECK (lifestyle_match_rating >= 1 AND lifestyle_match_rating <= 5),
    conversation_comfort_rating INTEGER CHECK (conversation_comfort_rating >= 1 AND conversation_comfort_rating <= 5),
    marriage_seriousness_rating INTEGER CHECK (marriage_seriousness_rating >= 1 AND marriage_seriousness_rating <= 5),

    -- Qualitative feedback
    positive_aspects TEXT[],   -- e.g. ['가치관 일치', '소통 방식']
    dealbreaker_aspects TEXT[], -- e.g. ['종교 차이', '거리 문제']
    free_text_feedback TEXT,

    -- Feedback type (implicit vs explicit)
    feedback_type VARCHAR(20) DEFAULT 'explicit'
        CHECK (feedback_type IN ('implicit', 'explicit')),

    -- Implicit signals (auto-collected)
    profile_view_duration_seconds INTEGER,
    conversation_initiated BOOLEAN DEFAULT FALSE,
    photos_viewed INTEGER DEFAULT 0,

    -- Was this match shown after a reshuffle?
    from_reshuffle BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_match_feedback UNIQUE (user_id, match_user_id)
);

CREATE INDEX idx_match_feedback_user_id ON match_feedback(user_id);
CREATE INDEX idx_match_feedback_match_user ON match_feedback(match_user_id);
CREATE INDEX idx_match_feedback_rating ON match_feedback(overall_rating);
CREATE INDEX idx_match_feedback_created ON match_feedback(created_at);

COMMENT ON TABLE match_feedback IS 'Structured feedback after viewing matches, used to improve matching weights';

-- ==========================================
-- TABLE: profile_diagnostics
-- ==========================================
-- Cached profile quality analysis results

CREATE TABLE IF NOT EXISTS profile_diagnostics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Overall score
    overall_score INTEGER NOT NULL CHECK (overall_score >= 0 AND overall_score <= 100),

    -- Dimension scores
    photo_score INTEGER CHECK (photo_score >= 0 AND photo_score <= 100),
    answer_completeness_score INTEGER CHECK (answer_completeness_score >= 0 AND answer_completeness_score <= 100),
    answer_quality_score INTEGER CHECK (answer_quality_score >= 0 AND answer_quality_score <= 100),
    preference_consistency_score INTEGER CHECK (preference_consistency_score >= 0 AND preference_consistency_score <= 100),

    -- Identified issues as JSONB: [{severity, issue, impact, solution}]
    issues JSONB NOT NULL DEFAULT '[]'::jsonb,

    -- AI-generated recommendations
    recommendations JSONB NOT NULL DEFAULT '[]'::jsonb,

    -- Predicted improvement from fixing issues
    estimated_match_improvement_pct INTEGER,

    -- Competitive context
    similar_profile_count INTEGER,
    market_percentile INTEGER, -- user is in top X% of profiles

    -- Cache control
    is_stale BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_profile_diagnostics_user ON profile_diagnostics(user_id);
CREATE INDEX idx_profile_diagnostics_score ON profile_diagnostics(overall_score);
CREATE INDEX idx_profile_diagnostics_stale ON profile_diagnostics(user_id, is_stale);

CREATE TRIGGER profile_diagnostics_updated_at
    BEFORE UPDATE ON profile_diagnostics
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

COMMENT ON TABLE profile_diagnostics IS 'AI-generated profile quality diagnostics with improvement suggestions';

-- ==========================================
-- TABLE: matching_weight_adjustments
-- ==========================================
-- Per-user learned question importance weights from feedback

CREATE TABLE IF NOT EXISTS matching_weight_adjustments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Question weights as JSONB: {question_id: weight_multiplier}
    -- Default 1.0 = no adjustment; > 1.0 = more important; < 1.0 = less important
    question_weights JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- How many feedback events contributed to these weights
    feedback_sample_size INTEGER DEFAULT 0,

    -- Confidence in the weights (0-1)
    confidence_score FLOAT DEFAULT 0.0,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_weight_per_user UNIQUE (user_id)
);

CREATE INDEX idx_weight_adjustments_user ON matching_weight_adjustments(user_id);

CREATE TRIGGER matching_weight_adjustments_updated_at
    BEFORE UPDATE ON matching_weight_adjustments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

COMMENT ON TABLE matching_weight_adjustments IS 'AI-learned per-user question importance weights derived from feedback history';

-- ==========================================
-- FUNCTION: get_user_feedback_summary
-- ==========================================
-- Returns aggregated feedback insights for a user

CREATE OR REPLACE FUNCTION get_user_feedback_summary(p_user_id UUID)
RETURNS JSONB AS $$
DECLARE
    v_result JSONB;
    v_total_feedback INTEGER;
    v_avg_rating FLOAT;
    v_common_positives TEXT[];
    v_common_dealbreakers TEXT[];
BEGIN
    SELECT
        COUNT(*),
        AVG(overall_rating)
    INTO v_total_feedback, v_avg_rating
    FROM match_feedback
    WHERE user_id = p_user_id
      AND overall_rating IS NOT NULL;

    -- Aggregate most common positive aspects
    SELECT ARRAY_AGG(aspect ORDER BY cnt DESC) INTO v_common_positives
    FROM (
        SELECT aspect, COUNT(*) as cnt
        FROM match_feedback, UNNEST(positive_aspects) AS aspect
        WHERE user_id = p_user_id
        GROUP BY aspect
        LIMIT 5
    ) sub;

    -- Aggregate most common dealbreakers
    SELECT ARRAY_AGG(aspect ORDER BY cnt DESC) INTO v_common_dealbreakers
    FROM (
        SELECT aspect, COUNT(*) as cnt
        FROM match_feedback, UNNEST(dealbreaker_aspects) AS aspect
        WHERE user_id = p_user_id
        GROUP BY aspect
        LIMIT 5
    ) sub;

    v_result := jsonb_build_object(
        'total_feedback', COALESCE(v_total_feedback, 0),
        'avg_rating', COALESCE(ROUND(v_avg_rating::numeric, 2), 0),
        'common_positives', COALESCE(to_jsonb(v_common_positives), '[]'::jsonb),
        'common_dealbreakers', COALESCE(to_jsonb(v_common_dealbreakers), '[]'::jsonb)
    );

    RETURN v_result;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_user_feedback_summary IS 'Aggregates a user''s match feedback to identify patterns for weight adjustment';

-- ==========================================
-- FUNCTION: upsert_matching_weights
-- ==========================================
-- Updates per-user question weights based on feedback patterns

CREATE OR REPLACE FUNCTION upsert_matching_weights(
    p_user_id UUID,
    p_question_weights JSONB,
    p_feedback_count INTEGER,
    p_confidence FLOAT
)
RETURNS VOID AS $$
BEGIN
    INSERT INTO matching_weight_adjustments (user_id, question_weights, feedback_sample_size, confidence_score)
    VALUES (p_user_id, p_question_weights, p_feedback_count, p_confidence)
    ON CONFLICT (user_id) DO UPDATE
        SET question_weights = p_question_weights,
            feedback_sample_size = p_feedback_count,
            confidence_score = p_confidence,
            updated_at = NOW();
END;
$$ LANGUAGE plpgsql;

-- ==========================================
-- RLS POLICIES
-- ==========================================

ALTER TABLE ai_manager_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE followup_question_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE match_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE profile_diagnostics ENABLE ROW LEVEL SECURITY;
ALTER TABLE matching_weight_adjustments ENABLE ROW LEVEL SECURITY;

-- ai_manager_sessions
CREATE POLICY "Users manage own AI sessions"
ON ai_manager_sessions FOR ALL TO authenticated
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- followup_question_log
CREATE POLICY "Users view own followup logs"
ON followup_question_log FOR ALL TO authenticated
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- match_feedback
CREATE POLICY "Users manage own match feedback"
ON match_feedback FOR ALL TO authenticated
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- profile_diagnostics
CREATE POLICY "Users view own diagnostics"
ON profile_diagnostics FOR SELECT TO authenticated
USING (auth.uid() = user_id);

CREATE POLICY "Service role can upsert diagnostics"
ON profile_diagnostics FOR ALL TO service_role
USING (true) WITH CHECK (true);

-- matching_weight_adjustments
CREATE POLICY "Users view own weights"
ON matching_weight_adjustments FOR SELECT TO authenticated
USING (auth.uid() = user_id);

CREATE POLICY "Service role manages weights"
ON matching_weight_adjustments FOR ALL TO service_role
USING (true) WITH CHECK (true);
