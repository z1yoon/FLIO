-- ==========================================
-- FLIO Behavioral & Reputation Tracking Tables
-- ==========================================
-- Description: User behavior logs, reports, interactions, and conversation analytics
-- Consolidated from: 004_verification_system.sql (lines 247-284) + 005_trust_score_system.sql (lines 126-168)
-- ==========================================

-- ===================
-- USER BEHAVIOR LOGS
-- ===================

CREATE TABLE IF NOT EXISTS user_behavior_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    event_type VARCHAR(50) NOT NULL,
    event_category VARCHAR(30) DEFAULT 'general',
    event_data JSONB DEFAULT '{}'::jsonb,

    -- Change tracking
    field_changed VARCHAR(100),
    old_value TEXT,
    new_value TEXT,

    -- Risk assessment
    risk_level VARCHAR(20) DEFAULT 'low',
    risk_reason TEXT,

    -- Engagement metrics (for trust score behavioral component)
    engagement_quality FLOAT,
    response_time_seconds INTEGER,
    message_length INTEGER,

    -- Session context
    session_id VARCHAR(100),
    ip_address INET,
    user_agent TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_behavior_logs_user ON user_behavior_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_behavior_logs_type ON user_behavior_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_behavior_logs_risk ON user_behavior_logs(risk_level);
CREATE INDEX IF NOT EXISTS idx_behavior_logs_user_time ON user_behavior_logs(user_id, created_at DESC);

COMMENT ON TABLE user_behavior_logs IS 'Tracks user behavior for trust score calculation (scoring logic in migration 013)';

-- ===================
-- USER REPORTS
-- ===================

CREATE TABLE IF NOT EXISTS user_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reporter_user_id UUID NOT NULL REFERENCES auth.users(id),
    reported_user_id UUID NOT NULL REFERENCES auth.users(id),
    report_type VARCHAR(50) NOT NULL, -- harassment, scam, fake_profile, ghosting, etc.
    status VARCHAR(20) DEFAULT 'pending', -- pending, investigating, confirmed, dismissed
    severity_level INTEGER DEFAULT 1, -- 1 (low) to 5 (severe)
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reports_reported_user ON user_reports(reported_user_id);

-- ===================
-- USER INTERACTIONS
-- ===================

CREATE TABLE IF NOT EXISTS user_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    target_user_id UUID NOT NULL REFERENCES auth.users(id),
    interaction_type VARCHAR(30) NOT NULL, -- like, pass, message_sent, blocked, etc.
    response_time_seconds INTEGER,
    blocked BOOLEAN DEFAULT false,
    ghosted BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_interactions_user ON user_interactions(user_id);

-- ===================
-- CONVERSATION ANALYTICS
-- ===================

CREATE TABLE IF NOT EXISTS conversation_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL,
    user_id UUID NOT NULL REFERENCES auth.users(id),
    total_messages INTEGER DEFAULT 0,
    avg_response_time_hours FLOAT,
    end_reason VARCHAR(50), -- mutual, ghosting, met_in_person, started_relationship, etc.
    ghosting_pattern BOOLEAN DEFAULT false, -- >10 messages then no response for 7+ days
    positive_outcome BOOLEAN DEFAULT false, -- met_in_person or started_relationship
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(conversation_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_conv_analytics_user ON conversation_analytics(user_id);

-- ===================
-- ROW LEVEL SECURITY
-- ===================

ALTER TABLE user_behavior_logs ENABLE ROW LEVEL SECURITY;

-- Behavior logs (service-managed)
CREATE POLICY "Service can manage behavior logs"
    ON user_behavior_logs FOR ALL USING (true);

-- ===================
-- COMMENTS
-- ===================

COMMENT ON TABLE user_behavior_logs IS 'Logs user actions for behavioral scoring';
COMMENT ON TABLE user_reports IS 'User reports of misconduct or abuse';
COMMENT ON TABLE user_interactions IS 'Tracks user-to-user interactions';
COMMENT ON TABLE conversation_analytics IS 'Analytics for conversation quality and outcomes';
