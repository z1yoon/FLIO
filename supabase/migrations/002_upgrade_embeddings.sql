-- FLIO Database Migration: Upgrade to BGE-M3 (1024D) embeddings
-- This migration upgrades profile embeddings from 768D (ko-sroberta) to 1024D (BGE-M3)

-- Step 1: Add new 1024D column for BGE-M3 embeddings
ALTER TABLE public.profiles 
ADD COLUMN IF NOT EXISTS profile_embedding_v2 vector(1024);

-- Step 2: Add reshuffle history table
-- Tracks when users reshuffle and why (for AI analysis)
CREATE TABLE IF NOT EXISTS public.reshuffle_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Reason categories
    reason_category VARCHAR(50) NOT NULL,
    reason_text TEXT,
    
    -- AI analysis results
    ai_analysis JSONB DEFAULT '{}',
    suggested_questions JSONB DEFAULT '[]',
    filter_changes JSONB DEFAULT '{}',
    
    -- Whether user answered additional questions
    questions_answered BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Step 3: Add profile answer history table
-- Tracks all answers for adaptive questioning
CREATE TABLE IF NOT EXISTS public.answer_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Question context
    question_text TEXT NOT NULL,
    category VARCHAR(50) NOT NULL,
    
    -- Answer details
    answer_text TEXT NOT NULL,
    
    -- AI analysis
    clarity_score INTEGER,
    sentiment VARCHAR(20),
    key_info JSONB DEFAULT '[]',
    is_vague BOOLEAN DEFAULT FALSE,
    
    -- If this triggered follow-up questions
    triggered_followup BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Step 4: Create index for new embedding column
CREATE INDEX IF NOT EXISTS idx_profiles_embedding_v2 
ON public.profiles 
USING ivfflat (profile_embedding_v2 vector_cosine_ops)
WITH (lists = 100);

-- Step 5: Create indexes for new tables
CREATE INDEX IF NOT EXISTS idx_reshuffle_user ON public.reshuffle_history(user_id);
CREATE INDEX IF NOT EXISTS idx_reshuffle_created ON public.reshuffle_history(created_at);

CREATE INDEX IF NOT EXISTS idx_answer_user ON public.answer_history(user_id);
CREATE INDEX IF NOT EXISTS idx_answer_category ON public.answer_history(category);
CREATE INDEX IF NOT EXISTS idx_answer_vague ON public.answer_history(is_vague);

-- Step 6: Enable RLS on new tables
ALTER TABLE public.reshuffle_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.answer_history ENABLE ROW LEVEL SECURITY;

-- RLS policies for reshuffle_history
CREATE POLICY "Users can view own reshuffle history"
ON public.reshuffle_history FOR SELECT
TO authenticated
USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own reshuffle history"
ON public.reshuffle_history FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = user_id);

-- RLS policies for answer_history
CREATE POLICY "Users can view own answer history"
ON public.answer_history FOR SELECT
TO authenticated
USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own answer history"
ON public.answer_history FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = user_id);

-- Step 7: Update find_similar_profiles function for 1024D
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
    face_verified BOOLEAN,
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
        p.face_verified,
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

-- Step 8: Function to get user's question clarity stats
CREATE OR REPLACE FUNCTION get_answer_quality_stats(target_user_id UUID)
RETURNS TABLE (
    total_answers INTEGER,
    avg_clarity FLOAT,
    vague_percentage FLOAT,
    categories_answered TEXT[]
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::INTEGER AS total_answers,
        AVG(ah.clarity_score)::FLOAT AS avg_clarity,
        (SUM(CASE WHEN ah.is_vague THEN 1 ELSE 0 END)::FLOAT / COUNT(*)::FLOAT * 100)::FLOAT AS vague_percentage,
        ARRAY_AGG(DISTINCT ah.category)::TEXT[] AS categories_answered
    FROM public.answer_history ah
    WHERE ah.user_id = target_user_id
    GROUP BY ah.user_id;
END;
$$ LANGUAGE plpgsql;

-- Step 9: Function to get reshuffle patterns (for AI improvement)
CREATE OR REPLACE FUNCTION get_reshuffle_patterns(target_user_id UUID)
RETURNS TABLE (
    total_reshuffles INTEGER,
    common_reasons TEXT[],
    last_reshuffle TIMESTAMP WITH TIME ZONE,
    avg_questions_answered FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::INTEGER AS total_reshuffles,
        ARRAY_AGG(DISTINCT rh.reason_category)::TEXT[] AS common_reasons,
        MAX(rh.created_at) AS last_reshuffle,
        AVG(CASE WHEN rh.questions_answered THEN 1.0 ELSE 0.0 END)::FLOAT AS avg_questions_answered
    FROM public.reshuffle_history rh
    WHERE rh.user_id = target_user_id
    GROUP BY rh.user_id;
END;
$$ LANGUAGE plpgsql;

-- Step 10: Add comment for documentation
COMMENT ON COLUMN public.profiles.profile_embedding_v2 IS 
'BGE-M3 1024D embedding for profile matching. Replaces 768D ko-sroberta embedding.';

COMMENT ON TABLE public.reshuffle_history IS 
'Tracks user reshuffle requests for AI-driven matching improvement.';

COMMENT ON TABLE public.answer_history IS 
'Stores all profile answers with AI analysis for adaptive questioning.';
