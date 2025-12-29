-- Migration: Feedback System
-- Features: Match outcomes, Secret profile verification, Trust scores

-- ==========================================
-- Match Outcomes Table
-- Track what happens after matching
-- ==========================================
CREATE TABLE IF NOT EXISTS match_outcomes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id UUID NOT NULL,
    user_a_id UUID NOT NULL REFERENCES profiles(id),
    user_b_id UUID NOT NULL REFERENCES profiles(id),
    outcome VARCHAR(50) NOT NULL, -- dating, met, chatting, rejected, no_response
    reward FLOAT DEFAULT 0.0,
    days_active INTEGER DEFAULT 0,
    questions_asked_a TEXT[], -- Question IDs asked to user A
    questions_asked_b TEXT[], -- Question IDs asked to user B
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_match_outcomes_users ON match_outcomes(user_a_id, user_b_id);
CREATE INDEX idx_match_outcomes_outcome ON match_outcomes(outcome);

-- ==========================================
-- Secret Profile Reports Table
-- Anonymous reports about height/weight accuracy ONLY
-- IMPORTANT: reporter_id is NEVER exposed to reported user
-- 
-- App validates: face, age, job, income, education
-- User reports: height, weight (can't verify until meeting)
-- ==========================================
CREATE TABLE IF NOT EXISTS secret_profile_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reporter_id UUID NOT NULL REFERENCES profiles(id), -- WHO reported (kept secret!)
    reported_user_id UUID NOT NULL REFERENCES profiles(id), -- WHO was reported
    field VARCHAR(10) NOT NULL CHECK (field IN ('height', 'weight')), -- ONLY these two
    status VARCHAR(20) NOT NULL CHECK (status IN ('accurate', 'inaccurate')),
    difference_level VARCHAR(20) CHECK (difference_level IN ('slight', 'moderate', 'significant')),
    -- slight: 3cm/3kg 이하, moderate: 3-7cm/kg, significant: 7+ cm/kg
    actual_value TEXT, -- What reporter observed (e.g., "170cm 정도", "70kg 정도")
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for finding reports about a user (but NOT who reported)
CREATE INDEX idx_reports_reported_user ON secret_profile_reports(reported_user_id);
CREATE INDEX idx_reports_field ON secret_profile_reports(field);

-- RLS Policy: Users can NEVER see who reported them
ALTER TABLE secret_profile_reports ENABLE ROW LEVEL SECURITY;

-- Only system can read reports (not users)
CREATE POLICY "reports_system_only" ON secret_profile_reports
    FOR SELECT
    TO authenticated
    USING (false); -- Users cannot query this table directly

-- Users can insert reports (but can't see others' reports)
CREATE POLICY "reports_insert" ON secret_profile_reports
    FOR INSERT
    TO authenticated
    WITH CHECK (reporter_id = auth.uid());

-- ==========================================
-- User Trust Profiles Table
-- Track user credibility and verification status
-- ==========================================
CREATE TABLE IF NOT EXISTS user_trust_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE NOT NULL REFERENCES profiles(id),
    trust_score FLOAT DEFAULT 100.0, -- 0-100
    total_reports_received INTEGER DEFAULT 0,
    accurate_reports INTEGER DEFAULT 0,
    inaccurate_reports INTEGER DEFAULT 0,
    flagged_fields JSONB DEFAULT '{}', -- {"height": 2, "weight": 1}
    is_blocked BOOLEAN DEFAULT false,
    blocked_until TIMESTAMPTZ,
    blocked_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_trust_user ON user_trust_profiles(user_id);
CREATE INDEX idx_trust_blocked ON user_trust_profiles(is_blocked);

-- ==========================================
-- A/B Test Experiments Table
-- ==========================================
CREATE TABLE IF NOT EXISTS ab_experiments (
    id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'draft', -- draft, running, paused, completed
    variants JSONB NOT NULL, -- [{id, name, config, weight}]
    user_percentage FLOAT DEFAULT 100.0,
    target_segments TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ
);

-- ==========================================
-- A/B Test User Assignments
-- Track which variant each user is in
-- ==========================================
CREATE TABLE IF NOT EXISTS ab_user_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id),
    experiment_id VARCHAR(100) NOT NULL REFERENCES ab_experiments(id),
    variant_id VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, experiment_id)
);

CREATE INDEX idx_ab_assignments_user ON ab_user_assignments(user_id);
CREATE INDEX idx_ab_assignments_experiment ON ab_user_assignments(experiment_id);

-- ==========================================
-- A/B Test Conversions
-- Track conversions per user per experiment
-- ==========================================
CREATE TABLE IF NOT EXISTS ab_conversions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id),
    experiment_id VARCHAR(100) NOT NULL REFERENCES ab_experiments(id),
    variant_id VARCHAR(100) NOT NULL,
    metric_name VARCHAR(100) NOT NULL, -- profile_completion, match_success, etc.
    metric_value FLOAT DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ab_conversions_experiment ON ab_conversions(experiment_id, variant_id);

-- ==========================================
-- Functions
-- ==========================================

-- Function to check if user is blocked
CREATE OR REPLACE FUNCTION check_user_blocked(p_user_id UUID)
RETURNS TABLE (
    is_blocked BOOLEAN,
    blocked_until TIMESTAMPTZ,
    blocked_reason TEXT,
    flagged_fields JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        utp.is_blocked,
        utp.blocked_until,
        utp.blocked_reason,
        utp.flagged_fields
    FROM user_trust_profiles utp
    WHERE utp.user_id = p_user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get user trust score
CREATE OR REPLACE FUNCTION get_user_trust_score(p_user_id UUID)
RETURNS FLOAT AS $$
DECLARE
    score FLOAT;
BEGIN
    SELECT trust_score INTO score
    FROM user_trust_profiles
    WHERE user_id = p_user_id;
    
    RETURN COALESCE(score, 100.0);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to filter matches by trust score
CREATE OR REPLACE FUNCTION filter_matches_by_trust(
    p_user_id UUID,
    p_min_trust_score FLOAT DEFAULT 50.0
)
RETURNS SETOF profiles AS $$
BEGIN
    RETURN QUERY
    SELECT p.*
    FROM profiles p
    LEFT JOIN user_trust_profiles utp ON p.id = utp.user_id
    WHERE p.id != p_user_id
      AND (utp.is_blocked IS NULL OR utp.is_blocked = false)
      AND (utp.trust_score IS NULL OR utp.trust_score >= p_min_trust_score);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ==========================================
-- Trigger: Auto-update timestamps
-- ==========================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_match_outcomes_updated_at
    BEFORE UPDATE ON match_outcomes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_trust_profiles_updated_at
    BEFORE UPDATE ON user_trust_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- ==========================================
-- Default A/B Experiments
-- ==========================================
INSERT INTO ab_experiments (id, name, description, status, variants) VALUES
(
    'question_order_v1',
    'Question Category Order',
    'Test which category to ask first for better completion',
    'draft',
    '[
        {"id": "marriage_first", "name": "결혼관 먼저", "config": {"first_category": "결혼관"}, "weight": 1.0},
        {"id": "lifestyle_first", "name": "라이프스타일 먼저", "config": {"first_category": "라이프스타일"}, "weight": 1.0}
    ]'::jsonb
),
(
    'avatar_tone_v1',
    'Avatar Personality',
    'Test friendly vs professional avatar tone',
    'draft',
    '[
        {"id": "friendly", "name": "친근한 톤", "config": {"tone": "friendly", "emoji": true}, "weight": 1.0},
        {"id": "professional", "name": "전문적인 톤", "config": {"tone": "professional", "emoji": false}, "weight": 1.0}
    ]'::jsonb
)
ON CONFLICT (id) DO NOTHING;
