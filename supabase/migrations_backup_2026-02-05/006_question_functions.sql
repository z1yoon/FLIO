-- ==========================================
-- FLIO Question Functions and Permissions
-- ==========================================
-- Description: Functions and RLS policies for question system
-- Consolidated from: 002_questions_and_answers.sql (lines 95-407)
-- ==========================================

-- ==========================================
-- FUNCTIONS
-- ==========================================

-- Get active question count
CREATE OR REPLACE FUNCTION get_active_question_count()
RETURNS INTEGER AS $$
BEGIN
    RETURN (SELECT COUNT(*) FROM questions);
END;
$$ LANGUAGE plpgsql STABLE;

-- Update question count trigger
CREATE OR REPLACE FUNCTION update_question_count()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO system_settings (key, value, updated_at)
    VALUES ('active_question_count', jsonb_build_object('count', (SELECT COUNT(*) FROM questions)), NOW())
    ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW();
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_question_count ON questions;
CREATE TRIGGER trigger_update_question_count
    AFTER INSERT OR DELETE ON questions
    FOR EACH STATEMENT EXECUTE FUNCTION update_question_count();

-- Update user_answers timestamp
CREATE TRIGGER user_answers_updated_at
    BEFORE UPDATE ON user_answers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- ==========================================
-- ROW LEVEL SECURITY
-- ==========================================

ALTER TABLE questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_answers ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_settings ENABLE ROW LEVEL SECURITY;

-- Questions (public read)
CREATE POLICY "Questions are viewable by all"
ON questions FOR SELECT
TO authenticated
USING (true);

-- User answers (private)
CREATE POLICY "Users can view own answers"
ON user_answers FOR SELECT
TO authenticated
USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own answers"
ON user_answers FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own answers"
ON user_answers FOR UPDATE
TO authenticated
USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own answers"
ON user_answers FOR DELETE
TO authenticated
USING (auth.uid() = user_id);

-- User feedback
CREATE POLICY "Users can view own feedback"
ON user_feedback FOR SELECT
TO authenticated
USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own feedback"
ON user_feedback FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = user_id);

-- System settings (public read)
CREATE POLICY "System settings are viewable by all"
ON system_settings FOR SELECT
TO authenticated
USING (true);

-- ==========================================
-- GRANT PERMISSIONS
-- ==========================================

GRANT SELECT ON questions TO authenticated;
GRANT SELECT ON system_settings TO authenticated;
GRANT EXECUTE ON FUNCTION get_active_question_count TO authenticated;
