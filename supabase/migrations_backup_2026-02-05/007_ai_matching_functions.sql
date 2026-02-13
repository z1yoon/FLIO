-- ==========================================
-- FLIO AI Matching Functions
-- ==========================================
-- Description: AI-powered matching functions using vector embeddings
-- Consolidated from: 001_core_schema.sql (lines 278-381)
-- ==========================================

-- Find Similar Profiles (1024D Embeddings)
DROP FUNCTION IF EXISTS find_similar_profiles(vector, UUID, INTEGER, VARCHAR, INTEGER, INTEGER);

CREATE FUNCTION find_similar_profiles(
    query_embedding vector(1024),
    exclude_user_id UUID,
    match_limit INTEGER DEFAULT 20,
    gender_filter VARCHAR(10) DEFAULT NULL,
    min_age INTEGER DEFAULT NULL,
    max_age INTEGER DEFAULT NULL
)
RETURNS TABLE (
    user_id UUID,
    similarity FLOAT,
    nickname VARCHAR(50),
    birth_date DATE,
    gender VARCHAR(10),
    photos TEXT[]
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.user_id,
        (1 - (p.profile_embedding <=> query_embedding))::FLOAT AS similarity,
        p.nickname,
        p.birth_date,
        p.gender,
        p.photos
    FROM public.profiles p
    WHERE p.user_id != exclude_user_id
        AND p.is_active = TRUE
        AND p.profile_embedding IS NOT NULL
        AND (gender_filter IS NULL OR p.gender = gender_filter)
        AND (min_age IS NULL OR DATE_PART('year', AGE(p.birth_date)) >= min_age)
        AND (max_age IS NULL OR DATE_PART('year', AGE(p.birth_date)) <= max_age)
    ORDER BY p.profile_embedding <=> query_embedding
    LIMIT match_limit;
END;
$$ LANGUAGE plpgsql;

-- Store Profile Embedding
DROP FUNCTION IF EXISTS store_profile_embedding(UUID, vector, TEXT);

CREATE FUNCTION store_profile_embedding(
    p_user_id UUID,
    p_embedding vector(1024),
    p_profile_text TEXT DEFAULT NULL
)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE public.profiles
    SET
        profile_embedding = p_embedding,
        updated_at = NOW()
    WHERE user_id = p_user_id;

    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- Get User Profile Summary
DROP FUNCTION IF EXISTS get_user_profile_summary(UUID);

CREATE FUNCTION get_user_profile_summary(p_user_id UUID)
RETURNS TABLE (
    user_id UUID,
    nickname VARCHAR,
    age INTEGER,
    gender VARCHAR,
    bio TEXT,
    photos TEXT[],
    has_embedding BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.user_id,
        p.nickname,
        DATE_PART('year', AGE(p.birth_date))::INTEGER as age,
        p.gender,
        p.bio,
        p.photos,
        (p.profile_embedding IS NOT NULL) as has_embedding
    FROM public.profiles p
    WHERE p.user_id = p_user_id;
END;
$$ LANGUAGE plpgsql;

-- ==========================================
-- GRANT PERMISSIONS
-- ==========================================

GRANT EXECUTE ON FUNCTION find_similar_profiles(vector, UUID, INTEGER, VARCHAR, INTEGER, INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION store_profile_embedding(UUID, vector, TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION get_user_profile_summary(UUID) TO authenticated;

GRANT EXECUTE ON FUNCTION find_similar_profiles(vector, UUID, INTEGER, VARCHAR, INTEGER, INTEGER) TO service_role;
GRANT EXECUTE ON FUNCTION store_profile_embedding(UUID, vector, TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION get_user_profile_summary(UUID) TO service_role;
