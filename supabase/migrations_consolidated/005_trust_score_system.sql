-- ==========================================
-- FLIO Trust Score & Tier-Based Matching System
-- ==========================================
-- Consolidates: 009_tier_based_matching + 010_trust_score_system + 012_fix_trust_score_defaults
-- Complete 5-tier trust score system with verification and matching
-- ==========================================

-- ==========================================
-- PART 1: 5-TIER SYSTEM CONFIGURATION
-- ==========================================

-- Tier calculation function
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

-- Note: tier_preferences column already defined in profiles table (001_core_schema.sql)

-- Create indexes for tier-based queries
CREATE INDEX IF NOT EXISTS idx_profiles_trust_tier ON profiles(trust_tier);
CREATE INDEX IF NOT EXISTS idx_profiles_tier_preferences ON profiles USING GIN(tier_preferences);

-- ==========================================
-- PART 2: PHOTO VERIFICATION SYSTEM (REQUIRED - 20% weight)
-- ==========================================

-- Photo verification score function
CREATE OR REPLACE FUNCTION calculate_photo_verification_score(p_user_id UUID)
RETURNS FLOAT AS $$
DECLARE v_score FLOAT := 0.0; v_verified_at TIMESTAMPTZ; v_verification_score FLOAT; v_expires_at TIMESTAMPTZ;
BEGIN
    SELECT verified_at, verification_score, expires_at
    INTO v_verified_at, v_verification_score, v_expires_at
    FROM photo_verifications
    WHERE user_id = p_user_id AND verification_status = 'verified'
    ORDER BY verified_at DESC LIMIT 1;

    -- If not verified, return 0 (user is BLOCKED from matches anyway)
    IF v_verified_at IS NULL THEN RETURN 0.0; END IF;

    -- Score based on quality and freshness
    RETURN CASE
        WHEN v_expires_at > NOW() AND v_verification_score >= 0.90 THEN 1.0  -- Recent + high quality
        WHEN v_expires_at > NOW() AND v_verification_score >= 0.75 THEN 0.8  -- Recent + good quality
        WHEN v_expires_at <= NOW() THEN 0.5  -- Expired - needs re-verification
        ELSE 0.6
    END;
END;
$$ LANGUAGE plpgsql;

-- Function to check if user can access matches (PHOTO REQUIRED)
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
$$ LANGUAGE plpgsql;

-- ==========================================
-- PART 3: SOCIAL VERIFICATION SYSTEM (10% weight)
-- ==========================================

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
$$ LANGUAGE plpgsql;

-- ==========================================
-- PART 4: BEHAVIORAL & REPUTATION SYSTEM (20% total)
-- ==========================================
-- Note: user_behavior_logs engagement columns already defined in 004_verification_system.sql

-- User Reports Table
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

-- User Interactions Table
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

-- Conversation Analytics Table
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

-- Behavioral score function (15% weight)
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
$$ LANGUAGE plpgsql;

-- Reputation score function (5% weight)
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
$$ LANGUAGE plpgsql;

-- ==========================================
-- PART 5: WEIGHTED MATCHING ALGORITHM
-- ==========================================

-- Helper: Calculate weighted answer alignment
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
$$ LANGUAGE plpgsql;

-- Hybrid Matching: embeddings (60%) + weighted answers (40%)
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
$$ LANGUAGE plpgsql;

-- ==========================================
-- PART 6: TRUST SCORE CALCULATION (7 COMPONENTS)
-- ==========================================

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

    -- 3. Consistency (15%) - Build up gradually with answers
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

    -- 4. Behavioral (15%) - Already handles account age in function
    v_behavioral_score := calculate_behavioral_score(p_user_id);

    -- 5. Social (10%)
    v_social_score := calculate_social_verification_score(p_user_id);

    -- 6. Completeness (10%)
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

-- ==========================================
-- PART 7: TRIGGERS & SYNC
-- ==========================================

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
-- PART 8: BACKFILL & PERMISSIONS
-- ==========================================

-- Backfill tier_preferences for existing users
UPDATE profiles
SET tier_preferences = get_default_tier_preferences(COALESCE(trust_tier, 'pebble'))
WHERE tier_preferences IS NULL;

-- Grant permissions
GRANT EXECUTE ON FUNCTION calculate_tier_from_score TO authenticated;
GRANT EXECUTE ON FUNCTION get_default_tier_preferences TO authenticated;
GRANT EXECUTE ON FUNCTION calculate_photo_verification_score TO authenticated;
GRANT EXECUTE ON FUNCTION can_user_access_matches TO authenticated;
GRANT EXECUTE ON FUNCTION calculate_social_verification_score TO authenticated;
GRANT EXECUTE ON FUNCTION calculate_behavioral_score TO authenticated;
GRANT EXECUTE ON FUNCTION calculate_reputation_score TO authenticated;
GRANT EXECUTE ON FUNCTION calculate_weighted_answer_alignment TO authenticated;
GRANT EXECUTE ON FUNCTION find_matches TO authenticated;
GRANT EXECUTE ON FUNCTION calculate_trust_score TO authenticated;

GRANT SELECT, INSERT, UPDATE ON photo_verifications TO authenticated;
GRANT SELECT, INSERT, UPDATE ON social_verifications TO authenticated;
GRANT SELECT, INSERT, UPDATE ON user_reports TO authenticated;
GRANT SELECT, INSERT, UPDATE ON user_interactions TO authenticated;
GRANT SELECT, INSERT, UPDATE ON conversation_analytics TO authenticated;

-- ==========================================
-- COMMENTS & DOCUMENTATION
-- ==========================================

COMMENT ON COLUMN profiles.tier_preferences IS 'Ocean Pearl Theme tiers user wants to match with: pebble(조약돌), shell(조개), pearl(진주), coral(산호), diamond(다이아)';
COMMENT ON COLUMN profiles.trust_tier IS 'Current tier based on trust score: pebble(0-19%), shell(20-39%), pearl(40-59%), coral(60-79%), diamond(80-100%)';
COMMENT ON FUNCTION get_default_tier_preferences IS 'Returns default tier preferences for a given trust tier. Lower tiers can only match with same or lower tiers.';
COMMENT ON FUNCTION calculate_trust_score IS 'Calculates comprehensive trust score from 7 components: Document (25%), Photo (20%), Consistency (15%), Behavioral (15%), Social (10%), Completeness (10%), Reputation (5%)';

-- ==========================================
-- MIGRATION NOTES
-- ==========================================
-- Trust Score System Summary:
--
-- 🔒 PHOTO VERIFICATION REQUIRED:
--    - Users cannot access matches without photo verification
--    - Photo verification expires every 6 months (re-verify required)
--    - Still contributes 20% to trust score based on quality
--
-- 💎 5-TIER SYSTEM:
--    - Diamond (80-100%): ₩59,900/month, 30 matches/day + Priority
--    - Coral (60-79%):    ₩39,900/month, 20 matches/day
--    - Pearl (40-59%):    ₩19,900/month, 15 matches/day
--    - Shell (20-39%):    ₩9,900/month,  10 matches/day
--    - Pebble (0-19%):    Free,          5 matches/day
--
-- 🎯 MATCHING ALGORITHM:
--    - Weighted question scoring (important questions weighted higher)
--    - Formula: embedding (60%) + weighted answers (40%)
--    - Trust score NOT included in matching (users matched within same tier)
--
-- 📊 TRUST SCORE DEFAULTS FOR NEW USERS:
--    - Consistency: 0.3 (builds to 1.0 with 30+ answers)
--    - Behavioral: 0.5 (builds to 0.8 with 6+ months account age)
--    - Reputation: 1.0 (decreases with negative behavior)
--    - New users start in Pebble tier and progress up
-- ==========================================
