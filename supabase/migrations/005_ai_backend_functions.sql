-- FLIO AI Backend Functions
-- RPC functions for Azure OpenAI integration and profile matching

-- ==========================================
-- Fix 1: Update find_similar_profiles function for 1024D embeddings
-- ==========================================
-- Drop if exists to avoid conflicts
DROP FUNCTION IF EXISTS find_similar_profiles_v2(vector, UUID, INTEGER, VARCHAR, INTEGER, INTEGER);

CREATE FUNCTION find_similar_profiles_v2(
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
        (1 - (p.profile_embedding_v2 <=> query_embedding))::FLOAT AS similarity,
        p.nickname,
        p.birth_date,
        p.gender,
        p.photos
    FROM public.profiles p
    WHERE p.user_id != exclude_user_id
        AND p.is_active = TRUE
        AND p.profile_embedding_v2 IS NOT NULL
        -- Optional filters
        AND (gender_filter IS NULL OR p.gender = gender_filter)
        AND (min_age IS NULL OR DATE_PART('year', AGE(p.birth_date)) >= min_age)
        AND (max_age IS NULL OR DATE_PART('year', AGE(p.birth_date)) <= max_age)
    ORDER BY p.profile_embedding_v2 <=> query_embedding
    LIMIT match_limit;
END;
$$ LANGUAGE plpgsql;

-- ==========================================
-- Fix 2: Get unanswered questions for user (with answered status)
-- ==========================================
-- Drop existing function first to change return type
DROP FUNCTION IF EXISTS get_questions_for_user(UUID, INTEGER);

CREATE FUNCTION get_questions_for_user(
    p_user_id UUID,
    p_limit INTEGER DEFAULT 40
)
RETURNS TABLE (
    question_id VARCHAR(100),
    question_text TEXT,
    category VARCHAR(50),
    answer_type VARCHAR(50),
    options JSONB,
    base_weight FLOAT,
    effectiveness_score FLOAT,
    is_answered BOOLEAN
) AS $$
DECLARE
    user_lang VARCHAR;
BEGIN
    -- Get user's language preference
    SELECT language INTO user_lang FROM public.user_settings WHERE user_id = p_user_id;
    user_lang := COALESCE(user_lang, 'ko');
    
    RETURN QUERY
    SELECT 
        q.id as question_id,
        CASE WHEN user_lang = 'en' THEN q.text_en ELSE q.text_ko END as question_text,
        q.category,
        q.answer_type,
        q.options,
        q.base_weight,
        q.effectiveness_score,
        (ua.question_id IS NOT NULL) as is_answered
    FROM public.questions q
    LEFT JOIN public.user_answers ua ON (q.id = ua.question_id AND ua.user_id = p_user_id)
    WHERE q.is_active = TRUE
    ORDER BY 
        CASE WHEN ua.question_id IS NULL THEN 0 ELSE 1 END,  -- Unanswered first
        q.effectiveness_score DESC,
        q.id
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- ==========================================
-- Fix 3: Get user profile summary for matching
-- ==========================================
-- Drop if exists to avoid conflicts
DROP FUNCTION IF EXISTS get_user_profile_summary(UUID);

CREATE FUNCTION get_user_profile_summary(
    p_user_id UUID
)
RETURNS TABLE (
    user_id UUID,
    nickname VARCHAR(50),
    age INTEGER,
    gender VARCHAR(10),
    total_answers INTEGER,
    has_embedding BOOLEAN,
    last_updated TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.user_id,
        p.nickname,
        DATE_PART('year', AGE(p.birth_date))::INTEGER as age,
        p.gender,
        COALESCE(answer_counts.total_answers, 0) as total_answers,
        (p.profile_embedding_v2 IS NOT NULL) as has_embedding,
        p.updated_at as last_updated
    FROM public.profiles p
    LEFT JOIN (
        SELECT 
            ua.user_id,
            COUNT(*) as total_answers
        FROM public.user_answers ua
        GROUP BY ua.user_id
    ) answer_counts ON p.user_id = answer_counts.user_id
    WHERE p.user_id = p_user_id;
END;
$$ LANGUAGE plpgsql;

-- ==========================================
-- Fix 4: Update embedding storage helper for profiles table
-- ==========================================
-- Note: store_user_embedding already exists in migration 004 for user_embeddings table
-- This function updates profiles table instead
-- Drop if exists to avoid conflicts
DROP FUNCTION IF EXISTS store_user_embedding(UUID, vector, TEXT);

CREATE FUNCTION store_profile_embedding(
    p_user_id UUID,
    p_embedding vector(1024),
    p_profile_text TEXT DEFAULT NULL
)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE public.profiles 
    SET 
        profile_embedding_v2 = p_embedding,
        updated_at = NOW(),
        answers = CASE 
            WHEN p_profile_text IS NOT NULL THEN 
                COALESCE(answers, '{}'::jsonb) || jsonb_build_object('profile_text', p_profile_text)
            ELSE answers
        END
    WHERE user_id = p_user_id;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- ==========================================
-- Fix 5: Add indexes for performance  
-- ==========================================

-- Index for user answers performance
CREATE INDEX IF NOT EXISTS idx_user_answers_user_question 
ON public.user_answers(user_id, question_id);

-- Index for profiles with embeddings
CREATE INDEX IF NOT EXISTS idx_profiles_has_embedding 
ON public.profiles(user_id) WHERE profile_embedding_v2 IS NOT NULL;

-- Index for active questions
CREATE INDEX IF NOT EXISTS idx_questions_active_effectiveness 
ON public.questions(is_active, effectiveness_score DESC) WHERE is_active = TRUE;

-- ==========================================
-- Fix 6: Grant permissions for AI backend
-- ==========================================

-- Grant execute permissions on new functions (with full signatures)
GRANT EXECUTE ON FUNCTION find_similar_profiles_v2(vector, UUID, INTEGER, VARCHAR, INTEGER, INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION get_questions_for_user(UUID, INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION get_user_profile_summary(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION store_profile_embedding(UUID, vector, TEXT) TO authenticated;

-- Ensure service role can access these functions
GRANT EXECUTE ON FUNCTION find_similar_profiles_v2(vector, UUID, INTEGER, VARCHAR, INTEGER, INTEGER) TO service_role;
GRANT EXECUTE ON FUNCTION get_questions_for_user(UUID, INTEGER) TO service_role;
GRANT EXECUTE ON FUNCTION get_user_profile_summary(UUID) TO service_role;
GRANT EXECUTE ON FUNCTION store_profile_embedding(UUID, vector, TEXT) TO service_role;

-- ==========================================
-- Fix 7: Add helpful view for debugging
-- ==========================================

CREATE OR REPLACE VIEW user_embedding_status AS
SELECT 
    p.user_id,
    p.nickname,
    DATE_PART('year', AGE(p.birth_date))::INTEGER as age,
    COALESCE(answer_counts.total_answers, 0) as answers_count,
    (p.profile_embedding_v2 IS NOT NULL) as has_embedding,
    CASE 
        WHEN p.profile_embedding_v2 IS NOT NULL THEN 1024
        ELSE NULL
    END as embedding_dimension,
    p.updated_at
FROM public.profiles p
LEFT JOIN (
    SELECT 
        ua.user_id,
        COUNT(*) as total_answers
    FROM public.user_answers ua
    GROUP BY ua.user_id
) answer_counts ON p.user_id = answer_counts.user_id
WHERE p.is_active = TRUE;

-- Grant access to the view
GRANT SELECT ON user_embedding_status TO authenticated, service_role;

-- Add comment for documentation
COMMENT ON VIEW user_embedding_status IS 
'Helper view to check which users have profile embeddings for AI matching';

COMMENT ON FUNCTION find_similar_profiles_v2 IS 
'AI matching function using 1024D Azure OpenAI embeddings for profile similarity';

COMMENT ON FUNCTION get_questions_for_user IS 
'Get questions for user with answered status - supports AI backend question flow';

COMMENT ON FUNCTION get_user_profile_summary IS 
'Get user profile summary including answer count and embedding status for AI services';

COMMENT ON FUNCTION store_profile_embedding IS 
'Store profile embedding in profiles table generated by Azure OpenAI for matching purposes';

-- ==========================================
-- Hybrid Matching Algorithm Functions
-- ==========================================

-- Function: Get User Answers with Metadata
DROP FUNCTION IF EXISTS get_user_answers_with_metadata(UUID);

CREATE OR REPLACE FUNCTION get_user_answers_with_metadata(p_user_id UUID)
RETURNS TABLE (
    question_id VARCHAR(100),
    answer_value VARCHAR(100),
    importance INTEGER,
    is_dealbreaker BOOLEAN,
    answer_type VARCHAR(50),
    options JSONB,
    category VARCHAR(50),
    base_weight FLOAT,
    effectiveness_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ua.question_id,
        ua.answer_value,
        ua.importance,
        ua.is_dealbreaker,
        q.answer_type,
        q.options,
        q.category,
        q.base_weight,
        q.effectiveness_score
    FROM user_answers ua
    JOIN questions q ON ua.question_id = q.id
    WHERE ua.user_id = p_user_id
    ORDER BY q.effectiveness_score DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function: Calculate Choice Question Compatibility
DROP FUNCTION IF EXISTS calculate_choice_compatibility(UUID, UUID);

CREATE OR REPLACE FUNCTION calculate_choice_compatibility(
    p_user_a_id UUID,
    p_user_b_id UUID
)
RETURNS TABLE (
    total_score FLOAT,
    matched_questions INTEGER,
    total_questions INTEGER,
    category_scores JSONB
) AS $$
DECLARE
    v_total_score FLOAT := 0.0;
    v_total_weight FLOAT := 0.0;
    v_matched_count INTEGER := 0;
    v_total_count INTEGER := 0;
    v_category_scores JSONB := '{}'::jsonb;
BEGIN
    WITH choice_matches AS (
        SELECT 
            q.category,
            q.base_weight,
            CASE 
                WHEN ua.answer_value = ub.answer_value THEN 1.0
                ELSE 0.0
            END as match_score
        FROM user_answers ua
        JOIN user_answers ub ON ua.question_id = ub.question_id
        JOIN questions q ON ua.question_id = q.id
        WHERE ua.user_id = p_user_a_id
          AND ub.user_id = p_user_b_id
          AND q.answer_type = 'choice'
    )
    SELECT 
        COALESCE(SUM(match_score * base_weight), 0.0),
        COALESCE(SUM(base_weight), 0.0),
        COUNT(*),
        COUNT(CASE WHEN match_score = 1.0 THEN 1 END)
    INTO v_total_score, v_total_weight, v_total_count, v_matched_count
    FROM choice_matches;
    
    RETURN QUERY
    SELECT 
        CASE WHEN v_total_weight > 0 THEN v_total_score / v_total_weight ELSE 0.5 END,
        v_matched_count,
        v_total_count,
        v_category_scores;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function: Update find_similar_profiles_v2 with Hybrid Algorithm
DROP FUNCTION IF EXISTS find_similar_profiles_v2(vector, UUID, INTEGER, VARCHAR, INTEGER, INTEGER);

CREATE OR REPLACE FUNCTION find_similar_profiles_v2(
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
    photos TEXT[],
    choice_score FLOAT,
    combined_score FLOAT,
    has_dealbreaker_conflict BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    WITH candidate_profiles AS (
        SELECT 
            p.user_id,
            p.profile_embedding_v2,
            p.nickname,
            p.birth_date,
            p.gender,
            p.photos,
            (1 - (p.profile_embedding_v2 <=> query_embedding))::FLOAT AS embedding_similarity
        FROM public.profiles p
        WHERE p.user_id != exclude_user_id
            AND p.is_active = TRUE
            AND p.profile_embedding_v2 IS NOT NULL
            AND (gender_filter IS NULL OR p.gender = gender_filter)
            AND (min_age IS NULL OR DATE_PART('year', AGE(p.birth_date)) >= min_age)
            AND (max_age IS NULL OR DATE_PART('year', AGE(p.birth_date)) <= max_age)
    ),
    choice_compatibility AS (
        SELECT 
            cp.user_id,
            COALESCE(
                (SELECT total_score FROM calculate_choice_compatibility(exclude_user_id, cp.user_id)),
                0.5
            ) as choice_score
        FROM candidate_profiles cp
    ),
    dealbreaker_check AS (
        SELECT 
            ub.user_id,
            COUNT(*) > 0 as has_conflict
        FROM user_answers ua
        JOIN user_answers ub ON ua.question_id = ub.question_id
        WHERE ua.user_id = exclude_user_id
          AND ua.is_dealbreaker = true
          AND ua.answer_value != ub.answer_value
        GROUP BY ub.user_id
    )
    SELECT 
        cp.user_id,
        cp.embedding_similarity as similarity,
        cp.nickname,
        cp.birth_date,
        cp.gender,
        cp.photos,
        cc.choice_score,
        (cc.choice_score * 0.5 + cp.embedding_similarity * 0.4 + 0.1)::FLOAT as combined_score,
        COALESCE(dc.has_conflict, false) as has_dealbreaker_conflict
    FROM candidate_profiles cp
    LEFT JOIN choice_compatibility cc ON cp.user_id = cc.user_id
    LEFT JOIN dealbreaker_check dc ON cp.user_id = dc.user_id
    WHERE COALESCE(dc.has_conflict, false) = false
    ORDER BY combined_score DESC
    LIMIT match_limit;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant Permissions
GRANT EXECUTE ON FUNCTION get_user_answers_with_metadata(UUID) TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION calculate_choice_compatibility(UUID, UUID) TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION find_similar_profiles_v2(vector, UUID, INTEGER, VARCHAR, INTEGER, INTEGER) TO authenticated, service_role;

-- Create Indexes for Performance
CREATE INDEX IF NOT EXISTS idx_user_answers_dealbreaker ON user_answers(question_id) WHERE is_dealbreaker = true;
CREATE INDEX IF NOT EXISTS idx_questions_answer_type ON questions(answer_type);

-- Update Documentation
COMMENT ON FUNCTION get_user_answers_with_metadata IS 
'Returns user answers with question metadata for matching algorithm';

COMMENT ON FUNCTION calculate_choice_compatibility IS 
'Calculates compatibility score based on choice-type questions with match_weight';

COMMENT ON FUNCTION find_similar_profiles_v2 IS 
'Hybrid matching algorithm - 50% choice questions + 40% embeddings + 10% bonus. Includes dealbreaker filtering.';