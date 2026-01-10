-- ==========================================
-- User Answers Table
-- Stores user responses to questions
-- ==========================================

CREATE TABLE IF NOT EXISTS public.user_answers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    question_id VARCHAR(100) NOT NULL REFERENCES public.questions(id) ON DELETE CASCADE,
    
    -- Answer data
    answer_value VARCHAR(100),  -- For choice questions
    answer_text TEXT,           -- For text questions
    importance INTEGER DEFAULT 3 CHECK (importance >= 1 AND importance <= 5),
    is_dealbreaker BOOLEAN DEFAULT false,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure one answer per question per user
    UNIQUE(user_id, question_id)
);

-- ==========================================
-- Question Performance Tracking
-- ==========================================

CREATE TABLE IF NOT EXISTS public.question_performance (
    question_id VARCHAR(100) PRIMARY KEY REFERENCES public.questions(id) ON DELETE CASCADE,
    total_answers INTEGER DEFAULT 0,
    avg_importance FLOAT DEFAULT 0.0,
    dealbreaker_count INTEGER DEFAULT 0,
    last_answered_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ==========================================
-- User Profiles for Embeddings
-- ==========================================

CREATE TABLE IF NOT EXISTS public.user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Profile embedding (1024D from Azure OpenAI)
    embedding vector(1024),
    profile_text TEXT,
    
    -- Metadata
    total_answers INTEGER DEFAULT 0,
    last_embedding_update TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ==========================================
-- User Feedback
-- ==========================================

CREATE TABLE IF NOT EXISTS public.user_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    feedback_type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ==========================================
-- Indexes
-- ==========================================

CREATE INDEX IF NOT EXISTS idx_user_answers_user_id ON public.user_answers(user_id);
CREATE INDEX IF NOT EXISTS idx_user_answers_question_id ON public.user_answers(question_id);
CREATE INDEX IF NOT EXISTS idx_user_answers_dealbreaker ON public.user_answers(is_dealbreaker) WHERE is_dealbreaker = true;

CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON public.user_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_profiles_embedding ON public.user_profiles USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_user_feedback_user_id ON public.user_feedback(user_id);

-- ==========================================
-- Row Level Security (RLS)
-- ==========================================

ALTER TABLE public.user_answers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.question_performance ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_feedback ENABLE ROW LEVEL SECURITY;

-- User Answers: Users can only see and manage their own answers
CREATE POLICY "Users can view own answers"
ON public.user_answers FOR SELECT
TO authenticated
USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own answers"
ON public.user_answers FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own answers"
ON public.user_answers FOR UPDATE
TO authenticated
USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own answers"
ON public.user_answers FOR DELETE
TO authenticated
USING (auth.uid() = user_id);

-- Question Performance: Read-only for all authenticated users
CREATE POLICY "Question performance is viewable by authenticated users"
ON public.question_performance FOR SELECT
TO authenticated
USING (true);

-- User Profiles: Users can only see and manage their own profile
CREATE POLICY "Users can view own profile"
ON public.user_profiles FOR SELECT
TO authenticated
USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own profile"
ON public.user_profiles FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own profile"
ON public.user_profiles FOR UPDATE
TO authenticated
USING (auth.uid() = user_id);

-- User Feedback: Users can only see and create their own feedback
CREATE POLICY "Users can view own feedback"
ON public.user_feedback FOR SELECT
TO authenticated
USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own feedback"
ON public.user_feedback FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = user_id);

-- ==========================================
-- Triggers
-- ==========================================

-- Update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER user_answers_updated_at
    BEFORE UPDATE ON public.user_answers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_timestamp();

CREATE TRIGGER user_profiles_updated_at
    BEFORE UPDATE ON public.user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_timestamp();

CREATE TRIGGER question_performance_updated_at
    BEFORE UPDATE ON public.question_performance
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_timestamp();

-- ==========================================
-- Helper Functions
-- ==========================================

-- Function to store user embedding
CREATE OR REPLACE FUNCTION store_user_embedding(
    p_user_id UUID,
    p_embedding vector(1024),
    p_profile_text TEXT,
    p_total_answers INTEGER DEFAULT 0
)
RETURNS BOOLEAN AS $$
BEGIN
    INSERT INTO public.user_profiles (user_id, embedding, profile_text, total_answers, last_embedding_update)
    VALUES (p_user_id, p_embedding, p_profile_text, p_total_answers, NOW())
    ON CONFLICT (user_id) 
    DO UPDATE SET
        embedding = p_embedding,
        profile_text = p_profile_text,
        total_answers = p_total_answers,
        last_embedding_update = NOW(),
        updated_at = NOW();
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant permissions
GRANT EXECUTE ON FUNCTION store_user_embedding(UUID, vector, TEXT, INTEGER) TO authenticated, service_role;

-- ==========================================
-- Documentation
-- ==========================================

COMMENT ON TABLE public.user_answers IS 
'Stores user responses to questions. One answer per question per user.';

COMMENT ON TABLE public.question_performance IS 
'Tracks question performance metrics for analytics.';

COMMENT ON TABLE public.user_profiles IS 
'Stores user profile embeddings (1024D) for AI matching.';

COMMENT ON TABLE public.user_feedback IS 
'User feedback and ratings for app improvement.';

COMMENT ON FUNCTION store_user_embedding IS 
'Stores or updates user profile embedding for AI matching.';
