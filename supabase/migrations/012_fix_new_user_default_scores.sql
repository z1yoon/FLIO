-- Migration: Fix new user default trust scores
-- New users should start at 조약돌 (pebble) tier, not 진주 (pearl)
--
-- Current issue:
-- - consistency_score defaults to 1.0 (perfect)
-- - behavioral_score defaults to 1.0 (perfect)
-- - This gives new users 45% base score → 진주 (pearl) tier
--
-- Solution:
-- - Change both defaults to 0.0 (unverified/unknown)
-- - New users will start at 0-20% → 조약돌 (pebble) tier
-- - They must complete profile and verify documents to increase score

-- 1. Update table defaults for new users
ALTER TABLE user_trust_scores
  ALTER COLUMN consistency_score SET DEFAULT 0.0;

ALTER TABLE user_trust_scores
  ALTER COLUMN behavioral_score SET DEFAULT 0.0;

-- Note: Existing users will be recalculated when calculate_trust_score() is next called
-- This happens automatically when users log in or view their profile

-- 2. Drop and recreate the calculate_trust_score function with new defaults
DROP FUNCTION IF EXISTS calculate_trust_score(UUID);

CREATE FUNCTION calculate_trust_score(p_user_id UUID)
RETURNS TABLE (
    user_id UUID,
    document_score FLOAT,
    consistency_score FLOAT,
    behavioral_score FLOAT,
    completeness_score FLOAT,
    total_score FLOAT,
    trust_tier VARCHAR(20),
    calculation_details JSONB
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_document_score FLOAT := 0.0;
    v_consistency_score FLOAT := 0.0;  -- Changed from 1.0
    v_behavioral_score FLOAT := 0.0;   -- Changed from 1.0
    v_completeness_score FLOAT := 0.0;
    v_total_score FLOAT := 0.0;
    v_trust_tier VARCHAR(20);
    v_weights JSONB := '{"document": 0.35, "consistency": 0.25, "behavioral": 0.20, "completeness": 0.20}'::jsonb;
    v_details JSONB := '{}'::jsonb;
    v_doc_count INTEGER;
    v_contradiction_count INTEGER;
    v_high_risk_count INTEGER;
    v_profile_fields INTEGER := 0;
    v_total_fields INTEGER := 20; -- Approximate total profile fields
    v_answered_questions INTEGER := 0;
    v_total_questions INTEGER := 44;
BEGIN
    -- 1. Document Score (35% weight)
    -- Count verified documents (ID, education, income, employment)
    SELECT COUNT(DISTINCT document_type)
    INTO v_doc_count
    FROM user_documents
    WHERE user_documents.user_id = p_user_id
      AND verification_status = 'verified'
      AND document_type IN ('id_card', 'diploma', 'income_cert', 'employment_cert');

    v_document_score := LEAST(v_doc_count / 4.0, 1.0);

    -- 2. Consistency Score (25% weight)
    -- ONLY deduct points for detected contradictions
    -- Default is 0.0 (unknown), increases to 1.0 when verified as consistent
    SELECT COUNT(*)
    INTO v_contradiction_count
    FROM consistency_checks
    WHERE consistency_checks.user_id = p_user_id
      AND contradiction_score >= 0.7;

    IF v_contradiction_count > 0 THEN
        v_consistency_score := GREATEST(1.0 - (v_contradiction_count * 0.15), 0.0);
    ELSE
        -- No contradictions detected
        -- But for new users, remain at 0.0 until NLI check is performed
        SELECT COUNT(*)
        INTO v_contradiction_count
        FROM consistency_checks
        WHERE consistency_checks.user_id = p_user_id;

        IF v_contradiction_count > 0 THEN
            -- NLI check performed, no contradictions found
            v_consistency_score := 1.0;
        ELSE
            -- No NLI check performed yet
            v_consistency_score := 0.0;
        END IF;
    END IF;

    -- 3. Behavioral Score (20% weight)
    -- ONLY deduct points for suspicious behavior
    -- Default is 0.0 (unknown), increases to 1.0 with good behavior over time
    SELECT COUNT(*)
    INTO v_high_risk_count
    FROM user_behavior_logs
    WHERE user_behavior_logs.user_id = p_user_id
      AND risk_level = 'high';

    IF v_high_risk_count > 0 THEN
        v_behavioral_score := GREATEST(1.0 - (v_high_risk_count * 0.2), 0.0);
    ELSE
        -- Check account age and activity
        DECLARE
            v_account_age_days INTEGER;
            v_activity_count INTEGER;
        BEGIN
            SELECT EXTRACT(DAY FROM (NOW() - created_at))
            INTO v_account_age_days
            FROM profiles
            WHERE profiles.user_id = p_user_id;

            SELECT COUNT(*)
            INTO v_activity_count
            FROM user_behavior_logs
            WHERE user_behavior_logs.user_id = p_user_id;

            -- Account age contributes to behavioral score
            -- 0-7 days: 0.0
            -- 7-30 days: 0.3
            -- 30-90 days: 0.6
            -- 90+ days: 1.0
            IF v_account_age_days >= 90 THEN
                v_behavioral_score := 1.0;
            ELSIF v_account_age_days >= 30 THEN
                v_behavioral_score := 0.6;
            ELSIF v_account_age_days >= 7 THEN
                v_behavioral_score := 0.3;
            ELSE
                v_behavioral_score := 0.0;  -- New account
            END IF;
        END;
    END IF;

    -- 4. Completeness Score (20% weight)
    -- Count filled profile fields
    SELECT
        CASE WHEN gender IS NOT NULL THEN 1 ELSE 0 END +
        CASE WHEN birth_date IS NOT NULL THEN 1 ELSE 0 END +
        CASE WHEN location IS NOT NULL THEN 1 ELSE 0 END +
        CASE WHEN height_cm IS NOT NULL THEN 1 ELSE 0 END +
        CASE WHEN education_level IS NOT NULL THEN 1 ELSE 0 END +
        CASE WHEN university_name IS NOT NULL THEN 1 ELSE 0 END +
        CASE WHEN employment_status IS NOT NULL THEN 1 ELSE 0 END +
        CASE WHEN company_name IS NOT NULL THEN 1 ELSE 0 END +
        CASE WHEN annual_income_range IS NOT NULL THEN 1 ELSE 0 END +
        CASE WHEN marital_status IS NOT NULL THEN 1 ELSE 0 END
    INTO v_profile_fields
    FROM profiles
    WHERE profiles.user_id = p_user_id;

    -- Count answered questions
    SELECT COUNT(*)
    INTO v_answered_questions
    FROM user_answers
    WHERE user_answers.user_id = p_user_id;

    -- Completeness = 50% profile + 50% questions
    v_completeness_score := (v_profile_fields::FLOAT / v_total_fields::FLOAT * 0.5) +
                           (v_answered_questions::FLOAT / v_total_questions::FLOAT * 0.5);

    -- 5. Calculate total weighted score
    v_total_score := (v_document_score * 0.35) +
                     (v_consistency_score * 0.25) +
                     (v_behavioral_score * 0.20) +
                     (v_completeness_score * 0.20);

    -- 6. Determine tier based on Ocean Pearl Theme
    -- 조약돌 → 조개 → 진주 → 산호 → 다이아
    IF v_total_score >= 0.80 THEN
        v_trust_tier := 'diamond';  -- 다이아 (80-100%)
    ELSIF v_total_score >= 0.60 THEN
        v_trust_tier := 'coral';    -- 산호 (60-79%)
    ELSIF v_total_score >= 0.40 THEN
        v_trust_tier := 'pearl';    -- 진주 (40-59%)
    ELSIF v_total_score >= 0.20 THEN
        v_trust_tier := 'shell';    -- 조개 (20-39%)
    ELSE
        v_trust_tier := 'pebble';   -- 조약돌 (0-19%)
    END IF;

    -- 7. Build calculation details
    v_details := jsonb_build_object(
        'weights', v_weights,
        'components', jsonb_build_object(
            'document', jsonb_build_object(
                'score', v_document_score,
                'verified_docs', v_doc_count
            ),
            'consistency', jsonb_build_object(
                'score', v_consistency_score,
                'contradictions', v_contradiction_count
            ),
            'behavioral', jsonb_build_object(
                'score', v_behavioral_score,
                'high_risk_events', v_high_risk_count
            ),
            'completeness', jsonb_build_object(
                'score', v_completeness_score,
                'profile_fields', v_profile_fields,
                'answered_questions', v_answered_questions
            )
        ),
        'tier_thresholds', jsonb_build_object(
            'pebble', '0-19%',
            'shell', '20-39%',
            'pearl', '40-59%',
            'coral', '60-79%',
            'diamond', '80-100%'
        )
    );

    -- 8. Upsert trust score record
    INSERT INTO user_trust_scores (
        user_id,
        document_score,
        consistency_score,
        behavioral_score,
        completeness_score,
        total_trust_score,
        trust_tier,
        last_calculated_at,
        calculation_details
    ) VALUES (
        p_user_id,
        v_document_score,
        v_consistency_score,
        v_behavioral_score,
        v_completeness_score,
        v_total_score,
        v_trust_tier,
        NOW(),
        v_details
    )
    ON CONFLICT (user_id)
    DO UPDATE SET
        document_score = EXCLUDED.document_score,
        consistency_score = EXCLUDED.consistency_score,
        behavioral_score = EXCLUDED.behavioral_score,
        completeness_score = EXCLUDED.completeness_score,
        total_trust_score = EXCLUDED.total_trust_score,
        trust_tier = EXCLUDED.trust_tier,
        last_calculated_at = EXCLUDED.last_calculated_at,
        calculation_details = EXCLUDED.calculation_details;

    -- 9. Return calculated scores
    RETURN QUERY
    SELECT
        p_user_id,
        v_document_score,
        v_consistency_score,
        v_behavioral_score,
        v_completeness_score,
        v_total_score,
        v_trust_tier,
        v_details;
END;
$$;

COMMENT ON FUNCTION calculate_trust_score(UUID) IS 'Updated: New users start with consistency_score=0.0 and behavioral_score=0.0 instead of 1.0. This ensures new users start at 조약돌 (pebble) tier.';
