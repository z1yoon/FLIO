-- ==========================================
-- FLIO Verification System (Complete)
-- ==========================================
-- Description: Comprehensive verification system including photo verification with liveness detection,
--              document verification with OCR and authenticity validation, phone/SMS verification,
--              social media verification, family background collection, and NLI-based consistency checks
-- Version: 1.0.0
-- Date: 2026-02-05
-- Dependencies: 001_core_system.sql (auth.users, profiles, user_behavior_logs)
-- ==========================================

-- ===========================================
-- TABLE DEFINITIONS
-- ===========================================

-- ===================
-- 1. PHOTO VERIFICATION (Required for matching access)
-- ===================

CREATE TABLE IF NOT EXISTS photo_verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Challenge verification
    challenge_pose VARCHAR(50) NOT NULL CHECK (
        challenge_pose IN ('smile', 'turn_left', 'turn_right', 'thumbs_up', 'peace_sign')
    ),
    submitted_selfie_url TEXT NOT NULL,
    submitted_at TIMESTAMPTZ DEFAULT NOW(),

    -- Azure Face API verification results
    face_match_score FLOAT CHECK (face_match_score >= 0.0 AND face_match_score <= 1.0),
    liveness_score FLOAT CHECK (liveness_score >= 0.0 AND liveness_score <= 1.0),
    pose_match_score FLOAT CHECK (pose_match_score >= 0.0 AND pose_match_score <= 1.0),
    verification_score FLOAT CHECK (verification_score >= 0.0 AND verification_score <= 1.0),

    -- Verification status
    verification_status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (
        verification_status IN ('pending', 'verified', 'flagged', 'rejected')
    ),
    verified_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE photo_verifications IS 'Photo verification with liveness detection and pose challenges - REQUIRED for match access';
COMMENT ON COLUMN photo_verifications.challenge_pose IS 'Randomly assigned pose challenge to verify liveness';
COMMENT ON COLUMN photo_verifications.face_match_score IS 'Azure Face API score comparing selfie to profile photos (0.0-1.0)';
COMMENT ON COLUMN photo_verifications.liveness_score IS 'Azure Face API liveness detection score (0.0-1.0)';
COMMENT ON COLUMN photo_verifications.pose_match_score IS 'Score for how well user performed the challenge pose (0.0-1.0)';
COMMENT ON COLUMN photo_verifications.verification_score IS 'Overall verification score (average of face_match, liveness, and pose_match)';
COMMENT ON COLUMN photo_verifications.expires_at IS 'Photo verification expires after 6 months, requiring re-verification';

-- ===================
-- 2. DOCUMENT VERIFICATION (OCR + Authenticity)
-- ===================

CREATE TABLE IF NOT EXISTS user_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Document identification
    document_type VARCHAR(50) NOT NULL CHECK (
        document_type IN ('id_card', 'diploma', 'employment_cert', 'income_proof', 'business_license')
    ),
    document_subtype VARCHAR(50),
    file_url TEXT NOT NULL,
    file_name VARCHAR(255),
    file_size_bytes INTEGER CHECK (file_size_bytes > 0),
    mime_type VARCHAR(50),

    -- OCR extraction results (Azure Document Intelligence)
    ocr_raw_text TEXT,
    ocr_extracted_data JSONB,
    ocr_confidence_score FLOAT CHECK (ocr_confidence_score >= 0.0 AND ocr_confidence_score <= 1.0),
    ocr_processed_at TIMESTAMPTZ,

    -- Comparison with user-provided data
    user_input_data JSONB,
    match_details JSONB,
    match_score FLOAT CHECK (match_score >= 0.0 AND match_score <= 1.0),

    -- Verification status
    verification_status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (
        verification_status IN ('pending', 'verified', 'flagged', 'rejected')
    ),
    verification_flags JSONB DEFAULT '[]'::jsonb,
    verification_notes TEXT,

    -- Authenticity validation (Korean document format validation)
    authenticity_score FLOAT CHECK (authenticity_score >= 0.0 AND authenticity_score <= 1.0),
    issuer_validated BOOLEAN DEFAULT false,
    format_validated BOOLEAN DEFAULT false,
    pattern_validated BOOLEAN DEFAULT false,
    authenticity_flags JSONB DEFAULT '[]'::jsonb,

    -- Admin review
    reviewed_by UUID REFERENCES auth.users(id),
    reviewed_at TIMESTAMPTZ,
    review_notes TEXT,
    expires_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE user_documents IS 'Document verification with OCR extraction and authenticity validation for Korean documents';
COMMENT ON COLUMN user_documents.document_type IS 'Type of document: id_card (resident registration card), diploma, employment_cert, income_proof, business_license';
COMMENT ON COLUMN user_documents.ocr_extracted_data IS 'Structured data extracted from document via Azure Document Intelligence';
COMMENT ON COLUMN user_documents.user_input_data IS 'User-provided data to compare against OCR results';
COMMENT ON COLUMN user_documents.match_details IS 'Detailed comparison results between OCR and user input';
COMMENT ON COLUMN user_documents.match_score IS 'Overall match score between OCR results and user input (0.0-1.0)';
COMMENT ON COLUMN user_documents.authenticity_score IS 'Document authenticity score (0.0-1.0) based on issuer, format, and pattern validation';
COMMENT ON COLUMN user_documents.issuer_validated IS 'Whether document issuer was validated against official Korean government/institution names';
COMMENT ON COLUMN user_documents.format_validated IS 'Whether document format/structure matches official Korean document formats';
COMMENT ON COLUMN user_documents.pattern_validated IS 'Whether document numbers and patterns match official Korean formats (e.g., resident registration number format)';
COMMENT ON COLUMN user_documents.authenticity_flags IS 'Array of detected authenticity issues or anomalies';

-- ===================
-- 3. PHONE VERIFICATION (SMS-based)
-- ===================

CREATE TABLE IF NOT EXISTS phone_verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Phone details
    phone_number VARCHAR(20) NOT NULL,
    country_code VARCHAR(5) NOT NULL DEFAULT '+82',

    -- Verification code
    verification_code VARCHAR(10),
    code_expires_at TIMESTAMPTZ,

    -- Verification status
    is_verified BOOLEAN NOT NULL DEFAULT false,
    verified_at TIMESTAMPTZ,

    -- Rate limiting
    attempts_count INTEGER NOT NULL DEFAULT 0 CHECK (attempts_count >= 0),
    last_attempt_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(user_id, phone_number)
);

COMMENT ON TABLE phone_verifications IS 'Phone number verification via SMS with rate limiting';
COMMENT ON COLUMN phone_verifications.verification_code IS 'One-time verification code sent via SMS';
COMMENT ON COLUMN phone_verifications.code_expires_at IS 'Verification code expiration timestamp (typically 10 minutes)';
COMMENT ON COLUMN phone_verifications.attempts_count IS 'Number of verification attempts for rate limiting';

-- Unique constraint: One verified phone number per user globally
-- This prevents multiple users from claiming the same phone number
CREATE UNIQUE INDEX IF NOT EXISTS idx_phone_verified_unique
    ON phone_verifications(phone_number)
    WHERE is_verified = true;

COMMENT ON INDEX idx_phone_verified_unique IS 'Ensures one verified phone number per user globally across the platform';

-- ===================
-- 4. SOCIAL MEDIA VERIFICATION
-- ===================

CREATE TABLE IF NOT EXISTS social_verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Platform identification
    platform VARCHAR(50) NOT NULL CHECK (
        platform IN ('instagram', 'facebook', 'linkedin', 'kakao', 'twitter')
    ),
    social_profile_url TEXT NOT NULL,
    username VARCHAR(100),

    -- Verification method
    verification_method VARCHAR(50) CHECK (
        verification_method IN ('post_code', 'bio_code', 'message_code')
    ),
    verification_code VARCHAR(100),
    code_expires_at TIMESTAMPTZ,

    -- Social profile metrics (for trust scoring)
    followers_count INTEGER CHECK (followers_count >= 0),
    follower_count INTEGER CHECK (follower_count >= 0),
    posts_count INTEGER CHECK (posts_count >= 0),
    account_age_days INTEGER CHECK (account_age_days >= 0),
    is_private BOOLEAN,
    is_verified_account BOOLEAN DEFAULT false,

    -- Verification status
    is_verified BOOLEAN NOT NULL DEFAULT false,
    verification_status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (
        verification_status IN ('pending', 'verified', 'flagged', 'rejected')
    ),
    verified_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(user_id, platform)
);

COMMENT ON TABLE social_verifications IS 'Social media account verification for additional identity validation';
COMMENT ON COLUMN social_verifications.verification_method IS 'Method used to verify social account ownership: post_code (post unique code), bio_code (add code to bio), message_code (send DM with code)';
COMMENT ON COLUMN social_verifications.is_verified_account IS 'Whether the social media platform has verified this account (blue checkmark)';
COMMENT ON COLUMN social_verifications.account_age_days IS 'Age of social media account in days (older accounts are more trustworthy)';

-- ===================
-- 5. FAMILY BACKGROUND (For trust scoring)
-- ===================

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

    -- Siblings information
    sibling_count INTEGER NOT NULL DEFAULT 0 CHECK (sibling_count >= 0),
    sibling_info JSONB DEFAULT '[]'::jsonb,
    birth_order INTEGER DEFAULT 1 CHECK (birth_order > 0),

    -- Family assets
    family_property_type VARCHAR(50),
    family_location VARCHAR(100),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(user_id)
);

COMMENT ON TABLE user_family_background IS 'Family background information for trust scoring and matching compatibility';
COMMENT ON COLUMN user_family_background.parents_status IS 'Korean family structure: 양부모 (both parents), 한부모 (single parent), 조손 (grandparents), etc.';
COMMENT ON COLUMN user_family_background.sibling_info IS 'Array of sibling details: [{"gender": "male", "age": 30, "occupation": "engineer", "marital_status": "married"}]';
COMMENT ON COLUMN user_family_background.birth_order IS 'Birth order among siblings (1 = firstborn, 2 = second, etc.)';

-- ===================
-- 6. NLI CONSISTENCY CHECKS (AI-powered contradiction detection)
-- ===================

CREATE TABLE IF NOT EXISTS consistency_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Check identification
    check_type VARCHAR(50) NOT NULL CHECK (
        check_type IN (
            'profile_vs_answer',
            'answer_vs_answer',
            'document_vs_profile',
            'document_vs_answer',
            'social_vs_profile',
            'family_vs_answer'
        )
    ),
    source_a VARCHAR(50),
    statement_a TEXT NOT NULL,
    source_b VARCHAR(50),
    statement_b TEXT NOT NULL,

    -- NLI (Natural Language Inference) results
    relationship VARCHAR(20) CHECK (
        relationship IN ('entailment', 'neutral', 'contradiction')
    ),
    contradiction_score FLOAT CHECK (contradiction_score >= 0.0 AND contradiction_score <= 1.0),
    confidence_score FLOAT CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),

    -- AI analysis
    ai_model_used VARCHAR(50) DEFAULT 'gpt-4o-mini',
    ai_reasoning TEXT,
    ai_response_raw JSONB,
    trust_impact FLOAT DEFAULT 0.0 CHECK (trust_impact >= -1.0 AND trust_impact <= 1.0),

    -- Resolution
    is_resolved BOOLEAN NOT NULL DEFAULT false,
    resolution_notes TEXT,
    resolved_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE consistency_checks IS 'NLI-based consistency checks between profile data, answers, documents, and social media to detect contradictions';
COMMENT ON COLUMN consistency_checks.check_type IS 'Type of consistency check being performed';
COMMENT ON COLUMN consistency_checks.relationship IS 'NLI relationship: entailment (statements agree), neutral (unrelated), contradiction (statements conflict)';
COMMENT ON COLUMN consistency_checks.contradiction_score IS 'Strength of contradiction detected (0.0 = no contradiction, 1.0 = strong contradiction)';
COMMENT ON COLUMN consistency_checks.confidence_score IS 'Confidence in the NLI analysis result (0.0-1.0)';
COMMENT ON COLUMN consistency_checks.trust_impact IS 'Impact on user trust score (-1.0 to +1.0, negative for contradictions)';

-- ===========================================
-- INDEXES
-- ===========================================

-- Photo verifications indexes
CREATE INDEX IF NOT EXISTS idx_photo_verif_user_id
    ON photo_verifications(user_id);
CREATE INDEX IF NOT EXISTS idx_photo_verif_status
    ON photo_verifications(verification_status);
CREATE INDEX IF NOT EXISTS idx_photo_verif_expires
    ON photo_verifications(expires_at)
    WHERE verification_status = 'verified';

-- User documents indexes
CREATE INDEX IF NOT EXISTS idx_documents_user_id
    ON user_documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_type
    ON user_documents(document_type);
CREATE INDEX IF NOT EXISTS idx_documents_status
    ON user_documents(verification_status);
CREATE INDEX IF NOT EXISTS idx_documents_user_type
    ON user_documents(user_id, document_type);
CREATE INDEX IF NOT EXISTS idx_documents_authenticity
    ON user_documents(authenticity_score DESC);
CREATE INDEX IF NOT EXISTS idx_documents_pending
    ON user_documents(user_id, created_at)
    WHERE verification_status = 'pending';
CREATE INDEX IF NOT EXISTS idx_documents_reviewed_by
    ON user_documents(reviewed_by);

-- GIN indexes for JSONB columns in user_documents
CREATE INDEX IF NOT EXISTS idx_documents_ocr_data_gin
    ON user_documents USING GIN(ocr_extracted_data);
CREATE INDEX IF NOT EXISTS idx_documents_user_input_gin
    ON user_documents USING GIN(user_input_data);
CREATE INDEX IF NOT EXISTS idx_documents_match_details_gin
    ON user_documents USING GIN(match_details);
CREATE INDEX IF NOT EXISTS idx_documents_verification_flags_gin
    ON user_documents USING GIN(verification_flags);
CREATE INDEX IF NOT EXISTS idx_documents_authenticity_flags_gin
    ON user_documents USING GIN(authenticity_flags);

-- Phone verifications indexes
CREATE INDEX IF NOT EXISTS idx_phone_verif_user_id
    ON phone_verifications(user_id);
CREATE INDEX IF NOT EXISTS idx_phone_verif_phone_number
    ON phone_verifications(phone_number);
CREATE INDEX IF NOT EXISTS idx_phone_verif_is_verified
    ON phone_verifications(is_verified);

-- Social verifications indexes
CREATE INDEX IF NOT EXISTS idx_social_verif_user_id
    ON social_verifications(user_id);
CREATE INDEX IF NOT EXISTS idx_social_verif_platform
    ON social_verifications(platform);
CREATE INDEX IF NOT EXISTS idx_social_verif_status
    ON social_verifications(verification_status);

-- Family background indexes
CREATE INDEX IF NOT EXISTS idx_family_background_user_id
    ON user_family_background(user_id);

-- GIN index for JSONB column in family_background
CREATE INDEX IF NOT EXISTS idx_family_sibling_info_gin
    ON user_family_background USING GIN(sibling_info);

-- Consistency checks indexes
CREATE INDEX IF NOT EXISTS idx_consistency_user_id
    ON consistency_checks(user_id);
CREATE INDEX IF NOT EXISTS idx_consistency_check_type
    ON consistency_checks(check_type);
CREATE INDEX IF NOT EXISTS idx_consistency_contradiction_score
    ON consistency_checks(contradiction_score DESC);
CREATE INDEX IF NOT EXISTS idx_consistency_relationship
    ON consistency_checks(relationship);
CREATE INDEX IF NOT EXISTS idx_consistency_unresolved
    ON consistency_checks(user_id, is_resolved)
    WHERE is_resolved = false;

-- GIN index for JSONB column in consistency_checks
CREATE INDEX IF NOT EXISTS idx_consistency_ai_response_gin
    ON consistency_checks USING GIN(ai_response_raw);

-- ===========================================
-- FUNCTIONS
-- ===========================================

-- ===================
-- Helper function: Log user behavior (for verification-related events)
-- ===================

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
    -- Categorize event by type
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
        WHEN 'document_upload' THEN
            v_risk_level := 'low';
            v_event_category := 'verification';
        WHEN 'verification_failure' THEN
            v_risk_level := 'high';
            v_risk_reason := 'Verification failed';
            v_event_category := 'verification';
        ELSE
            v_risk_level := 'low';
            v_event_category := 'general';
    END CASE;

    -- Insert behavior log
    INSERT INTO user_behavior_logs (
        user_id,
        event_type,
        event_category,
        event_data,
        field_changed,
        old_value,
        new_value,
        risk_level,
        risk_reason
    ) VALUES (
        p_user_id,
        p_event_type,
        v_event_category,
        p_event_data,
        p_field_changed,
        p_old_value,
        p_new_value,
        v_risk_level,
        v_risk_reason
    )
    RETURNING id INTO v_log_id;

    RETURN v_log_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION log_user_behavior IS 'Log user behavior events for verification tracking and trust scoring';

-- ===================
-- Function: Check if user has valid photo verification
-- ===================

CREATE OR REPLACE FUNCTION has_valid_photo_verification(p_user_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    v_is_valid BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1
        FROM photo_verifications
        WHERE user_id = p_user_id
            AND verification_status = 'verified'
            AND (expires_at IS NULL OR expires_at > NOW())
    ) INTO v_is_valid;

    RETURN COALESCE(v_is_valid, false);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION has_valid_photo_verification IS 'Check if user has a valid (non-expired) photo verification';

-- ===================
-- Function: Get user verification status summary
-- ===================

CREATE OR REPLACE FUNCTION get_verification_status(p_user_id UUID)
RETURNS JSONB AS $$
DECLARE
    v_result JSONB;
BEGIN
    SELECT jsonb_build_object(
        'photo_verified', (
            SELECT verification_status = 'verified'
            FROM photo_verifications
            WHERE user_id = p_user_id
                AND (expires_at IS NULL OR expires_at > NOW())
            ORDER BY verified_at DESC
            LIMIT 1
        ),
        'phone_verified', (
            SELECT is_verified
            FROM phone_verifications
            WHERE user_id = p_user_id
            ORDER BY verified_at DESC
            LIMIT 1
        ),
        'documents_verified_count', (
            SELECT COUNT(*)
            FROM user_documents
            WHERE user_id = p_user_id
                AND verification_status = 'verified'
        ),
        'social_verified_count', (
            SELECT COUNT(*)
            FROM social_verifications
            WHERE user_id = p_user_id
                AND is_verified = true
        ),
        'has_family_background', (
            SELECT EXISTS(SELECT 1 FROM user_family_background WHERE user_id = p_user_id)
        ),
        'unresolved_contradictions', (
            SELECT COUNT(*)
            FROM consistency_checks
            WHERE user_id = p_user_id
                AND relationship = 'contradiction'
                AND is_resolved = false
        )
    ) INTO v_result;

    RETURN v_result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION get_verification_status IS 'Get comprehensive verification status summary for a user';

-- ===================
-- Function: Calculate document authenticity score
-- ===================

CREATE OR REPLACE FUNCTION calculate_document_authenticity(
    p_issuer_validated BOOLEAN,
    p_format_validated BOOLEAN,
    p_pattern_validated BOOLEAN,
    p_ocr_confidence FLOAT
)
RETURNS FLOAT AS $$
DECLARE
    v_score FLOAT := 0.0;
    v_checks_passed INTEGER := 0;
BEGIN
    -- Count validation checks passed
    IF p_issuer_validated THEN v_checks_passed := v_checks_passed + 1; END IF;
    IF p_format_validated THEN v_checks_passed := v_checks_passed + 1; END IF;
    IF p_pattern_validated THEN v_checks_passed := v_checks_passed + 1; END IF;

    -- Base score from validation checks (70% weight)
    v_score := (v_checks_passed::FLOAT / 3.0) * 0.7;

    -- Add OCR confidence (30% weight)
    v_score := v_score + (COALESCE(p_ocr_confidence, 0.0) * 0.3);

    -- Ensure score is between 0.0 and 1.0
    v_score := LEAST(GREATEST(v_score, 0.0), 1.0);

    RETURN v_score;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION calculate_document_authenticity IS 'Calculate document authenticity score based on validation checks and OCR confidence';

-- ===========================================
-- TRIGGERS
-- ===========================================

-- ===================
-- Trigger: Update updated_at timestamp
-- ===================

CREATE OR REPLACE FUNCTION trigger_update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply timestamp triggers to verification tables
DROP TRIGGER IF EXISTS update_photo_verifications_timestamp ON photo_verifications;
CREATE TRIGGER update_photo_verifications_timestamp
    BEFORE UPDATE ON photo_verifications
    FOR EACH ROW
    EXECUTE FUNCTION trigger_update_timestamp();

DROP TRIGGER IF EXISTS update_documents_timestamp ON user_documents;
CREATE TRIGGER update_documents_timestamp
    BEFORE UPDATE ON user_documents
    FOR EACH ROW
    EXECUTE FUNCTION trigger_update_timestamp();

DROP TRIGGER IF EXISTS update_phone_verifications_timestamp ON phone_verifications;
CREATE TRIGGER update_phone_verifications_timestamp
    BEFORE UPDATE ON phone_verifications
    FOR EACH ROW
    EXECUTE FUNCTION trigger_update_timestamp();

DROP TRIGGER IF EXISTS update_social_verifications_timestamp ON social_verifications;
CREATE TRIGGER update_social_verifications_timestamp
    BEFORE UPDATE ON social_verifications
    FOR EACH ROW
    EXECUTE FUNCTION trigger_update_timestamp();

DROP TRIGGER IF EXISTS update_family_background_timestamp ON user_family_background;
CREATE TRIGGER update_family_background_timestamp
    BEFORE UPDATE ON user_family_background
    FOR EACH ROW
    EXECUTE FUNCTION trigger_update_timestamp();

-- ===================
-- Trigger: Log profile changes (for verification tracking)
-- ===================

CREATE OR REPLACE FUNCTION trigger_log_profile_changes()
RETURNS TRIGGER AS $$
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

    -- Log real name changes (critical)
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
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS log_profile_changes_trigger ON profiles;
CREATE TRIGGER log_profile_changes_trigger
    AFTER UPDATE ON profiles
    FOR EACH ROW
    EXECUTE FUNCTION trigger_log_profile_changes();

COMMENT ON FUNCTION trigger_log_profile_changes IS 'Log critical profile changes that may indicate fraud or inconsistency';

-- ===========================================
-- ROW LEVEL SECURITY (RLS)
-- ===========================================

-- Enable RLS on all verification tables
ALTER TABLE photo_verifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE phone_verifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE social_verifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_family_background ENABLE ROW LEVEL SECURITY;
ALTER TABLE consistency_checks ENABLE ROW LEVEL SECURITY;

-- ===================
-- RLS Policies: photo_verifications
-- ===================

DROP POLICY IF EXISTS "Users can view own photo verifications" ON photo_verifications;
CREATE POLICY "Users can view own photo verifications"
    ON photo_verifications
    FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own photo verifications" ON photo_verifications;
CREATE POLICY "Users can insert own photo verifications"
    ON photo_verifications
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role can manage all photo verifications" ON photo_verifications;
CREATE POLICY "Service role can manage all photo verifications"
    ON photo_verifications
    FOR ALL
    USING (true);

-- ===================
-- RLS Policies: user_documents
-- ===================

DROP POLICY IF EXISTS "Users can view own documents" ON user_documents;
CREATE POLICY "Users can view own documents"
    ON user_documents
    FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own documents" ON user_documents;
CREATE POLICY "Users can insert own documents"
    ON user_documents
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own documents" ON user_documents;
CREATE POLICY "Users can update own documents"
    ON user_documents
    FOR UPDATE
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role can manage all documents" ON user_documents;
CREATE POLICY "Service role can manage all documents"
    ON user_documents
    FOR ALL
    USING (true);

-- ===================
-- RLS Policies: phone_verifications
-- ===================

DROP POLICY IF EXISTS "Users can view own phone verifications" ON phone_verifications;
CREATE POLICY "Users can view own phone verifications"
    ON phone_verifications
    FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own phone verifications" ON phone_verifications;
CREATE POLICY "Users can insert own phone verifications"
    ON phone_verifications
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own phone verifications" ON phone_verifications;
CREATE POLICY "Users can update own phone verifications"
    ON phone_verifications
    FOR UPDATE
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role can manage all phone verifications" ON phone_verifications;
CREATE POLICY "Service role can manage all phone verifications"
    ON phone_verifications
    FOR ALL
    USING (true);

-- ===================
-- RLS Policies: social_verifications
-- ===================

DROP POLICY IF EXISTS "Users can view own social verifications" ON social_verifications;
CREATE POLICY "Users can view own social verifications"
    ON social_verifications
    FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own social verifications" ON social_verifications;
CREATE POLICY "Users can insert own social verifications"
    ON social_verifications
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own social verifications" ON social_verifications;
CREATE POLICY "Users can update own social verifications"
    ON social_verifications
    FOR UPDATE
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role can manage all social verifications" ON social_verifications;
CREATE POLICY "Service role can manage all social verifications"
    ON social_verifications
    FOR ALL
    USING (true);

-- ===================
-- RLS Policies: user_family_background
-- ===================

DROP POLICY IF EXISTS "Users can view own family background" ON user_family_background;
CREATE POLICY "Users can view own family background"
    ON user_family_background
    FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own family background" ON user_family_background;
CREATE POLICY "Users can insert own family background"
    ON user_family_background
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own family background" ON user_family_background;
CREATE POLICY "Users can update own family background"
    ON user_family_background
    FOR UPDATE
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role can manage all family background" ON user_family_background;
CREATE POLICY "Service role can manage all family background"
    ON user_family_background
    FOR ALL
    USING (true);

-- ===================
-- RLS Policies: consistency_checks
-- ===================

DROP POLICY IF EXISTS "Users can view own consistency checks" ON consistency_checks;
CREATE POLICY "Users can view own consistency checks"
    ON consistency_checks
    FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role can manage all consistency checks" ON consistency_checks;
CREATE POLICY "Service role can manage all consistency checks"
    ON consistency_checks
    FOR ALL
    USING (true);

-- ===========================================
-- FINAL COMMENTS
-- ===========================================

COMMENT ON TABLE photo_verifications IS 'Photo verification with liveness detection and pose challenges - REQUIRED for match access. Verification expires after 6 months.';
COMMENT ON TABLE user_documents IS 'Document verification with OCR extraction and authenticity validation for Korean documents (ID cards, diplomas, employment certificates, etc.)';
COMMENT ON TABLE phone_verifications IS 'Phone number verification via SMS with rate limiting. One verified phone number per user globally.';
COMMENT ON TABLE social_verifications IS 'Social media account verification for additional identity validation and trust scoring';
COMMENT ON TABLE user_family_background IS 'Family background information for trust scoring and matching compatibility in Korean dating context';
COMMENT ON TABLE consistency_checks IS 'NLI-based consistency checks between profile data, answers, documents, and social media to detect contradictions and fraud';
