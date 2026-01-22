-- ==========================================
-- FLIO User Answers & Feedback
-- ==========================================
-- Stores user answers and feedback
-- Note: Profile embeddings are in profiles.profile_embedding (migrations 001+002)
-- question_performance table is in migration 003
-- ==========================================

-- User answers table
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

-- Note: Profile embeddings are stored in profiles.profile_embedding (migration 001+002)
-- The user_profiles table has been removed as redundant

-- User feedback
CREATE TABLE IF NOT EXISTS public.user_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    feedback_type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ==========================================
-- INDEXES
-- ==========================================

CREATE INDEX IF NOT EXISTS idx_user_answers_user_id ON public.user_answers(user_id);
CREATE INDEX IF NOT EXISTS idx_user_answers_question_id ON public.user_answers(question_id);
CREATE INDEX IF NOT EXISTS idx_user_answers_dealbreaker ON public.user_answers(is_dealbreaker) WHERE is_dealbreaker = true;

CREATE INDEX IF NOT EXISTS idx_user_feedback_user_id ON public.user_feedback(user_id);

-- ==========================================
-- ROW LEVEL SECURITY
-- ==========================================

ALTER TABLE public.user_answers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_feedback ENABLE ROW LEVEL SECURITY;

-- User answers
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

-- User feedback
CREATE POLICY "Users can view own feedback"
ON public.user_feedback FOR SELECT
TO authenticated
USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own feedback"
ON public.user_feedback FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = user_id);

-- ==========================================
-- TRIGGERS
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

-- ==========================================
-- HELPER FUNCTIONS
-- ==========================================

-- Note: store_profile_embedding function is in migration 004
-- It updates profiles.profile_embedding instead of a separate user_profiles table

-- ==========================================
-- COMMENTS
-- ==========================================

COMMENT ON TABLE public.user_answers IS
'Stores user responses to questions. One answer per question per user.';

COMMENT ON TABLE public.user_feedback IS
'User feedback and ratings for app improvement.';
