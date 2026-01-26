-- ==========================================
-- FLIO Trust Score Matching Algorithm
-- ==========================================
-- Description: Tier-based weighted matching algorithm
-- Consolidated from: 005_trust_score_system.sql (lines 276-387)
-- ==========================================

-- ==========================================
-- WEIGHTED MATCHING ALGORITHM
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
-- GRANT PERMISSIONS
-- ==========================================

GRANT EXECUTE ON FUNCTION calculate_weighted_answer_alignment TO authenticated;
GRANT EXECUTE ON FUNCTION find_matches TO authenticated;

-- ==========================================
-- COMMENTS
-- ==========================================

COMMENT ON FUNCTION calculate_weighted_answer_alignment IS 'Calculates weighted answer alignment between two users based on question weights and importance ratings';
COMMENT ON FUNCTION find_matches IS 'Hybrid matching algorithm: embeddings (60%) + weighted answers (40%) within tier-based pools';
