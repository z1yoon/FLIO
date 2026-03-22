-- ==========================================
-- FLIO Simplified Trust Score System
-- ==========================================
-- Migration: 012_simplified_trust_score.sql
-- Description: Replaces the complex 7-component trust score with a simple
--              verification checklist. 1 document = 1 tier upgrade.
--
--   신분증   (id_card)          20 pts → 이름, 나이
--   건강검진서 (health_checkup)  20 pts → 키, 몸무게  (NEW)
--   졸업증명서 (diploma)         20 pts → 학교
--   재직증명서 (employment_cert) 20 pts → 회사
--   소득증명서 (income_proof)    20 pts → 연봉
--
-- Tier thresholds (unchanged — same 0/20/40/60/80% breakpoints):
--   조약돌  0–19 pts   조개  20–39   진주  40–59   산호  60–79   다이아  80–100
-- ==========================================

-- ==========================================
-- 1. Add health_checkup to document_type enum
-- ==========================================

ALTER TABLE user_documents
    DROP CONSTRAINT IF EXISTS user_documents_document_type_check;

ALTER TABLE user_documents
    ADD CONSTRAINT user_documents_document_type_check
    CHECK (document_type IN (
        'id_card',
        'health_checkup',
        'diploma',
        'employment_cert',
        'income_proof',
        'criminal_check',
        'business_license'
    ));

COMMENT ON COLUMN user_documents.document_type IS
    'id_card=신분증(이름,나이) health_checkup=건강검진서(키,몸무게) '
    'diploma=졸업증명서(학교) employment_cert=재직증명서(회사) '
    'income_proof=소득증명서(연봉)';

-- ==========================================
-- 2. Simplify user_trust_scores table
-- ==========================================

-- Add new columns used by the simplified scoring
ALTER TABLE user_trust_scores
    ADD COLUMN IF NOT EXISTS verified_documents  JSONB  DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS field_verifications JSONB  DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS reputation_penalty  INT    DEFAULT 0,
    ADD COLUMN IF NOT EXISTS nli_penalty         INT    DEFAULT 0,
    ADD COLUMN IF NOT EXISTS nli_contradictions  JSONB  DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS is_matching_blocked BOOLEAN DEFAULT FALSE;

-- Drop old component columns that are no longer used
ALTER TABLE user_trust_scores
    DROP COLUMN IF EXISTS document_score,
    DROP COLUMN IF EXISTS photo_score,
    DROP COLUMN IF EXISTS consistency_score,
    DROP COLUMN IF EXISTS behavioral_score,
    DROP COLUMN IF EXISTS social_score,
    DROP COLUMN IF EXISTS completeness_score,
    DROP COLUMN IF EXISTS reputation_score;

-- ==========================================
-- 3. Update daily_match_views limit reference
-- ==========================================

-- Update tier comment to reflect new limits (3/5/7/10/15)
COMMENT ON TABLE daily_match_views IS
    'Tracks daily match views. Tier limits: 조약돌=3 조개=5 진주=7 산호=10 다이아=15';
