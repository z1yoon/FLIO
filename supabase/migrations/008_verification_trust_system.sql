-- ==========================================
-- FLIO Migration 008: Verification & Trust System
-- Korean Marriage Agency Style (결혼정보회사)
-- ==========================================
-- This migration adds:
-- 1. Extended profile fields (education, income, family)
-- 2. Document verification system (OCR)
-- 3. Trust Score system
-- 4. Behavioral tracking
-- 5. NLI Consistency checks
-- ==========================================

-- ===================
-- 1. EXTEND PROFILES TABLE
-- ===================

-- 1.1 Identity fields
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS real_name VARCHAR(50);
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS real_name_verified BOOLEAN DEFAULT false;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS height_cm INTEGER;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS weight_kg INTEGER;

-- 1.2 Education fields (학력)
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS education_level VARCHAR(50);
-- Values: 고졸, 전문대졸, 대졸, 석사, 박사
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS university_name VARCHAR(100);
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS major VARCHAR(100);
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS graduation_year INTEGER;

-- 1.3 Career & Income fields (직장/소득)
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS employment_status VARCHAR(50);
-- Values: 정규직, 계약직, 자영업, 프리랜서, 공무원, 전문직, 무직
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS company_name VARCHAR(100);
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS job_title VARCHAR(100);
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS industry VARCHAR(100);
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS annual_income_range VARCHAR(50);
-- Values: ~3천만, 3천만~5천만, 5천만~7천만, 7천만~1억, 1억~1.5억, 1.5억~2억, 2억~

-- 1.4 Marital History (혼인이력)
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS marital_status VARCHAR(20) DEFAULT '미혼';
-- Values: 미혼, 이혼, 사별
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS divorce_reason TEXT;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS has_children BOOLEAN DEFAULT false;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS children_count INTEGER DEFAULT 0;

-- 1.5 Verification & Trust fields
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS verification_level VARCHAR(20) DEFAULT 'none';
-- Values: none, basic, full
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS trust_tier VARCHAR(20) DEFAULT 'unverified';
-- Values: unverified, bronze, silver, gold, platinum
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS last_verified_at TIMESTAMPTZ;

-- ===================
-- 2. FAMILY BACKGROUND TABLE
-- ===================

CREATE TABLE IF NOT EXISTS user_family_background (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Father information
    father_occupation VARCHAR(100),
    father_education VARCHAR(50), -- 고졸, 대졸, 석사, 박사
    father_alive BOOLEAN DEFAULT true,

    -- Mother information
    mother_occupation VARCHAR(100),
    mother_education VARCHAR(50),
    mother_alive BOOLEAN DEFAULT true,

    -- Parents status
    parents_status VARCHAR(50) DEFAULT '양친', -- 양친, 한부모(부), 한부모(모), 조부모양육, 기타
    parents_marital_status VARCHAR(50), -- 기혼, 이혼, 사별
    parents_financial_stability VARCHAR(50), -- 매우안정, 안정, 보통, 불안정

    -- Siblings
    sibling_count INTEGER DEFAULT 0,
    sibling_info JSONB DEFAULT '[]'::jsonb,
    -- Format: [{"gender": "male/female", "age": 30, "occupation": "회사원", "married": true}]

    -- Birth order
    birth_order INTEGER DEFAULT 1, -- 1 = 첫째, 2 = 둘째, etc.

    -- Optional: Family assets (sensitive, optional)
    family_property_type VARCHAR(50), -- 자가, 전세, 월세
    family_location VARCHAR(100), -- 거주지역

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_id)
);

-- Index for family background
CREATE INDEX IF NOT EXISTS idx_family_background_user ON user_family_background(user_id);

-- ===================
-- 3. DOCUMENT VERIFICATION TABLE
-- ===================

CREATE TABLE IF NOT EXISTS user_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Document identification
    document_type VARCHAR(50) NOT NULL,
    -- Values: id_card, diploma, income_cert, employment_cert
    document_subtype VARCHAR(50),
    -- Values for id_card: 주민등록증, 운전면허증, 여권
    -- Values for diploma: 졸업증명서, 학위증명서
    -- Values for income_cert: 소득금액증명원, 원천징수영수증
    -- Values for employment_cert: 재직증명서, 4대보험가입증명

    -- File storage
    file_url TEXT NOT NULL,
    file_name VARCHAR(255),
    file_size_bytes INTEGER,
    mime_type VARCHAR(50),

    -- OCR extraction results
    ocr_raw_text TEXT, -- Raw OCR output
    ocr_extracted_data JSONB, -- Structured extracted data
    ocr_confidence_score FLOAT, -- OCR confidence (0.0-1.0)
    ocr_processed_at TIMESTAMPTZ,

    -- Comparison with user input
    user_input_data JSONB, -- What user claimed in profile
    match_details JSONB, -- Field-by-field comparison
    match_score FLOAT, -- Overall match score (0.0-1.0)

    -- Verification status
    verification_status VARCHAR(20) DEFAULT 'pending',
    -- Values: pending, processing, verified, flagged, rejected, expired
    verification_flags JSONB DEFAULT '[]'::jsonb, -- List of issues found
    verification_notes TEXT,

    -- Admin review (for flagged cases)
    reviewed_by UUID REFERENCES auth.users(id),
    reviewed_at TIMESTAMPTZ,
    review_notes TEXT,

    -- Expiration (documents may need re-verification)
    expires_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for documents
CREATE INDEX IF NOT EXISTS idx_documents_user ON user_documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_type ON user_documents(document_type);
CREATE INDEX IF NOT EXISTS idx_documents_status ON user_documents(verification_status);
CREATE INDEX IF NOT EXISTS idx_documents_user_type ON user_documents(user_id, document_type);

-- ===================
-- 4. TRUST SCORE TABLE
-- ===================

CREATE TABLE IF NOT EXISTS user_trust_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Component scores (0.0 - 1.0)
    document_score FLOAT DEFAULT 0.0,
    -- Based on: ID verification, education, income, employment docs

    consistency_score FLOAT DEFAULT 1.0,
    -- Based on: NLI contradiction checks

    behavioral_score FLOAT DEFAULT 1.0,
    -- Based on: Edit patterns, stability, account age

    completeness_score FLOAT DEFAULT 0.0,
    -- Based on: Profile fields, questions answered, family background

    -- Weighted total score
    total_trust_score FLOAT DEFAULT 0.0,

    -- Trust tier assignment
    trust_tier VARCHAR(20) DEFAULT 'unverified',
    -- Values: unverified, bronze, silver, gold, platinum

    -- Score weights (stored for audit/debugging)
    weights_used JSONB DEFAULT '{
        "document": 0.35,
        "consistency": 0.25,
        "behavioral": 0.20,
        "completeness": 0.20
    }'::jsonb,

    -- Calculation details for transparency
    calculation_details JSONB DEFAULT '{}'::jsonb,
    -- Stores breakdown of how each component was calculated

    -- History tracking
    score_history JSONB DEFAULT '[]'::jsonb,
    -- Stores past scores with timestamps

    -- Timestamps
    last_calculated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_id)
);

-- Indexes for trust scores
CREATE INDEX IF NOT EXISTS idx_trust_scores_user ON user_trust_scores(user_id);
CREATE INDEX IF NOT EXISTS idx_trust_scores_tier ON user_trust_scores(trust_tier);
CREATE INDEX IF NOT EXISTS idx_trust_scores_total ON user_trust_scores(total_trust_score DESC);

-- ===================
-- 5. BEHAVIORAL TRACKING TABLE
-- ===================

CREATE TABLE IF NOT EXISTS user_behavior_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Event identification
    event_type VARCHAR(50) NOT NULL,
    -- Values: profile_edit, income_change, education_change,
    --         answer_change, answer_rewrite, photo_change,
    --         login, profile_view, match_action

    event_category VARCHAR(30) DEFAULT 'general',
    -- Values: critical, important, general

    -- Event data
    event_data JSONB DEFAULT '{}'::jsonb,
    -- Stores context about the event

    -- Change tracking (for edit events)
    field_changed VARCHAR(100),
    old_value TEXT,
    new_value TEXT,

    -- Risk assessment
    risk_level VARCHAR(20) DEFAULT 'low',
    -- Values: low, medium, high, critical

    risk_reason TEXT,
    -- Explanation for risk level

    -- Session context
    session_id VARCHAR(100),
    ip_address INET,
    user_agent TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for behavior logs
CREATE INDEX IF NOT EXISTS idx_behavior_logs_user ON user_behavior_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_behavior_logs_type ON user_behavior_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_behavior_logs_risk ON user_behavior_logs(risk_level);
CREATE INDEX IF NOT EXISTS idx_behavior_logs_user_time ON user_behavior_logs(user_id, created_at DESC);

-- Partitioning hint: Consider partitioning by created_at for large scale
-- CREATE TABLE user_behavior_logs_y2025m01 PARTITION OF user_behavior_logs
--     FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

-- ===================
-- 6. NLI CONSISTENCY CHECKS TABLE
-- ===================

CREATE TABLE IF NOT EXISTS consistency_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Check identification
    check_type VARCHAR(50) NOT NULL,
    -- Values: profile_vs_answers, cross_section, temporal,
    --         text_answers_internal, profile_vs_documents

    -- Statements being compared
    source_a VARCHAR(50), -- e.g., 'profile.income_range'
    statement_a TEXT NOT NULL,

    source_b VARCHAR(50), -- e.g., 'answer.financial_priority'
    statement_b TEXT NOT NULL,

    -- NLI results
    relationship VARCHAR(20),
    -- Values: entailment, neutral, contradiction

    contradiction_score FLOAT, -- 0.0 = no contradiction, 1.0 = full contradiction
    confidence_score FLOAT, -- AI confidence in the assessment

    -- AI analysis
    ai_model_used VARCHAR(50) DEFAULT 'gpt-4o-mini',
    ai_reasoning TEXT, -- Explanation from AI
    ai_response_raw JSONB, -- Full AI response for debugging

    -- Impact on trust score
    trust_impact FLOAT DEFAULT 0.0, -- How much this affects trust score

    -- Resolution (if user explains discrepancy)
    is_resolved BOOLEAN DEFAULT false,
    resolution_notes TEXT,
    resolved_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for consistency checks
CREATE INDEX IF NOT EXISTS idx_consistency_user ON consistency_checks(user_id);
CREATE INDEX IF NOT EXISTS idx_consistency_type ON consistency_checks(check_type);
CREATE INDEX IF NOT EXISTS idx_consistency_score ON consistency_checks(contradiction_score DESC);
CREATE INDEX IF NOT EXISTS idx_consistency_unresolved ON consistency_checks(user_id, is_resolved)
    WHERE is_resolved = false;

-- ===================
-- 7. PHONE VERIFICATION TABLE
-- ===================

CREATE TABLE IF NOT EXISTS phone_verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    phone_number VARCHAR(20) NOT NULL,
    country_code VARCHAR(5) DEFAULT '+82', -- Korea default

    -- Verification code
    verification_code VARCHAR(10),
    code_expires_at TIMESTAMPTZ,

    -- Status
    is_verified BOOLEAN DEFAULT false,
    verified_at TIMESTAMPTZ,

    -- Attempt tracking
    attempts_count INTEGER DEFAULT 0,
    last_attempt_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_id, phone_number)
);

-- Index for phone verifications
CREATE INDEX IF NOT EXISTS idx_phone_verif_user ON phone_verifications(user_id);

-- ===================
-- 8. RPC FUNCTIONS
-- ===================

-- 8.1 Calculate Trust Score
CREATE OR REPLACE FUNCTION calculate_trust_score(p_user_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_document_score FLOAT := 0.0;
    v_consistency_score FLOAT := 1.0;
    v_behavioral_score FLOAT := 1.0;
    v_completeness_score FLOAT := 0.0;
    v_total_score FLOAT := 0.0;
    v_trust_tier VARCHAR(20);
    v_weights JSONB := '{"document": 0.35, "consistency": 0.25, "behavioral": 0.20, "completeness": 0.20}'::jsonb;
    v_details JSONB := '{}'::jsonb;
BEGIN
    -- Calculate Document Score
    SELECT COALESCE(AVG(match_score), 0.0) INTO v_document_score
    FROM user_documents
    WHERE user_id = p_user_id AND verification_status = 'verified';

    -- Calculate Consistency Score
    SELECT COALESCE(1.0 - AVG(contradiction_score), 1.0) INTO v_consistency_score
    FROM consistency_checks
    WHERE user_id = p_user_id AND NOT is_resolved;

    -- Calculate Behavioral Score (simplified - high risk events reduce score)
    SELECT COALESCE(
        1.0 - (COUNT(*) FILTER (WHERE risk_level = 'high') * 0.15)
            - (COUNT(*) FILTER (WHERE risk_level = 'medium') * 0.05)
            - (COUNT(*) FILTER (WHERE risk_level = 'critical') * 0.25),
        1.0
    ) INTO v_behavioral_score
    FROM user_behavior_logs
    WHERE user_id = p_user_id
    AND created_at > NOW() - INTERVAL '30 days';

    -- Ensure behavioral score doesn't go below 0
    v_behavioral_score := GREATEST(v_behavioral_score, 0.0);

    -- Calculate Completeness Score
    SELECT
        (
            -- Profile completeness (40%)
            (CASE WHEN real_name IS NOT NULL THEN 0.05 ELSE 0 END) +
            (CASE WHEN height_cm IS NOT NULL THEN 0.03 ELSE 0 END) +
            (CASE WHEN education_level IS NOT NULL THEN 0.05 ELSE 0 END) +
            (CASE WHEN employment_status IS NOT NULL THEN 0.05 ELSE 0 END) +
            (CASE WHEN annual_income_range IS NOT NULL THEN 0.05 ELSE 0 END) +
            (CASE WHEN marital_status IS NOT NULL THEN 0.03 ELSE 0 END) +
            -- Questions answered (40%)
            0.40 * LEAST(
                (SELECT COUNT(*) FROM user_answers WHERE user_answers.user_id = p_user_id)::FLOAT / 44.0,
                1.0
            ) +
            -- Family background (10%)
            (CASE WHEN EXISTS(SELECT 1 FROM user_family_background WHERE user_family_background.user_id = p_user_id)
                THEN 0.10 ELSE 0 END) +
            -- Documents uploaded (10%)
            LEAST(
                (SELECT COUNT(*) FROM user_documents WHERE user_documents.user_id = p_user_id)::FLOAT * 0.025,
                0.10
            )
        )
    INTO v_completeness_score
    FROM profiles
    WHERE profiles.user_id = p_user_id;

    -- Handle case where profile doesn't exist yet
    v_completeness_score := COALESCE(v_completeness_score, 0.0);

    -- Calculate Total Score
    v_total_score :=
        (v_document_score * 0.35) +
        (v_consistency_score * 0.25) +
        (v_behavioral_score * 0.20) +
        (v_completeness_score * 0.20);

    -- Clamp to 0-1 range
    v_total_score := LEAST(GREATEST(v_total_score, 0.0), 1.0);

    -- Determine Trust Tier
    v_trust_tier := CASE
        WHEN v_total_score >= 0.90 THEN 'platinum'
        WHEN v_total_score >= 0.75 THEN 'gold'
        WHEN v_total_score >= 0.60 THEN 'silver'
        WHEN v_total_score >= 0.40 THEN 'bronze'
        ELSE 'unverified'
    END;

    -- Build details JSON
    v_details := jsonb_build_object(
        'document_score', v_document_score,
        'consistency_score', v_consistency_score,
        'behavioral_score', v_behavioral_score,
        'completeness_score', v_completeness_score,
        'total_score', v_total_score,
        'trust_tier', v_trust_tier,
        'calculated_at', NOW()
    );

    -- Upsert trust score record
    INSERT INTO user_trust_scores (
        user_id, document_score, consistency_score, behavioral_score,
        completeness_score, total_trust_score, trust_tier,
        calculation_details, last_calculated_at, updated_at
    ) VALUES (
        p_user_id, v_document_score, v_consistency_score, v_behavioral_score,
        v_completeness_score, v_total_score, v_trust_tier,
        v_details, NOW(), NOW()
    )
    ON CONFLICT (user_id) DO UPDATE SET
        document_score = EXCLUDED.document_score,
        consistency_score = EXCLUDED.consistency_score,
        behavioral_score = EXCLUDED.behavioral_score,
        completeness_score = EXCLUDED.completeness_score,
        total_trust_score = EXCLUDED.total_trust_score,
        trust_tier = EXCLUDED.trust_tier,
        calculation_details = EXCLUDED.calculation_details,
        last_calculated_at = NOW(),
        updated_at = NOW(),
        score_history = user_trust_scores.score_history || jsonb_build_array(
            jsonb_build_object(
                'score', user_trust_scores.total_trust_score,
                'tier', user_trust_scores.trust_tier,
                'timestamp', user_trust_scores.last_calculated_at
            )
        );

    -- Update profile with trust tier
    UPDATE profiles
    SET trust_tier = v_trust_tier,
        updated_at = NOW()
    WHERE profiles.user_id = p_user_id;

    RETURN v_details;
END;
$$;

-- 8.2 Log User Behavior
CREATE OR REPLACE FUNCTION log_user_behavior(
    p_user_id UUID,
    p_event_type VARCHAR(50),
    p_event_data JSONB DEFAULT '{}',
    p_field_changed VARCHAR(100) DEFAULT NULL,
    p_old_value TEXT DEFAULT NULL,
    p_new_value TEXT DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_risk_level VARCHAR(20) := 'low';
    v_risk_reason TEXT := NULL;
    v_event_category VARCHAR(30) := 'general';
    v_log_id UUID;
BEGIN
    -- Determine risk level based on event type
    CASE p_event_type
        WHEN 'income_change' THEN
            v_risk_level := 'high';
            v_risk_reason := 'Income information changed';
            v_event_category := 'critical';
        WHEN 'education_change' THEN
            v_risk_level := 'high';
            v_risk_reason := 'Education information changed';
            v_event_category := 'critical';
        WHEN 'real_name_change' THEN
            v_risk_level := 'critical';
            v_risk_reason := 'Real name changed - requires re-verification';
            v_event_category := 'critical';
        WHEN 'answer_rewrite' THEN
            v_risk_level := 'medium';
            v_risk_reason := 'Question answer significantly changed';
            v_event_category := 'important';
        WHEN 'profile_edit' THEN
            v_risk_level := 'low';
            v_event_category := 'general';
        WHEN 'photo_change' THEN
            v_risk_level := 'low';
            v_event_category := 'general';
        ELSE
            v_risk_level := 'low';
            v_event_category := 'general';
    END CASE;

    -- Check for suspicious patterns (multiple high-risk events)
    IF (
        SELECT COUNT(*) FROM user_behavior_logs
        WHERE user_id = p_user_id
        AND risk_level IN ('high', 'critical')
        AND created_at > NOW() - INTERVAL '7 days'
    ) >= 3 THEN
        v_risk_level := 'critical';
        v_risk_reason := COALESCE(v_risk_reason, '') || ' Multiple high-risk changes detected';
    END IF;

    -- Insert log entry
    INSERT INTO user_behavior_logs (
        user_id, event_type, event_category, event_data,
        field_changed, old_value, new_value,
        risk_level, risk_reason
    ) VALUES (
        p_user_id, p_event_type, v_event_category, p_event_data,
        p_field_changed, p_old_value, p_new_value,
        v_risk_level, v_risk_reason
    )
    RETURNING id INTO v_log_id;

    -- If high/critical risk, recalculate trust score
    IF v_risk_level IN ('high', 'critical') THEN
        PERFORM calculate_trust_score(p_user_id);
    END IF;

    RETURN v_log_id;
END;
$$;

-- 8.3 Get User Trust Summary
CREATE OR REPLACE FUNCTION get_user_trust_summary(p_user_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_result JSONB;
BEGIN
    SELECT jsonb_build_object(
        'user_id', p_user_id,
        'trust_score', COALESCE(ts.total_trust_score, 0),
        'trust_tier', COALESCE(ts.trust_tier, 'unverified'),
        'component_scores', jsonb_build_object(
            'document', COALESCE(ts.document_score, 0),
            'consistency', COALESCE(ts.consistency_score, 1),
            'behavioral', COALESCE(ts.behavioral_score, 1),
            'completeness', COALESCE(ts.completeness_score, 0)
        ),
        'verification_status', jsonb_build_object(
            'id_verified', EXISTS(
                SELECT 1 FROM user_documents
                WHERE user_id = p_user_id
                AND document_type = 'id_card'
                AND verification_status = 'verified'
            ),
            'education_verified', EXISTS(
                SELECT 1 FROM user_documents
                WHERE user_id = p_user_id
                AND document_type = 'diploma'
                AND verification_status = 'verified'
            ),
            'income_verified', EXISTS(
                SELECT 1 FROM user_documents
                WHERE user_id = p_user_id
                AND document_type = 'income_cert'
                AND verification_status = 'verified'
            ),
            'employment_verified', EXISTS(
                SELECT 1 FROM user_documents
                WHERE user_id = p_user_id
                AND document_type = 'employment_cert'
                AND verification_status = 'verified'
            ),
            'phone_verified', EXISTS(
                SELECT 1 FROM phone_verifications
                WHERE user_id = p_user_id
                AND is_verified = true
            )
        ),
        'recent_flags', (
            SELECT COALESCE(jsonb_agg(
                jsonb_build_object(
                    'type', check_type,
                    'score', contradiction_score,
                    'created_at', created_at
                )
            ), '[]'::jsonb)
            FROM consistency_checks
            WHERE user_id = p_user_id
            AND contradiction_score > 0.5
            AND NOT is_resolved
            ORDER BY created_at DESC
            LIMIT 5
        ),
        'last_calculated', ts.last_calculated_at
    ) INTO v_result
    FROM user_trust_scores ts
    WHERE ts.user_id = p_user_id;

    -- If no trust score exists, return default
    IF v_result IS NULL THEN
        v_result := jsonb_build_object(
            'user_id', p_user_id,
            'trust_score', 0,
            'trust_tier', 'unverified',
            'component_scores', jsonb_build_object(
                'document', 0,
                'consistency', 1,
                'behavioral', 1,
                'completeness', 0
            ),
            'verification_status', jsonb_build_object(
                'id_verified', false,
                'education_verified', false,
                'income_verified', false,
                'employment_verified', false,
                'phone_verified', false
            ),
            'recent_flags', '[]'::jsonb,
            'last_calculated', NULL
        );
    END IF;

    RETURN v_result;
END;
$$;

-- 8.4 Get Profile with Trust for Matching
CREATE OR REPLACE FUNCTION get_profile_with_trust(p_user_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_result JSONB;
BEGIN
    SELECT jsonb_build_object(
        'user_id', p.user_id,
        'nickname', p.nickname,
        'real_name_initial', LEFT(p.real_name, 1) || '**', -- Privacy: show only initial
        'age', EXTRACT(YEAR FROM AGE(NOW(), p.birth_date))::INTEGER,
        'gender', p.gender,
        'height_cm', p.height_cm,
        'education_level', p.education_level,
        'university_name', p.university_name,
        'employment_status', p.employment_status,
        'job_title', p.job_title,
        'industry', p.industry,
        'annual_income_range', p.annual_income_range,
        'marital_status', p.marital_status,
        'trust_tier', COALESCE(ts.trust_tier, 'unverified'),
        'trust_score', COALESCE(ts.total_trust_score, 0),
        'verified_items', (
            SELECT COALESCE(array_agg(document_type), ARRAY[]::VARCHAR[])
            FROM user_documents
            WHERE user_id = p_user_id AND verification_status = 'verified'
        ),
        'has_family_info', EXISTS(
            SELECT 1 FROM user_family_background WHERE user_id = p_user_id
        ),
        'profile_completeness', COALESCE(ts.completeness_score, 0)
    ) INTO v_result
    FROM profiles p
    LEFT JOIN user_trust_scores ts ON ts.user_id = p.user_id
    WHERE p.user_id = p_user_id;

    RETURN v_result;
END;
$$;

-- ===================
-- 9. ROW LEVEL SECURITY
-- ===================

-- Enable RLS on new tables
ALTER TABLE user_family_background ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_trust_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_behavior_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE consistency_checks ENABLE ROW LEVEL SECURITY;
ALTER TABLE phone_verifications ENABLE ROW LEVEL SECURITY;

-- Family Background: Users can only see/edit their own
CREATE POLICY "Users can view own family background"
    ON user_family_background FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own family background"
    ON user_family_background FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own family background"
    ON user_family_background FOR UPDATE
    USING (auth.uid() = user_id);

-- Documents: Users can only see/upload their own
CREATE POLICY "Users can view own documents"
    ON user_documents FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can upload own documents"
    ON user_documents FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Trust Scores: Users can view their own, service can update
CREATE POLICY "Users can view own trust score"
    ON user_trust_scores FOR SELECT
    USING (auth.uid() = user_id);

-- Behavior Logs: Service only (users can't directly access)
CREATE POLICY "Service can manage behavior logs"
    ON user_behavior_logs FOR ALL
    USING (true); -- Controlled via service role

-- Consistency Checks: Service only
CREATE POLICY "Service can manage consistency checks"
    ON consistency_checks FOR ALL
    USING (true); -- Controlled via service role

-- Phone Verifications: Users can manage their own
CREATE POLICY "Users can view own phone verifications"
    ON phone_verifications FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own phone verifications"
    ON phone_verifications FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own phone verifications"
    ON phone_verifications FOR UPDATE
    USING (auth.uid() = user_id);

-- ===================
-- 10. TRIGGERS
-- ===================

-- Trigger to log profile changes
CREATE OR REPLACE FUNCTION trigger_log_profile_changes()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- Log income changes
    IF OLD.annual_income_range IS DISTINCT FROM NEW.annual_income_range THEN
        PERFORM log_user_behavior(
            NEW.user_id,
            'income_change',
            jsonb_build_object('field', 'annual_income_range'),
            'annual_income_range',
            OLD.annual_income_range,
            NEW.annual_income_range
        );
    END IF;

    -- Log education changes
    IF OLD.education_level IS DISTINCT FROM NEW.education_level THEN
        PERFORM log_user_behavior(
            NEW.user_id,
            'education_change',
            jsonb_build_object('field', 'education_level'),
            'education_level',
            OLD.education_level,
            NEW.education_level
        );
    END IF;

    -- Log real name changes
    IF OLD.real_name IS DISTINCT FROM NEW.real_name THEN
        PERFORM log_user_behavior(
            NEW.user_id,
            'real_name_change',
            jsonb_build_object('field', 'real_name'),
            'real_name',
            OLD.real_name,
            NEW.real_name
        );
    END IF;

    RETURN NEW;
END;
$$;

-- Create trigger on profiles table
DROP TRIGGER IF EXISTS log_profile_changes_trigger ON profiles;
CREATE TRIGGER log_profile_changes_trigger
    AFTER UPDATE ON profiles
    FOR EACH ROW
    EXECUTE FUNCTION trigger_log_profile_changes();

-- Trigger to update timestamps
CREATE OR REPLACE FUNCTION trigger_update_timestamp()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

-- Apply timestamp triggers to new tables
DROP TRIGGER IF EXISTS update_family_background_timestamp ON user_family_background;
CREATE TRIGGER update_family_background_timestamp
    BEFORE UPDATE ON user_family_background
    FOR EACH ROW
    EXECUTE FUNCTION trigger_update_timestamp();

DROP TRIGGER IF EXISTS update_documents_timestamp ON user_documents;
CREATE TRIGGER update_documents_timestamp
    BEFORE UPDATE ON user_documents
    FOR EACH ROW
    EXECUTE FUNCTION trigger_update_timestamp();

DROP TRIGGER IF EXISTS update_trust_scores_timestamp ON user_trust_scores;
CREATE TRIGGER update_trust_scores_timestamp
    BEFORE UPDATE ON user_trust_scores
    FOR EACH ROW
    EXECUTE FUNCTION trigger_update_timestamp();

-- ===================
-- 11. INDEXES FOR PERFORMANCE
-- ===================

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_profiles_trust_matching
    ON profiles(trust_tier, gender)
    WHERE trust_tier != 'unverified';

CREATE INDEX IF NOT EXISTS idx_trust_scores_tier_score
    ON user_trust_scores(trust_tier, total_trust_score DESC);

-- Partial index for pending verifications
CREATE INDEX IF NOT EXISTS idx_documents_pending
    ON user_documents(user_id, created_at)
    WHERE verification_status = 'pending';

-- ===================
-- MIGRATION COMPLETE
-- ===================
-- Run calculate_trust_score(user_id) after profile updates
-- to recalculate trust tier
