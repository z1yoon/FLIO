-- ==========================================
-- FLIO Verification Tables
-- ==========================================
-- Description: Photo, document, phone, social, family, and consistency verification tables
-- Consolidated from: 004_verification_system.sql (lines 14-244)
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
    follower_count INTEGER,
    posts_count INTEGER,
    account_age_days INTEGER,
    is_private BOOLEAN,
    is_verified_account BOOLEAN DEFAULT false,

    -- Verification status
    is_verified BOOLEAN DEFAULT false,
    verification_status VARCHAR(20) DEFAULT 'pending',
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
-- 6. NLI CONSISTENCY CHECKS
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
-- 7. COMMENTS
-- ===================

COMMENT ON TABLE photo_verifications IS 'Photo verification with liveness detection - REQUIRED for match access';
COMMENT ON TABLE user_documents IS 'Document verification with OCR and authenticity validation';
COMMENT ON TABLE phone_verifications IS 'Phone number verification via SMS';
COMMENT ON TABLE social_verifications IS 'Social media account verification';
COMMENT ON TABLE consistency_checks IS 'AI-powered consistency checks between user statements';
