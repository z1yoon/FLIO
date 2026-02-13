-- ==========================================
-- FLIO Questions Schema
-- ==========================================
-- Description: Tables for questions, user answers, feedback, and system settings
-- Consolidated from: 002_questions_and_answers.sql (lines 8-93)
-- ==========================================

-- Drop old tables if they exist
DROP TABLE IF EXISTS question_performance CASCADE;
DROP TABLE IF EXISTS user_answers CASCADE;
DROP TABLE IF EXISTS user_feedback CASCADE;
DROP TABLE IF EXISTS questions CASCADE;
DROP TABLE IF EXISTS system_settings CASCADE;

-- ==========================================
-- QUESTIONS TABLE
-- ==========================================

CREATE TABLE questions (
    id VARCHAR(100) PRIMARY KEY,
    category VARCHAR(50) NOT NULL,
    text_ko TEXT NOT NULL,
    text_en TEXT NOT NULL,
    answer_type VARCHAR(50) NOT NULL,
    options JSONB NOT NULL,
    base_weight FLOAT DEFAULT 0.5,
    effectiveness_score FLOAT DEFAULT 5.0,
    can_be_dealbreaker BOOLEAN DEFAULT false,
    tags TEXT[],
    placeholder TEXT,
    max_length INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_questions_category ON questions(category);
CREATE INDEX idx_questions_weight ON questions(base_weight DESC);
CREATE INDEX idx_questions_answer_type ON questions(answer_type);

-- ==========================================
-- USER ANSWERS TABLE
-- ==========================================

CREATE TABLE user_answers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    question_id VARCHAR(100) NOT NULL REFERENCES questions(id) ON DELETE CASCADE,

    -- Answer data
    answer_value VARCHAR(100),  -- For choice questions
    answer_text TEXT,           -- For text questions
    importance INTEGER DEFAULT 3 CHECK (importance >= 1 AND importance <= 5),
    is_dealbreaker BOOLEAN DEFAULT false,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- One answer per question per user
    UNIQUE(user_id, question_id)
);

CREATE INDEX idx_user_answers_user_id ON user_answers(user_id);
CREATE INDEX idx_user_answers_question_id ON user_answers(question_id);
CREATE INDEX idx_user_answers_dealbreaker ON user_answers(is_dealbreaker) WHERE is_dealbreaker = true;

-- ==========================================
-- USER FEEDBACK TABLE
-- ==========================================

CREATE TABLE user_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    feedback_type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_user_feedback_user_id ON user_feedback(user_id);

-- ==========================================
-- SYSTEM SETTINGS TABLE
-- ==========================================

CREATE TABLE system_settings (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==========================================
-- COMMENTS
-- ==========================================

COMMENT ON TABLE questions IS '40 research-based questions (35 choice + 5 text) for matching compatibility';
COMMENT ON TABLE user_answers IS 'User responses to questions with importance ratings';
COMMENT ON TABLE user_feedback IS 'General app feedback from users';
COMMENT ON COLUMN questions.can_be_dealbreaker IS 'True = exact match filtering, False = weighted scoring';
