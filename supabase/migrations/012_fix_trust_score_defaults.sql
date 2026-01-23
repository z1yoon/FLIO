-- Fix trust score calculation to not give new users 100% scores
-- This updates the calculate_trust_score function to use realistic defaults

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
    v_account_age_days INTEGER := 0;
    v_unresolved_contradictions INTEGER := 0;
BEGIN
    -- 1. Document (25%)
    SELECT COALESCE(AVG(match_score), 0.0) INTO v_document_score
    FROM user_documents WHERE user_id = p_user_id AND verification_status = 'verified';

    -- 2. Photo (20%) - REQUIRED but still contributes to score quality
    v_photo_score := calculate_photo_verification_score(p_user_id);

    -- 3. Consistency (15%) - NEW LOGIC: Build up gradually
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
        -- Has contradictions - use old formula
        SELECT COALESCE(1.0 - AVG(contradiction_score), 0.5) INTO v_consistency_score
        FROM consistency_checks WHERE user_id = p_user_id AND NOT is_resolved;
    END IF;

    -- 4. Behavioral (15%) - NEW LOGIC: Base 0.5 + age bonus
    SELECT EXTRACT(DAY FROM NOW() - created_at)::INTEGER INTO v_account_age_days
    FROM profiles WHERE user_id = p_user_id;

    v_account_age_days := COALESCE(v_account_age_days, 0);

    -- Start at 0.5, build up with account age
    v_behavioral_score := 0.5;
    IF v_account_age_days >= 180 THEN
        v_behavioral_score := v_behavioral_score + 0.30;  -- 6+ months: 0.80
    ELSIF v_account_age_days >= 90 THEN
        v_behavioral_score := v_behavioral_score + 0.20;  -- 3+ months: 0.70
    ELSIF v_account_age_days >= 30 THEN
        v_behavioral_score := v_behavioral_score + 0.10;  -- 1+ month: 0.60
    ELSIF v_account_age_days >= 7 THEN
        v_behavioral_score := v_behavioral_score + 0.05;  -- 1+ week: 0.55
    END IF;

    -- Apply penalties from behavior logs
    v_behavioral_score := v_behavioral_score - COALESCE(
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

    v_behavioral_score := LEAST(GREATEST(v_behavioral_score, 0.0), 1.0);

    -- 5. Social (10%)
    v_social_score := calculate_social_verification_score(p_user_id);

    -- 6. Completeness (10%)
    SELECT (
        (CASE WHEN real_name IS NOT NULL THEN 0.05 ELSE 0 END) +
        (CASE WHEN height_cm IS NOT NULL THEN 0.03 ELSE 0 END) +
        (CASE WHEN education_level IS NOT NULL THEN 0.05 ELSE 0 END) +
        (CASE WHEN employment_status IS NOT NULL THEN 0.05 ELSE 0 END) +
        (CASE WHEN annual_income_range IS NOT NULL THEN 0.05 ELSE 0 END) +
        0.40 * LEAST((SELECT COUNT(*) FROM user_answers WHERE user_answers.user_id = p_user_id)::FLOAT / 44.0, 1.0) +
        0.10 * (CASE WHEN EXISTS(SELECT 1 FROM user_family_background WHERE user_family_background.user_id = p_user_id) THEN 1 ELSE 0 END)
    ) INTO v_completeness_score
    FROM profiles WHERE profiles.user_id = p_user_id;

    v_completeness_score := COALESCE(v_completeness_score, 0.0);

    -- 7. Reputation (5%)
    v_reputation_score := calculate_reputation_score(p_user_id);

    -- Calculate total (7 components)
    v_total_score := (v_document_score * 0.25) + (v_photo_score * 0.20) + (v_consistency_score * 0.15) +
                     (v_behavioral_score * 0.15) + (v_social_score * 0.10) + (v_completeness_score * 0.10) +
                     (v_reputation_score * 0.05);

    v_total_score := LEAST(GREATEST(v_total_score, 0.0), 1.0);
    v_trust_tier := calculate_tier_from_score(v_total_score);

    -- Upsert trust score
    INSERT INTO user_trust_scores (user_id, document_score, consistency_score, behavioral_score, completeness_score,
                                    total_trust_score, trust_tier, last_calculated_at, updated_at)
    VALUES (p_user_id, v_document_score, v_consistency_score, v_behavioral_score, v_completeness_score,
            v_total_score, v_trust_tier, NOW(), NOW())
    ON CONFLICT (user_id) DO UPDATE SET
        document_score = EXCLUDED.document_score,
        consistency_score = EXCLUDED.consistency_score,
        behavioral_score = EXCLUDED.behavioral_score,
        completeness_score = EXCLUDED.completeness_score,
        total_trust_score = EXCLUDED.total_trust_score,
        trust_tier = EXCLUDED.trust_tier,
        last_calculated_at = NOW(),
        updated_at = NOW();

    -- Update profile
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
        'version', '1.0',
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
