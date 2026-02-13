-- ==========================================
-- FLIO Trust Score and Reputation System
-- ==========================================
-- Migration: 005_trust_and_reputation.sql
-- Description: Comprehensive trust scoring system with 7 components and behavioral tracking
-- Dependencies: 001_profiles.sql, 002_verification_system.sql
-- Components:
--   - Behavioral tracking (behavior logs, reports, interactions, analytics)
--   - Trust score calculation (7-component scoring algorithm)
--   - Tier system (diamond, coral, pearl, shell, pebble)
--   - Weighted matching algorithm
-- Version: 2.0 (2026 Edition)
-- ==========================================

-- ==========================================
-- PART 1: TIER SYSTEM CONFIGURATION
-- ==========================================

-- Tier calculation function
-- Converts raw trust score (0.0-1.0) to ocean-themed tier name
CREATE OR REPLACE FUNCTION calculate_tier_from_score(score DECIMAL)
RETURNS TEXT AS $$
BEGIN
  -- 5-tier system: Diamond/Coral/Pearl/Shell/Pebble
  IF score >= 0.80 THEN RETURN 'diamond';    -- 80-100%: ₩59,900/month, 30 matches/day + Priority
  ELSIF score >= 0.60 THEN RETURN 'coral';    -- 60-79%:  ₩39,900/month, 20 matches/day
  ELSIF score >= 0.40 THEN RETURN 'pearl';    -- 40-59%:  ₩19,900/month, 15 matches/day
  ELSIF score >= 0.20 THEN RETURN 'shell';    -- 20-39%:  ₩9,900/month,  10 matches/day
  ELSE RETURN 'pebble';                       -- 0-19%:   Free,         5 matches/day
  END IF;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Default tier preferences (who each tier can match with)
-- Lower tiers can only match with same or lower tiers
CREATE OR REPLACE FUNCTION get_default_tier_preferences(current_tier TEXT)
RETURNS TEXT[] AS $$
BEGIN
  CASE current_tier
    WHEN 'diamond' THEN RETURN ARRAY['diamond', 'coral', 'pearl', 'shell', 'pebble'];
    WHEN 'coral' THEN RETURN ARRAY['coral', 'pearl', 'shell', 'pebble'];
    WHEN 'pearl' THEN RETURN ARRAY['pearl', 'shell', 'pebble'];
    WHEN 'shell' THEN RETURN ARRAY['shell', 'pebble'];
    ELSE RETURN ARRAY['pebble']; -- pebble can only match pebble
  END CASE;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ==========================================
-- PART 2: BEHAVIORAL AND REPUTATION TABLES
-- ==========================================

-- User Trust Scores Table
-- Stores calculated trust score components and tier assignment
CREATE TABLE IF NOT EXISTS user_trust_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Component scores (0.0 - 1.0)
    document_score FLOAT DEFAULT 0.0 CHECK (document_score >= 0.0 AND document_score <= 1.0),
    photo_score FLOAT DEFAULT 0.0 CHECK (photo_score >= 0.0 AND photo_score <= 1.0),
    consistency_score FLOAT DEFAULT 0.3 CHECK (consistency_score >= 0.0 AND consistency_score <= 1.0),
    behavioral_score FLOAT DEFAULT 0.5 CHECK (behavioral_score >= 0.0 AND behavioral_score <= 1.0),
    social_score FLOAT DEFAULT 0.0 CHECK (social_score >= 0.0 AND social_score <= 1.0),
    completeness_score FLOAT DEFAULT 0.0 CHECK (completeness_score >= 0.0 AND completeness_score <= 1.0),
    reputation_score FLOAT DEFAULT 1.0 CHECK (reputation_score >= 0.0 AND reputation_score <= 1.0),

    -- Total score and tier
    total_trust_score FLOAT DEFAULT 0.0 CHECK (total_trust_score >= 0.0 AND total_trust_score <= 1.0),
    trust_tier VARCHAR(20) DEFAULT 'pebble' CHECK (trust_tier IN ('diamond', 'coral', 'pearl', 'shell', 'pebble')),

    -- Metadata
    last_calculated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- User Behavior Logs
-- Tracks all user actions for behavioral scoring and security monitoring
CREATE TABLE IF NOT EXISTS user_behavior_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Event classification
    event_type VARCHAR(50) NOT NULL,
    event_category VARCHAR(30) DEFAULT 'general' CHECK (event_category IN ('general', 'security', 'engagement', 'verification', 'moderation', 'payment')),
    event_data JSONB DEFAULT '{}'::jsonb,

    -- Change tracking
    field_changed VARCHAR(100),
    old_value TEXT,
    new_value TEXT,

    -- Risk assessment
    risk_level VARCHAR(20) DEFAULT 'low' CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
    risk_reason TEXT,

    -- Engagement metrics (for trust score behavioral component)
    engagement_quality FLOAT CHECK (engagement_quality IS NULL OR (engagement_quality >= 0.0 AND engagement_quality <= 1.0)),
    response_time_seconds INTEGER CHECK (response_time_seconds IS NULL OR response_time_seconds >= 0),
    message_length INTEGER CHECK (message_length IS NULL OR message_length >= 0),

    -- Session context
    session_id VARCHAR(100),
    ip_address INET,
    user_agent TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- User Reports
-- Tracks user-generated reports of misconduct or abuse
CREATE TABLE IF NOT EXISTS user_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reporter_user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    reported_user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Report details
    report_type VARCHAR(50) NOT NULL CHECK (report_type IN ('harassment', 'scam', 'fake_profile', 'ghosting', 'inappropriate_content', 'catfishing', 'spam', 'other')),
    report_reason TEXT,
    evidence_data JSONB DEFAULT '{}'::jsonb,

    -- Status tracking
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'investigating', 'confirmed', 'dismissed', 'resolved')),
    severity_level INTEGER DEFAULT 1 CHECK (severity_level >= 1 AND severity_level <= 5),

    -- Resolution
    reviewed_by UUID REFERENCES auth.users(id),
    reviewed_at TIMESTAMPTZ,
    resolution_notes TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Prevent duplicate reports
    CONSTRAINT unique_active_report UNIQUE (reporter_user_id, reported_user_id, report_type, status)
);

-- User Interactions
-- Tracks user-to-user interactions for behavioral analysis
CREATE TABLE IF NOT EXISTS user_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    target_user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Interaction details
    interaction_type VARCHAR(30) NOT NULL CHECK (interaction_type IN ('like', 'pass', 'super_like', 'message_sent', 'message_read', 'blocked', 'unblocked', 'reported', 'profile_view')),
    interaction_data JSONB DEFAULT '{}'::jsonb,

    -- Response metrics
    response_time_seconds INTEGER CHECK (response_time_seconds IS NULL OR response_time_seconds >= 0),

    -- Flags
    blocked BOOLEAN DEFAULT false,
    ghosted BOOLEAN DEFAULT false,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Conversation Analytics
-- Tracks conversation quality and outcomes for reputation scoring
CREATE TABLE IF NOT EXISTS conversation_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Message metrics
    total_messages INTEGER DEFAULT 0 CHECK (total_messages >= 0),
    user_messages_sent INTEGER DEFAULT 0 CHECK (user_messages_sent >= 0),
    avg_response_time_hours FLOAT CHECK (avg_response_time_hours IS NULL OR avg_response_time_hours >= 0),
    avg_message_length INTEGER CHECK (avg_message_length IS NULL OR avg_message_length >= 0),

    -- Conversation outcome
    end_reason VARCHAR(50) CHECK (end_reason IS NULL OR end_reason IN ('mutual', 'ghosting', 'unmatched', 'blocked', 'met_in_person', 'started_relationship', 'not_compatible', 'no_response', 'conversation_ongoing')),
    ghosting_pattern BOOLEAN DEFAULT false, -- >10 messages then no response for 7+ days
    positive_outcome BOOLEAN DEFAULT false, -- met_in_person or started_relationship

    -- Duration
    conversation_duration_hours INTEGER CHECK (conversation_duration_hours IS NULL OR conversation_duration_hours >= 0),

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(conversation_id, user_id)
);

-- ==========================================
-- PART 3: INDEXES
-- ==========================================

-- Trust Scores Indexes
CREATE INDEX IF NOT EXISTS idx_trust_scores_user ON user_trust_scores(user_id);
CREATE INDEX IF NOT EXISTS idx_trust_scores_tier ON user_trust_scores(trust_tier);
CREATE INDEX IF NOT EXISTS idx_trust_scores_total ON user_trust_scores(total_trust_score DESC);
CREATE INDEX IF NOT EXISTS idx_trust_scores_calculated ON user_trust_scores(last_calculated_at DESC);

-- Behavior Logs Indexes
CREATE INDEX IF NOT EXISTS idx_behavior_logs_user ON user_behavior_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_behavior_logs_type ON user_behavior_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_behavior_logs_category ON user_behavior_logs(event_category);
CREATE INDEX IF NOT EXISTS idx_behavior_logs_risk ON user_behavior_logs(risk_level);
CREATE INDEX IF NOT EXISTS idx_behavior_logs_user_time ON user_behavior_logs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_behavior_logs_event_data ON user_behavior_logs USING GIN(event_data);

-- User Reports Indexes
CREATE INDEX IF NOT EXISTS idx_reports_reporter ON user_reports(reporter_user_id);
CREATE INDEX IF NOT EXISTS idx_reports_reported ON user_reports(reported_user_id);
CREATE INDEX IF NOT EXISTS idx_reports_status ON user_reports(status);
CREATE INDEX IF NOT EXISTS idx_reports_type ON user_reports(report_type);
CREATE INDEX IF NOT EXISTS idx_reports_severity ON user_reports(severity_level DESC);
CREATE INDEX IF NOT EXISTS idx_reports_created ON user_reports(created_at DESC);

-- User Interactions Indexes
CREATE INDEX IF NOT EXISTS idx_interactions_user ON user_interactions(user_id);
CREATE INDEX IF NOT EXISTS idx_interactions_target ON user_interactions(target_user_id);
CREATE INDEX IF NOT EXISTS idx_interactions_type ON user_interactions(interaction_type);
CREATE INDEX IF NOT EXISTS idx_interactions_user_time ON user_interactions(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_interactions_data ON user_interactions USING GIN(interaction_data);

-- Conversation Analytics Indexes
CREATE INDEX IF NOT EXISTS idx_conv_analytics_user ON conversation_analytics(user_id);
CREATE INDEX IF NOT EXISTS idx_conv_analytics_conversation ON conversation_analytics(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conv_analytics_outcome ON conversation_analytics(end_reason);
CREATE INDEX IF NOT EXISTS idx_conv_analytics_ghosting ON conversation_analytics(ghosting_pattern) WHERE ghosting_pattern = true;
CREATE INDEX IF NOT EXISTS idx_conv_analytics_positive ON conversation_analytics(positive_outcome) WHERE positive_outcome = true;

-- Profile Tier Indexes (for matching queries)
CREATE INDEX IF NOT EXISTS idx_profiles_trust_tier ON profiles(trust_tier);
CREATE INDEX IF NOT EXISTS idx_profiles_tier_preferences ON profiles USING GIN(tier_preferences);

-- ==========================================
-- PART 4: TRUST SCORE CALCULATION FUNCTIONS
-- ==========================================

-- Component 1: Photo Verification Score (20% weight)
-- Evaluates photo verification quality and freshness
CREATE OR REPLACE FUNCTION calculate_photo_verification_score(p_user_id UUID)
RETURNS FLOAT AS $$
DECLARE
    v_verified_at TIMESTAMPTZ;
    v_verification_score FLOAT;
    v_expires_at TIMESTAMPTZ;
BEGIN
    SELECT verified_at, verification_score, expires_at
    INTO v_verified_at, v_verification_score, v_expires_at
    FROM photo_verifications
    WHERE user_id = p_user_id AND verification_status = 'verified'
    ORDER BY verified_at DESC LIMIT 1;

    -- If not verified, return 0 (user is BLOCKED from matches anyway)
    IF v_verified_at IS NULL THEN
        RETURN 0.0;
    END IF;

    -- Score based on quality and freshness
    RETURN CASE
        WHEN v_expires_at > NOW() AND v_verification_score >= 0.90 THEN 1.0  -- Recent + high quality
        WHEN v_expires_at > NOW() AND v_verification_score >= 0.75 THEN 0.8  -- Recent + good quality
        WHEN v_expires_at <= NOW() THEN 0.5  -- Expired - needs re-verification
        ELSE 0.6
    END;
END;
$$ LANGUAGE plpgsql STABLE;

-- Helper: Check if user can access matches (PHOTO REQUIRED)
CREATE OR REPLACE FUNCTION can_user_access_matches(p_user_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    v_photo_verified BOOLEAN;
    v_expires_at TIMESTAMPTZ;
BEGIN
    SELECT photo_verified, photo_verified_at + INTERVAL '6 months'
    INTO v_photo_verified, v_expires_at
    FROM profiles
    WHERE user_id = p_user_id;

    -- Must have valid photo verification
    IF v_photo_verified AND v_expires_at > NOW() THEN
        RETURN true;
    END IF;

    RETURN false;
END;
$$ LANGUAGE plpgsql STABLE;

-- Component 2: Social Verification Score (10% weight)
-- Evaluates linked social media accounts and their credibility
CREATE OR REPLACE FUNCTION calculate_social_verification_score(p_user_id UUID)
RETURNS FLOAT AS $$
DECLARE v_score FLOAT := 0.0;
BEGIN
    SELECT COALESCE(
        (COUNT(*) FILTER (WHERE platform = 'linkedin') * 0.40) +
        (COUNT(*) FILTER (WHERE platform = 'instagram') * 0.30) +
        (COUNT(*) FILTER (WHERE platform = 'kakao') * 0.20) +
        (COUNT(*) FILTER (WHERE platform = 'naver') * 0.10) +
        -- Bonuses
        (COUNT(*) FILTER (WHERE platform = 'linkedin' AND account_age_days > 730) * 0.10) +
        (COUNT(*) FILTER (WHERE platform = 'instagram' AND follower_count > 500) * 0.05) +
        (COUNT(*) FILTER (WHERE is_verified_account = true) * 0.15),
        0.0
    ) INTO v_score
    FROM social_verifications
    WHERE user_id = p_user_id AND verification_status = 'verified';

    RETURN LEAST(v_score, 1.0);
END;
$$ LANGUAGE plpgsql STABLE;

-- Component 3: Behavioral Score (15% weight)
-- Evaluates account age, response rate, and negative behaviors
CREATE OR REPLACE FUNCTION calculate_behavioral_score(p_user_id UUID)
RETURNS FLOAT AS $$
DECLARE
    v_base_score FLOAT := 0.5;  -- Start at 0.5, build up with account age
    v_response_rate FLOAT;
    v_report_count INTEGER;
    v_ghosting_count INTEGER;
    v_account_age_days INTEGER := 0;
BEGIN
    -- Account age bonus
    SELECT EXTRACT(DAY FROM NOW() - created_at)::INTEGER INTO v_account_age_days
    FROM profiles WHERE user_id = p_user_id;

    v_account_age_days := COALESCE(v_account_age_days, 0);

    -- Build up score with account age
    IF v_account_age_days >= 180 THEN
        v_base_score := v_base_score + 0.30;  -- 6+ months: 0.80
    ELSIF v_account_age_days >= 90 THEN
        v_base_score := v_base_score + 0.20;  -- 3+ months: 0.70
    ELSIF v_account_age_days >= 30 THEN
        v_base_score := v_base_score + 0.10;  -- 1+ month: 0.60
    ELSIF v_account_age_days >= 7 THEN
        v_base_score := v_base_score + 0.05;  -- 1+ week: 0.55
    END IF;

    -- Message response rate (>80% within 24h = +0.10)
    SELECT COALESCE(
        COUNT(*) FILTER (WHERE response_time_seconds < 86400)::FLOAT /
        NULLIF(COUNT(*), 0), 0.0
    ) INTO v_response_rate
    FROM user_interactions
    WHERE user_id = p_user_id AND interaction_type = 'message_sent'
    AND created_at > NOW() - INTERVAL '30 days';

    -- Reports against user (penalty)
    SELECT COUNT(*) INTO v_report_count
    FROM user_reports
    WHERE reported_user_id = p_user_id AND status IN ('confirmed', 'investigating')
    AND created_at > NOW() - INTERVAL '90 days';

    -- Ghosting pattern (penalty)
    SELECT COUNT(*) INTO v_ghosting_count
    FROM conversation_analytics
    WHERE user_id = p_user_id AND ghosting_pattern = true
    AND created_at > NOW() - INTERVAL '90 days';

    v_base_score := v_base_score
        + (CASE WHEN v_response_rate > 0.8 THEN 0.10 ELSE 0.0 END)
        - (v_report_count * 0.10)
        - (v_ghosting_count * 0.05);

    -- Apply penalties from behavior logs
    v_base_score := v_base_score - COALESCE(
        (SELECT SUM(
            CASE risk_level
                WHEN 'critical' THEN 0.25
                WHEN 'high' THEN 0.15
                WHEN 'medium' THEN 0.05
                ELSE 0.01
            END
        ) FROM user_behavior_logs
        WHERE user_id = p_user_id AND created_at > NOW() - INTERVAL '30 days'),
        0.0
    );

    RETURN LEAST(GREATEST(v_base_score, 0.0), 1.0);
END;
$$ LANGUAGE plpgsql STABLE;

-- Component 4: Reputation Score (5% weight)
-- Evaluates user reputation based on reports and conversation outcomes
CREATE OR REPLACE FUNCTION calculate_reputation_score(p_user_id UUID)
RETURNS FLOAT AS $$
DECLARE
    v_score FLOAT := 1.0;
    v_confirmed_reports INTEGER;
    v_ghosting_rate FLOAT;
    v_positive_rate FLOAT;
BEGIN
    -- Confirmed reports (severe penalty: -0.20 each)
    SELECT COUNT(*) INTO v_confirmed_reports
    FROM user_reports
    WHERE reported_user_id = p_user_id AND status = 'confirmed'
    AND created_at > NOW() - INTERVAL '180 days';

    -- Ghosting rate
    SELECT COALESCE(
        COUNT(*) FILTER (WHERE ghosting_pattern = true)::FLOAT / NULLIF(COUNT(*), 0), 0.0
    ) INTO v_ghosting_rate
    FROM conversation_analytics
    WHERE user_id = p_user_id AND total_messages >= 10;

    -- Positive outcomes (bonus: +0.10)
    SELECT COALESCE(
        COUNT(*) FILTER (WHERE positive_outcome = true)::FLOAT / NULLIF(COUNT(*), 0), 0.0
    ) INTO v_positive_rate
    FROM conversation_analytics
    WHERE user_id = p_user_id;

    v_score := v_score
        - (v_confirmed_reports * 0.20)
        - (v_ghosting_rate * 0.10)
        + (v_positive_rate * 0.10);

    RETURN LEAST(GREATEST(v_score, 0.0), 1.0);
END;
$$ LANGUAGE plpgsql STABLE;

-- Main: Calculate Complete Trust Score (7 Components)
-- Combines all component scores with weighted algorithm
CREATE OR REPLACE FUNCTION calculate_trust_score(p_user_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_document_score FLOAT := 0.0;
    v_photo_score FLOAT := 0.0;
    v_consistency_score FLOAT := 0.3;  -- Start low, build up with answers
    v_behavioral_score FLOAT := 0.5;   -- Start at base, build up with time
    v_social_score FLOAT := 0.0;
    v_completeness_score FLOAT := 0.0;
    v_reputation_score FLOAT := 1.0;
    v_total_score FLOAT := 0.0;
    v_trust_tier VARCHAR(20);
    v_answer_count INTEGER := 0;
    v_unresolved_contradictions INTEGER := 0;
BEGIN
    -- 1. Document Score (25%)
    SELECT COALESCE(AVG(match_score), 0.0) INTO v_document_score
    FROM user_documents WHERE user_id = p_user_id AND verification_status = 'verified';

    -- 2. Photo Score (20%) - REQUIRED but still contributes to score quality
    v_photo_score := calculate_photo_verification_score(p_user_id);

    -- 3. Consistency Score (15%) - Build up gradually with answers
    SELECT COUNT(*) INTO v_answer_count
    FROM user_answers WHERE user_id = p_user_id;

    SELECT COUNT(*) INTO v_unresolved_contradictions
    FROM consistency_checks WHERE user_id = p_user_id AND NOT is_resolved;

    IF v_answer_count < 10 THEN
        -- New users with < 10 answers: gradually increase from 0.3 to 0.6
        v_consistency_score := 0.3 + (v_answer_count::FLOAT / 10.0) * 0.3;
    ELSIF v_unresolved_contradictions = 0 THEN
        -- Users with enough answers and no contradictions
        IF v_answer_count >= 30 THEN
            v_consistency_score := 1.0;
        ELSIF v_answer_count >= 20 THEN
            v_consistency_score := 0.9;
        ELSE
            v_consistency_score := 0.8;
        END IF;
    ELSE
        -- Has contradictions - use contradiction-based formula
        SELECT COALESCE(1.0 - AVG(contradiction_score), 0.5) INTO v_consistency_score
        FROM consistency_checks WHERE user_id = p_user_id AND NOT is_resolved;
    END IF;

    -- 4. Behavioral Score (15%)
    v_behavioral_score := calculate_behavioral_score(p_user_id);

    -- 5. Social Score (10%)
    v_social_score := calculate_social_verification_score(p_user_id);

    -- 6. Completeness Score (10%)
    SELECT (
        (CASE WHEN real_name IS NOT NULL THEN 0.05 ELSE 0 END) +
        (CASE WHEN height_cm IS NOT NULL THEN 0.03 ELSE 0 END) +
        (CASE WHEN education_level IS NOT NULL THEN 0.05 ELSE 0 END) +
        (CASE WHEN employment_status IS NOT NULL THEN 0.05 ELSE 0 END) +
        (CASE WHEN annual_income_range IS NOT NULL THEN 0.05 ELSE 0 END) +
        0.40 * LEAST((SELECT COUNT(*) FROM user_answers WHERE user_answers.user_id = p_user_id)::FLOAT / get_active_question_count()::FLOAT, 1.0) +
        0.10 * (CASE WHEN EXISTS(SELECT 1 FROM user_family_background WHERE user_family_background.user_id = p_user_id) THEN 1 ELSE 0 END)
    ) INTO v_completeness_score
    FROM profiles WHERE profiles.user_id = p_user_id;

    v_completeness_score := COALESCE(v_completeness_score, 0.0);

    -- 7. Reputation Score (5%)
    v_reputation_score := calculate_reputation_score(p_user_id);

    -- Calculate total score (7 components)
    v_total_score := (v_document_score * 0.25) + (v_photo_score * 0.20) + (v_consistency_score * 0.15) +
                     (v_behavioral_score * 0.15) + (v_social_score * 0.10) + (v_completeness_score * 0.10) +
                     (v_reputation_score * 0.05);

    v_total_score := LEAST(GREATEST(v_total_score, 0.0), 1.0);
    v_trust_tier := calculate_tier_from_score(v_total_score);

    -- Upsert trust score
    INSERT INTO user_trust_scores (
        user_id, document_score, photo_score, consistency_score, behavioral_score,
        social_score, completeness_score, reputation_score,
        total_trust_score, trust_tier, last_calculated_at, updated_at
    )
    VALUES (
        p_user_id, v_document_score, v_photo_score, v_consistency_score, v_behavioral_score,
        v_social_score, v_completeness_score, v_reputation_score,
        v_total_score, v_trust_tier, NOW(), NOW()
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
        last_calculated_at = NOW(),
        updated_at = NOW();

    -- Update profile with tier and match limits
    UPDATE profiles
    SET trust_tier = v_trust_tier,
        tier_preferences = COALESCE(tier_preferences, get_default_tier_preferences(v_trust_tier)),
        daily_match_limit = CASE v_trust_tier
            WHEN 'diamond' THEN 30
            WHEN 'coral' THEN 20
            WHEN 'pearl' THEN 15
            WHEN 'shell' THEN 10
            ELSE 5
        END
    WHERE profiles.user_id = p_user_id;

    RETURN jsonb_build_object(
        'version', '2.0',
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
        'calculated_at', NOW()
    );
END;
$$;

-- ==========================================
-- PART 5: TIER-BASED MATCHING FUNCTIONS
-- ==========================================

-- Helper: Calculate weighted answer alignment between two users
CREATE OR REPLACE FUNCTION calculate_weighted_answer_alignment(
    p_user_a UUID,
    p_user_b UUID
)
RETURNS DECIMAL AS $$
DECLARE v_alignment DECIMAL;
BEGIN
    WITH aligned_questions AS (
        SELECT
            a.question_id,
            (a.base_weight * (1.0 + a.importance::FLOAT / 5.0) * (a.effectiveness_score / 10.0)) AS question_weight,
            CASE
                WHEN (a.is_dealbreaker OR b.is_dealbreaker) AND a.answer_value != b.answer_value THEN 0.0
                WHEN a.answer_value = b.answer_value THEN 1.0
                ELSE 0.0
            END AS alignment
        FROM user_answers a
        JOIN questions q ON q.id = a.question_id
        JOIN user_answers b ON b.question_id = a.question_id
        WHERE a.user_id = p_user_a AND b.user_id = p_user_b
    )
    SELECT COALESCE(
        SUM(question_weight * alignment) / NULLIF(SUM(question_weight), 0), 0.0
    ) INTO v_alignment
    FROM aligned_questions;

    RETURN v_alignment;
END;
$$ LANGUAGE plpgsql STABLE;

-- Main: Find matches using hybrid algorithm (embeddings + weighted answers)
CREATE OR REPLACE FUNCTION find_matches(
    p_user_id UUID,
    p_limit INTEGER DEFAULT 10,
    p_min_compatibility DECIMAL DEFAULT 0.40
)
RETURNS TABLE (
    match_user_id UUID,
    compatibility_score DECIMAL,
    embedding_similarity DECIMAL,
    answer_alignment DECIMAL,
    trust_compatibility DECIMAL
) AS $$
DECLARE
    v_user_embedding VECTOR(512);
    v_user_gender TEXT;
    v_user_tier TEXT;
    v_allowed_tiers TEXT[];
    v_user_trust_score DECIMAL;
    v_user_photo_verified BOOLEAN;
BEGIN
    -- Get user data + check photo verification
    SELECT profile_embedding, gender, trust_tier, tier_preferences, photo_verified,
           COALESCE((SELECT total_trust_score FROM user_trust_scores WHERE user_id = p_user_id), 0.0)
    INTO v_user_embedding, v_user_gender, v_user_tier, v_allowed_tiers, v_user_photo_verified, v_user_trust_score
    FROM profiles WHERE user_id = p_user_id;

    -- REQUIRE PHOTO VERIFICATION
    IF NOT v_user_photo_verified THEN
        RAISE EXCEPTION 'Photo verification required to access matches';
    END IF;

    IF v_allowed_tiers IS NULL THEN
        v_allowed_tiers := get_default_tier_preferences(v_user_tier);
    END IF;

    IF v_user_tier = 'pebble' THEN
        v_allowed_tiers := ARRAY['pebble'];
    END IF;

    RETURN QUERY
    WITH candidates AS (
        SELECT
            p.user_id,
            (1 - (v_user_embedding <=> p.profile_embedding))::DECIMAL AS embedding_sim,
            COALESCE((SELECT total_trust_score FROM user_trust_scores WHERE user_id = p.user_id), 0.0) AS trust_score
        FROM profiles p
        WHERE p.user_id != p_user_id
          AND p.gender != v_user_gender
          AND p.profile_embedding IS NOT NULL
          AND p.trust_tier = ANY(v_allowed_tiers)
          AND p.photo_verified = true  -- ONLY SHOW PHOTO VERIFIED USERS
          AND (1 - (v_user_embedding <=> p.profile_embedding)) >= 0.3
        ORDER BY v_user_embedding <=> p.profile_embedding
        LIMIT p_limit * 3
    ),
    scored AS (
        SELECT
            c.user_id,
            c.embedding_sim,
            calculate_weighted_answer_alignment(p_user_id, c.user_id) AS answer_align
        FROM candidates c
    )
    SELECT
        s.user_id,
        ((s.embedding_sim * 0.60) + (s.answer_align * 0.40))::DECIMAL,
        s.embedding_sim,
        s.answer_align,
        NULL::DECIMAL  -- trust_comp removed (matching within same tier already)
    FROM scored s
    WHERE ((s.embedding_sim * 0.60) + (s.answer_align * 0.40)) >= p_min_compatibility
    ORDER BY ((s.embedding_sim * 0.60) + (s.answer_align * 0.40)) DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql STABLE;

-- ==========================================
-- PART 6: TRIGGERS
-- ==========================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger: updated_at for user_trust_scores
DROP TRIGGER IF EXISTS trigger_user_trust_scores_updated_at ON user_trust_scores;
CREATE TRIGGER trigger_user_trust_scores_updated_at
    BEFORE UPDATE ON user_trust_scores
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger: updated_at for user_reports
DROP TRIGGER IF EXISTS trigger_user_reports_updated_at ON user_reports;
CREATE TRIGGER trigger_user_reports_updated_at
    BEFORE UPDATE ON user_reports
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger: updated_at for conversation_analytics
DROP TRIGGER IF EXISTS trigger_conversation_analytics_updated_at ON conversation_analytics;
CREATE TRIGGER trigger_conversation_analytics_updated_at
    BEFORE UPDATE ON conversation_analytics
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Sync trust tier to profile when trust score changes
CREATE OR REPLACE FUNCTION sync_profile_trust_tier()
RETURNS TRIGGER AS $$
DECLARE
  v_new_tier TEXT;
BEGIN
  -- Calculate new tier from total_trust_score
  v_new_tier := calculate_tier_from_score(NEW.total_trust_score);

  -- Update profiles table
  UPDATE profiles
  SET trust_tier = v_new_tier,
      tier_preferences = COALESCE(tier_preferences, get_default_tier_preferences(v_new_tier))
  WHERE user_id = NEW.user_id;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_sync_profile_trust_tier ON user_trust_scores;
CREATE TRIGGER trigger_sync_profile_trust_tier
  AFTER INSERT OR UPDATE OF total_trust_score
  ON user_trust_scores
  FOR EACH ROW
  EXECUTE FUNCTION sync_profile_trust_tier();

-- Auto-update photo_verified flag when photo verification completes
CREATE OR REPLACE FUNCTION update_profile_photo_verified()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.verification_status = 'verified' THEN
        UPDATE profiles
        SET photo_verified = true,
            photo_verified_at = NEW.verified_at
        WHERE user_id = NEW.user_id;

        -- Recalculate trust score
        PERFORM calculate_trust_score(NEW.user_id);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_photo_verified ON photo_verifications;
CREATE TRIGGER trigger_update_photo_verified
    AFTER INSERT OR UPDATE ON photo_verifications
    FOR EACH ROW
    EXECUTE FUNCTION update_profile_photo_verified();

-- ==========================================
-- PART 7: ROW LEVEL SECURITY (RLS)
-- ==========================================

-- Enable RLS on all tables
ALTER TABLE user_trust_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_behavior_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_interactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_analytics ENABLE ROW LEVEL SECURITY;

-- user_trust_scores policies
CREATE POLICY "Users can view own trust scores"
    ON user_trust_scores FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Service can manage trust scores"
    ON user_trust_scores FOR ALL
    USING (true);

-- user_behavior_logs policies
CREATE POLICY "Service can manage behavior logs"
    ON user_behavior_logs FOR ALL
    USING (true);

-- user_reports policies
CREATE POLICY "Users can create reports"
    ON user_reports FOR INSERT
    WITH CHECK (auth.uid() = reporter_user_id);

CREATE POLICY "Users can view their own reports"
    ON user_reports FOR SELECT
    USING (auth.uid() = reporter_user_id OR auth.uid() = reported_user_id);

CREATE POLICY "Service can manage reports"
    ON user_reports FOR ALL
    USING (true);

-- user_interactions policies
CREATE POLICY "Users can view own interactions"
    ON user_interactions FOR SELECT
    USING (auth.uid() = user_id OR auth.uid() = target_user_id);

CREATE POLICY "Users can create interactions"
    ON user_interactions FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Service can manage interactions"
    ON user_interactions FOR ALL
    USING (true);

-- conversation_analytics policies
CREATE POLICY "Users can view own conversation analytics"
    ON conversation_analytics FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Service can manage conversation analytics"
    ON conversation_analytics FOR ALL
    USING (true);

-- ==========================================
-- PART 8: GRANTS AND PERMISSIONS
-- ==========================================

-- Grant execute permissions on functions
GRANT EXECUTE ON FUNCTION calculate_tier_from_score TO authenticated, anon;
GRANT EXECUTE ON FUNCTION get_default_tier_preferences TO authenticated, anon;
GRANT EXECUTE ON FUNCTION calculate_photo_verification_score TO authenticated, anon;
GRANT EXECUTE ON FUNCTION can_user_access_matches TO authenticated, anon;
GRANT EXECUTE ON FUNCTION calculate_social_verification_score TO authenticated, anon;
GRANT EXECUTE ON FUNCTION calculate_behavioral_score TO authenticated, anon;
GRANT EXECUTE ON FUNCTION calculate_reputation_score TO authenticated, anon;
GRANT EXECUTE ON FUNCTION calculate_trust_score TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION calculate_weighted_answer_alignment TO authenticated, anon;
GRANT EXECUTE ON FUNCTION find_matches TO authenticated;

-- Grant table permissions
GRANT SELECT, INSERT, UPDATE ON user_trust_scores TO authenticated;
GRANT SELECT, INSERT ON user_behavior_logs TO authenticated;
GRANT SELECT, INSERT, UPDATE ON user_reports TO authenticated;
GRANT SELECT, INSERT, UPDATE ON user_interactions TO authenticated;
GRANT SELECT, INSERT, UPDATE ON conversation_analytics TO authenticated;

-- ==========================================
-- PART 9: DATA BACKFILL
-- ==========================================

-- Backfill tier_preferences for existing users
UPDATE profiles
SET tier_preferences = get_default_tier_preferences(COALESCE(trust_tier, 'pebble'))
WHERE tier_preferences IS NULL;

-- ==========================================
-- PART 10: COMMENTS AND DOCUMENTATION
-- ==========================================

-- Table comments
COMMENT ON TABLE user_trust_scores IS 'Stores calculated trust scores with 7 components: Document (25%), Photo (20%), Consistency (15%), Behavioral (15%), Social (10%), Completeness (10%), Reputation (5%)';
COMMENT ON TABLE user_behavior_logs IS 'Tracks user actions for behavioral scoring and security monitoring. Includes risk assessment and engagement metrics.';
COMMENT ON TABLE user_reports IS 'User-generated reports of misconduct or abuse. Used for reputation scoring and moderation.';
COMMENT ON TABLE user_interactions IS 'Tracks user-to-user interactions (likes, messages, blocks) for behavioral analysis.';
COMMENT ON TABLE conversation_analytics IS 'Analytics for conversation quality and outcomes. Tracks ghosting patterns and positive outcomes.';

-- Column comments
COMMENT ON COLUMN user_trust_scores.document_score IS 'Score from verified documents (25% weight)';
COMMENT ON COLUMN user_trust_scores.photo_score IS 'Score from photo verification quality and freshness (20% weight)';
COMMENT ON COLUMN user_trust_scores.consistency_score IS 'Score from answer consistency checks (15% weight)';
COMMENT ON COLUMN user_trust_scores.behavioral_score IS 'Score from user behavior patterns (15% weight)';
COMMENT ON COLUMN user_trust_scores.social_score IS 'Score from linked social media accounts (10% weight)';
COMMENT ON COLUMN user_trust_scores.completeness_score IS 'Score from profile completeness (10% weight)';
COMMENT ON COLUMN user_trust_scores.reputation_score IS 'Score from user reputation and reports (5% weight)';
COMMENT ON COLUMN user_trust_scores.total_trust_score IS 'Weighted sum of all component scores (0.0 - 1.0)';
COMMENT ON COLUMN user_trust_scores.trust_tier IS 'Calculated tier: diamond (80-100%), coral (60-79%), pearl (40-59%), shell (20-39%), pebble (0-19%)';

COMMENT ON COLUMN user_behavior_logs.event_category IS 'Event category: general, security, engagement, verification, moderation, payment';
COMMENT ON COLUMN user_behavior_logs.risk_level IS 'Risk level: low, medium, high, critical';
COMMENT ON COLUMN user_behavior_logs.event_data IS 'JSONB data for event-specific information';

COMMENT ON COLUMN user_reports.report_type IS 'Type of report: harassment, scam, fake_profile, ghosting, inappropriate_content, catfishing, spam, other';
COMMENT ON COLUMN user_reports.status IS 'Report status: pending, investigating, confirmed, dismissed, resolved';
COMMENT ON COLUMN user_reports.severity_level IS 'Severity level from 1 (low) to 5 (critical)';

COMMENT ON COLUMN user_interactions.interaction_type IS 'Type of interaction: like, pass, super_like, message_sent, message_read, blocked, unblocked, reported, profile_view';

COMMENT ON COLUMN conversation_analytics.end_reason IS 'Conversation end reason: mutual, ghosting, unmatched, blocked, met_in_person, started_relationship, not_compatible, no_response, conversation_ongoing';
COMMENT ON COLUMN conversation_analytics.ghosting_pattern IS 'True if user sent 10+ messages then stopped responding for 7+ days';
COMMENT ON COLUMN conversation_analytics.positive_outcome IS 'True if conversation led to meeting in person or starting a relationship';

COMMENT ON COLUMN profiles.tier_preferences IS 'Ocean Pearl Theme tiers user wants to match with: pebble(조약돌), shell(조개), pearl(진주), coral(산호), diamond(다이아)';
COMMENT ON COLUMN profiles.trust_tier IS 'Current tier based on trust score: pebble(0-19%), shell(20-39%), pearl(40-59%), coral(60-79%), diamond(80-100%)';

-- Function comments
COMMENT ON FUNCTION calculate_tier_from_score IS 'Converts trust score (0.0-1.0) to tier name: diamond, coral, pearl, shell, or pebble';
COMMENT ON FUNCTION get_default_tier_preferences IS 'Returns default tier preferences for a given trust tier. Lower tiers can only match with same or lower tiers.';
COMMENT ON FUNCTION calculate_photo_verification_score IS 'Calculates photo verification score (20% weight) based on quality and expiration';
COMMENT ON FUNCTION can_user_access_matches IS 'Checks if user has valid photo verification to access matches. Photo verification is REQUIRED.';
COMMENT ON FUNCTION calculate_social_verification_score IS 'Calculates social verification score (10% weight) from linked social media accounts';
COMMENT ON FUNCTION calculate_behavioral_score IS 'Calculates behavioral score (15% weight) from account age, response rate, reports, and ghosting';
COMMENT ON FUNCTION calculate_reputation_score IS 'Calculates reputation score (5% weight) from confirmed reports, ghosting rate, and positive outcomes';
COMMENT ON FUNCTION calculate_trust_score IS 'Calculates comprehensive trust score from 7 components: Document (25%), Photo (20%), Consistency (15%), Behavioral (15%), Social (10%), Completeness (10%), Reputation (5%)';
COMMENT ON FUNCTION calculate_weighted_answer_alignment IS 'Calculates weighted answer alignment between two users based on question weights and importance ratings';
COMMENT ON FUNCTION find_matches IS 'Hybrid matching algorithm: embeddings (60%) + weighted answers (40%) within tier-based pools. Requires photo verification.';

-- ==========================================
-- END OF MIGRATION
-- ==========================================
