-- ==========================================
-- FLIO Complete Verification System
-- ==========================================
-- Consolidated: All verification tables in ONE place
-- 1. Photo verification (liveness + face match)
-- 2. Document verification (OCR + authenticity)
-- 3. Phone verification
-- 4. Social media verification
-- 5. User data (family, education, career)
-- 6. Behavioral tracking
-- 7. NLI consistency checks
-- ==========================================

-- ===================
-- 1. PHOTO VERIFICATION (Required for matching access)
-- ===================

CREATE TABLE IF NOT EXISTS photo_verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    challenge_pose VARCHAR(50) NOT NULL, -- smile, turn_left, turn_right, thumbs_up, peace_sign
    submitted_selfie_url TEXT NOT NULL,
    submitted_at TIMESTAMPTZ DEFAULT NOW(),

    -- Azure Face API results
    face_match_score FLOAT,   -- Does selfie match profile photos? (0.0-1.0)
    liveness_score FLOAT,     -- Real person, not photo-of-photo? (0.0-1.0)
    pose_match_score FLOAT,   -- Did they do the requested pose? (0.0-1.0)
    verification_score FLOAT, -- Average of above

    verification_status VARCHAR(20) DEFAULT 'pending', -- pending, verified, flagged, rejected
    verified_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ, -- Re-verify every 6 months

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_photo_verif_user ON photo_verifications(user_id);
CREATE INDEX IF NOT EXISTS idx_photo_verif_status ON photo_verifications(verification_status);
CREATE INDEX IF NOT EXISTS idx_photo_verif_expires ON photo_verifications(expires_at) WHERE verification_status = 'verified';

-- ===================
-- 2. DOCUMENT VERIFICATION (OCR + Authenticity)
-- ===================

CREATE TABLE IF NOT EXISTS user_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Document identification
    document_type VARCHAR(50) NOT NULL, -- id_card, diploma, employment_cert, income_proof
    document_subtype VARCHAR(50),
    file_url TEXT NOT NULL,
    file_name VARCHAR(255),
    file_size_bytes INTEGER,
    mime_type VARCHAR(50),

    -- OCR extraction results
    ocr_raw_text TEXT,
    ocr_extracted_data JSONB,
    ocr_confidence_score FLOAT,
    ocr_processed_at TIMESTAMPTZ,

    -- Comparison with user input
    user_input_data JSONB,
    match_details JSONB,
    match_score FLOAT,

    -- Verification status
    verification_status VARCHAR(20) DEFAULT 'pending', -- pending, verified, flagged, rejected
    verification_flags JSONB DEFAULT '[]'::jsonb,
    verification_notes TEXT,

    -- Authenticity validation
    authenticity_score FLOAT,
    issuer_validated BOOLEAN DEFAULT false,
    format_validated BOOLEAN DEFAULT false,
    pattern_validated BOOLEAN DEFAULT false,
    authenticity_flags JSONB DEFAULT '[]'::jsonb,

    -- Admin review
    reviewed_by UUID REFERENCES auth.users(id),
    reviewed_at TIMESTAMPTZ,
    review_notes TEXT,
    expires_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_documents_user ON user_documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_type ON user_documents(document_type);
CREATE INDEX IF NOT EXISTS idx_documents_status ON user_documents(verification_status);
CREATE INDEX IF NOT EXISTS idx_documents_user_type ON user_documents(user_id, document_type);
CREATE INDEX IF NOT EXISTS idx_documents_authenticity ON user_documents(authenticity_score DESC);
CREATE INDEX IF NOT EXISTS idx_documents_pending ON user_documents(user_id, created_at)
    WHERE verification_status = 'pending';

COMMENT ON COLUMN user_documents.authenticity_score IS 'Document authenticity score (0.0-1.0) based on issuer, format, and pattern validation';
COMMENT ON COLUMN user_documents.issuer_validated IS 'Whether document issuer was validated against official Korean government/institution names';
COMMENT ON COLUMN user_documents.format_validated IS 'Whether document format/structure matches official Korean document formats';
COMMENT ON COLUMN user_documents.pattern_validated IS 'Whether document numbers and patterns match official formats';

-- ===================
-- 3. PHONE VERIFICATION
-- ===================

CREATE TABLE IF NOT EXISTS phone_verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    phone_number VARCHAR(20) NOT NULL,
    country_code VARCHAR(5) DEFAULT '+82',
    verification_code VARCHAR(10),
    code_expires_at TIMESTAMPTZ,
    is_verified BOOLEAN DEFAULT false,
    verified_at TIMESTAMPTZ,
    attempts_count INTEGER DEFAULT 0,
    last_attempt_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, phone_number)
);

CREATE INDEX IF NOT EXISTS idx_phone_verif_user ON phone_verifications(user_id);

-- ===================
-- 4. SOCIAL MEDIA VERIFICATION
-- ===================

CREATE TABLE IF NOT EXISTS social_verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    platform VARCHAR(50) NOT NULL, -- instagram, facebook, linkedin, kakao
    social_profile_url TEXT NOT NULL,
    username VARCHAR(100),

    -- Verification method
    verification_method VARCHAR(50), -- post_code, bio_code, message_code
    verification_code VARCHAR(100),
    code_expires_at TIMESTAMPTZ,

    -- Social data collected
    followers_count INTEGER,
    posts_count INTEGER,
    account_age_days INTEGER,
    is_private BOOLEAN,

    -- Verification status
    is_verified BOOLEAN DEFAULT false,
    verified_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, platform)
);

CREATE INDEX IF NOT EXISTS idx_social_verif_user ON social_verifications(user_id);
CREATE INDEX IF NOT EXISTS idx_social_verif_platform ON social_verifications(platform);

-- ===================
-- 5. FAMILY BACKGROUND
-- ===================
-- Note: Profile columns (identity, education, career, marital status) are defined in 001_core_schema.sql

CREATE TABLE IF NOT EXISTS user_family_background (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Parents information
    father_occupation VARCHAR(100),
    father_education VARCHAR(50),
    father_alive BOOLEAN DEFAULT true,
    mother_occupation VARCHAR(100),
    mother_education VARCHAR(50),
    mother_alive BOOLEAN DEFAULT true,
    parents_status VARCHAR(50) DEFAULT '양부모',
    parents_marital_status VARCHAR(50),
    parents_financial_stability VARCHAR(50),

    -- Siblings
    sibling_count INTEGER DEFAULT 0,
    sibling_info JSONB DEFAULT '[]'::jsonb,
    birth_order INTEGER DEFAULT 1,

    -- Family assets
    family_property_type VARCHAR(50),
    family_location VARCHAR(100),

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id)
);

CREATE INDEX IF NOT EXISTS idx_family_background_user ON user_family_background(user_id);

COMMENT ON TABLE user_family_background IS 'Stores family background information for trust scoring';

-- ===================
-- 7. NLI CONSISTENCY CHECKS
-- ===================

CREATE TABLE IF NOT EXISTS consistency_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Check identification
    check_type VARCHAR(50) NOT NULL,
    source_a VARCHAR(50),
    statement_a TEXT NOT NULL,
    source_b VARCHAR(50),
    statement_b TEXT NOT NULL,

    -- NLI results
    relationship VARCHAR(20), -- entailment, neutral, contradiction
    contradiction_score FLOAT,
    confidence_score FLOAT,

    -- AI analysis
    ai_model_used VARCHAR(50) DEFAULT 'gpt-4o-mini',
    ai_reasoning TEXT,
    ai_response_raw JSONB,
    trust_impact FLOAT DEFAULT 0.0,

    -- Resolution
    is_resolved BOOLEAN DEFAULT false,
    resolution_notes TEXT,
    resolved_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_consistency_user ON consistency_checks(user_id);
CREATE INDEX IF NOT EXISTS idx_consistency_type ON consistency_checks(check_type);
CREATE INDEX IF NOT EXISTS idx_consistency_score ON consistency_checks(contradiction_score DESC);
CREATE INDEX IF NOT EXISTS idx_consistency_unresolved ON consistency_checks(user_id, is_resolved)
    WHERE is_resolved = false;

COMMENT ON TABLE consistency_checks IS 'NLI-based consistency checks between profile and answers';

-- ===================
-- 8. BEHAVIORAL TRACKING
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

COMMENT ON TABLE user_behavior_logs IS 'Tracks user behavior for trust score calculation (scoring logic in migration 010)';

-- ===================
-- 9. ROW LEVEL SECURITY
-- ===================

ALTER TABLE photo_verifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE phone_verifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE social_verifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_family_background ENABLE ROW LEVEL SECURITY;
ALTER TABLE consistency_checks ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_behavior_logs ENABLE ROW LEVEL SECURITY;

-- Photo verifications
CREATE POLICY "Users can view own photo verifications"
    ON photo_verifications FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can upload own photo verifications"
    ON photo_verifications FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Documents
CREATE POLICY "Users can view own documents"
    ON user_documents FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can upload own documents"
    ON user_documents FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Phone verifications
CREATE POLICY "Users can view own phone verifications"
    ON phone_verifications FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own phone verifications"
    ON phone_verifications FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own phone verifications"
    ON phone_verifications FOR UPDATE USING (auth.uid() = user_id);

-- Social verifications
CREATE POLICY "Users can view own social verifications"
    ON social_verifications FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own social verifications"
    ON social_verifications FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own social verifications"
    ON social_verifications FOR UPDATE USING (auth.uid() = user_id);

-- Family background
CREATE POLICY "Users can view own family background"
    ON user_family_background FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own family background"
    ON user_family_background FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own family background"
    ON user_family_background FOR UPDATE USING (auth.uid() = user_id);

-- Consistency checks (service-managed)
CREATE POLICY "Service can manage consistency checks"
    ON consistency_checks FOR ALL USING (true);

-- Behavior logs (service-managed)
CREATE POLICY "Service can manage behavior logs"
    ON user_behavior_logs FOR ALL USING (true);

-- ===================
-- 10. HELPER FUNCTIONS
-- ===================

-- Log user behavior (no scoring logic)
CREATE OR REPLACE FUNCTION log_user_behavior(
    p_user_id UUID,
    p_event_type VARCHAR(50),
    p_event_data JSONB DEFAULT '{}',
    p_field_changed VARCHAR(100) DEFAULT NULL,
    p_old_value TEXT DEFAULT NULL,
    p_new_value TEXT DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_risk_level VARCHAR(20) := 'low';
    v_risk_reason TEXT := NULL;
    v_event_category VARCHAR(30) := 'general';
    v_log_id UUID;
BEGIN
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
            v_risk_reason := 'Real name changed';
            v_event_category := 'critical';
        WHEN 'answer_rewrite' THEN
            v_risk_level := 'medium';
            v_risk_reason := 'Question answer changed';
            v_event_category := 'important';
        ELSE
            v_risk_level := 'low';
            v_event_category := 'general';
    END CASE;

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

    RETURN v_log_id;
END;
$$ LANGUAGE plpgsql;

-- ===================
-- 11. TRIGGERS
-- ===================

-- Timestamp update trigger
CREATE OR REPLACE FUNCTION trigger_update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_photo_verifications_timestamp ON photo_verifications;
CREATE TRIGGER update_photo_verifications_timestamp
    BEFORE UPDATE ON photo_verifications
    FOR EACH ROW EXECUTE FUNCTION trigger_update_timestamp();

DROP TRIGGER IF EXISTS update_documents_timestamp ON user_documents;
CREATE TRIGGER update_documents_timestamp
    BEFORE UPDATE ON user_documents
    FOR EACH ROW EXECUTE FUNCTION trigger_update_timestamp();

DROP TRIGGER IF EXISTS update_family_background_timestamp ON user_family_background;
CREATE TRIGGER update_family_background_timestamp
    BEFORE UPDATE ON user_family_background
    FOR EACH ROW EXECUTE FUNCTION trigger_update_timestamp();

-- Profile change logging trigger
CREATE OR REPLACE FUNCTION trigger_log_profile_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.annual_income_range IS DISTINCT FROM NEW.annual_income_range THEN
        PERFORM log_user_behavior(
            NEW.user_id, 'income_change',
            jsonb_build_object('field', 'annual_income_range'),
            'annual_income_range', OLD.annual_income_range, NEW.annual_income_range
        );
    END IF;

    IF OLD.education_level IS DISTINCT FROM NEW.education_level THEN
        PERFORM log_user_behavior(
            NEW.user_id, 'education_change',
            jsonb_build_object('field', 'education_level'),
            'education_level', OLD.education_level, NEW.education_level
        );
    END IF;

    IF OLD.real_name IS DISTINCT FROM NEW.real_name THEN
        PERFORM log_user_behavior(
            NEW.user_id, 'real_name_change',
            jsonb_build_object('field', 'real_name'),
            'real_name', OLD.real_name, NEW.real_name
        );
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS log_profile_changes_trigger ON profiles;
CREATE TRIGGER log_profile_changes_trigger
    AFTER UPDATE ON profiles
    FOR EACH ROW EXECUTE FUNCTION trigger_log_profile_changes();

-- ===================
-- MIGRATION COMPLETE
-- ===================
