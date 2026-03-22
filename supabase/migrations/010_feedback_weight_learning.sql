-- ==========================================
-- FLIO Feedback-Based Weight Learning
-- ==========================================
-- Migration: 010_feedback_weight_learning.sql
-- Description: Per-user question weights learned from reshuffle feedback.
--              Drives Pearson-based personalized matching.
-- Dependencies: 001, 002
-- ==========================================

-- ==========================================
-- TABLE: user_question_weights
-- ==========================================
-- Stores per-user learned importance weight for each question.
-- Default weight = 1.0 (equal). Increases when a question dimension
-- repeatedly correlates with rejection; decreases when user seems indifferent.

CREATE TABLE IF NOT EXISTS user_question_weights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    question_id TEXT NOT NULL,

    -- Learned weight multiplier applied on top of static score
    -- Range: 0.1 (user doesn't care) → 3.0 (user cares a lot)
    weight FLOAT NOT NULL DEFAULT 1.0
        CHECK (weight >= 0.1 AND weight <= 3.0),

    -- How many reshuffle feedback sessions contributed to this weight
    feedback_count INTEGER NOT NULL DEFAULT 0,

    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_user_question_weight UNIQUE (user_id, question_id)
);

CREATE INDEX idx_uqw_user_id ON user_question_weights(user_id);
CREATE INDEX idx_uqw_user_question ON user_question_weights(user_id, question_id);

CREATE TRIGGER uqw_updated_at
    BEFORE UPDATE ON user_question_weights
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

COMMENT ON TABLE user_question_weights IS
    'Per-user learned question weights updated from reshuffle feedback. '
    'Used by matching engine to personalize static question score calculation.';

-- ==========================================
-- RLS
-- ==========================================

ALTER TABLE user_question_weights ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users view own question weights"
ON user_question_weights FOR SELECT TO authenticated
USING (auth.uid() = user_id);

CREATE POLICY "Service role manages question weights"
ON user_question_weights FOR ALL TO service_role
USING (true) WITH CHECK (true);
