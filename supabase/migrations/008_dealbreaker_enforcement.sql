-- ==========================================
-- Dealbreaker Enforcement for Matching
-- ==========================================
-- Migration: 008_dealbreaker_enforcement.sql
-- Description: Add hard filtering for dealbreaker questions in matching algorithm
-- Dependencies: 003_matching_and_tracking.sql
-- Date: 2026-02-06
-- ==========================================

-- ==========================================
-- PART 1: Dealbreaker Check Function
-- ==========================================

-- Check if two users violate each other's dealbreakers
-- Returns TRUE if compatible (no dealbreakers violated)
-- Returns FALSE if incompatible (dealbreaker violated)
CREATE OR REPLACE FUNCTION check_dealbreakers(
    p_user_a_id UUID,
    p_user_b_id UUID
)
RETURNS BOOLEAN AS $$
DECLARE
    v_compatible BOOLEAN := TRUE;
    v_a_gender VARCHAR(20);
    v_b_gender VARCHAR(20);
    v_a_age INTEGER;
    v_b_age INTEGER;
    v_a_answer RECORD;
    v_b_answer RECORD;
BEGIN
    -- Get basic demographics
    SELECT gender, DATE_PART('year', AGE(birth_date))::INTEGER
    INTO v_a_gender, v_a_age
    FROM profiles WHERE user_id = p_user_a_id;

    SELECT gender, DATE_PART('year', AGE(birth_date))::INTEGER
    INTO v_b_gender, v_b_age
    FROM profiles WHERE user_id = p_user_b_id;

    -- DEALBREAKER 1: Gender preference (Q001)
    -- Check if A's gender preference matches B's gender (if marked as dealbreaker)
    SELECT answer_value, is_dealbreaker INTO v_a_answer
    FROM user_answers
    WHERE user_id = p_user_a_id AND question_id = 'Q001';

    IF FOUND AND v_a_answer.is_dealbreaker = TRUE THEN
        IF v_a_answer.answer_value != v_b_gender THEN
            RETURN FALSE;  -- Gender mismatch is dealbreaker
        END IF;
    END IF;

    -- Check if B's gender preference matches A's gender
    SELECT answer_value, is_dealbreaker INTO v_b_answer
    FROM user_answers
    WHERE user_id = p_user_b_id AND question_id = 'Q001';

    IF FOUND AND v_b_answer.is_dealbreaker = TRUE THEN
        IF v_b_answer.answer_value != v_a_gender THEN
            RETURN FALSE;  -- Gender mismatch is dealbreaker
        END IF;
    END IF;

    -- DEALBREAKER 2: Age range (Q002)
    -- Check if B's age is within A's acceptable range (if marked as dealbreaker)
    SELECT answer_value, is_dealbreaker INTO v_a_answer
    FROM user_answers
    WHERE user_id = p_user_a_id AND question_id = 'Q002';

    IF FOUND AND v_a_answer.is_dealbreaker = TRUE THEN
        -- Parse age range (e.g., "25-30" or "30-35")
        DECLARE
            v_min_age INTEGER;
            v_max_age INTEGER;
            v_age_parts TEXT[];
        BEGIN
            v_age_parts := string_to_array(v_a_answer.answer_value, '-');
            IF array_length(v_age_parts, 1) = 2 THEN
                v_min_age := v_age_parts[1]::INTEGER;
                v_max_age := v_age_parts[2]::INTEGER;
                IF v_b_age < v_min_age OR v_b_age > v_max_age THEN
                    RETURN FALSE;  -- Age out of range
                END IF;
            END IF;
        END;
    END IF;

    -- Check if A's age is within B's acceptable range
    SELECT answer_value, is_dealbreaker INTO v_b_answer
    FROM user_answers
    WHERE user_id = p_user_b_id AND question_id = 'Q002';

    IF FOUND AND v_b_answer.is_dealbreaker = TRUE THEN
        DECLARE
            v_min_age INTEGER;
            v_max_age INTEGER;
            v_age_parts TEXT[];
        BEGIN
            v_age_parts := string_to_array(v_b_answer.answer_value, '-');
            IF array_length(v_age_parts, 1) = 2 THEN
                v_min_age := v_age_parts[1]::INTEGER;
                v_max_age := v_age_parts[2]::INTEGER;
                IF v_a_age < v_min_age OR v_a_age > v_max_age THEN
                    RETURN FALSE;  -- Age out of range
                END IF;
            END IF;
        END;
    END IF;

    -- DEALBREAKER 3: Divorce status (Q003)
    -- Check if A accepts B's divorce status (if marked as dealbreaker)
    SELECT answer_value, is_dealbreaker INTO v_a_answer
    FROM user_answers
    WHERE user_id = p_user_a_id AND question_id = 'Q003';

    IF FOUND AND v_a_answer.is_dealbreaker = TRUE THEN
        SELECT answer_value INTO v_b_answer
        FROM user_answers
        WHERE user_id = p_user_b_id AND question_id = 'Q003';

        IF FOUND THEN
            -- If A doesn't accept divorce ('없음') but B is divorced
            IF v_a_answer.answer_value = '없음' AND v_b_answer.answer_value != '없음' THEN
                RETURN FALSE;
            END IF;
        END IF;
    END IF;

    -- Check if B accepts A's divorce status
    SELECT answer_value, is_dealbreaker INTO v_b_answer
    FROM user_answers
    WHERE user_id = p_user_b_id AND question_id = 'Q003';

    IF FOUND AND v_b_answer.is_dealbreaker = TRUE THEN
        SELECT answer_value INTO v_a_answer
        FROM user_answers
        WHERE user_id = p_user_a_id AND question_id = 'Q003';

        IF FOUND THEN
            IF v_b_answer.answer_value = '없음' AND v_a_answer.answer_value != '없음' THEN
                RETURN FALSE;
            END IF;
        END IF;
    END IF;

    -- DEALBREAKER 4: Disability acceptance (Q004)
    -- Check if A accepts disability and B has disability (if marked as dealbreaker)
    SELECT answer_value, is_dealbreaker INTO v_a_answer
    FROM user_answers
    WHERE user_id = p_user_a_id AND question_id = 'Q004';

    IF FOUND AND v_a_answer.is_dealbreaker = TRUE THEN
        SELECT answer_value INTO v_b_answer
        FROM user_answers
        WHERE user_id = p_user_b_id AND question_id = 'Q004';

        IF FOUND THEN
            -- If A doesn't accept disability but B has disability
            IF v_a_answer.answer_value = '아니요' AND v_b_answer.answer_value = '예' THEN
                RETURN FALSE;
            END IF;
        END IF;
    END IF;

    -- Check if B accepts disability and A has disability
    SELECT answer_value, is_dealbreaker INTO v_b_answer
    FROM user_answers
    WHERE user_id = p_user_b_id AND question_id = 'Q004';

    IF FOUND AND v_b_answer.is_dealbreaker = TRUE THEN
        SELECT answer_value INTO v_a_answer
        FROM user_answers
        WHERE user_id = p_user_a_id AND question_id = 'Q004';

        IF FOUND THEN
            IF v_b_answer.answer_value = '아니요' AND v_a_answer.answer_value = '예' THEN
                RETURN FALSE;
            END IF;
        END IF;
    END IF;

    -- All dealbreaker checks passed
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- ==========================================
-- PART 2: Update find_matches Function
-- ==========================================

-- Update the find_matches function to include dealbreaker filtering
-- Note: This assumes find_matches function exists in migration 003
-- Add this as an additional WHERE clause in the existing function

COMMENT ON FUNCTION check_dealbreakers IS 'Enforces hard filtering for 4 dealbreaker questions: Gender (Q001), Age (Q002), Divorce (Q003), Disability (Q004). Returns FALSE if any dealbreaker is violated.';

-- ==========================================
-- PART 3: Add Dealbreaker Statistics
-- ==========================================

-- Track how many matches are filtered due to dealbreakers
CREATE TABLE IF NOT EXISTS dealbreaker_filter_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    filtered_user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    dealbreaker_type VARCHAR(50) NOT NULL CHECK (dealbreaker_type IN ('gender', 'age', 'divorce', 'disability')),
    user_answer_value TEXT,
    filtered_user_answer_value TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dealbreaker_stats_user ON dealbreaker_filter_stats(user_id);
CREATE INDEX IF NOT EXISTS idx_dealbreaker_stats_type ON dealbreaker_filter_stats(dealbreaker_type);
CREATE INDEX IF NOT EXISTS idx_dealbreaker_stats_created ON dealbreaker_filter_stats(created_at);

-- ==========================================
-- PART 4: Helper Function - Get Dealbreaker Summary
-- ==========================================

-- Get summary of dealbreaker filtering for analytics
CREATE OR REPLACE FUNCTION get_dealbreaker_summary(p_user_id UUID)
RETURNS JSONB AS $$
DECLARE
    v_total_filtered INTEGER;
    v_by_type JSONB;
BEGIN
    SELECT COUNT(*) INTO v_total_filtered
    FROM dealbreaker_filter_stats
    WHERE user_id = p_user_id;

    SELECT jsonb_object_agg(dealbreaker_type, count)
    INTO v_by_type
    FROM (
        SELECT dealbreaker_type, COUNT(*) as count
        FROM dealbreaker_filter_stats
        WHERE user_id = p_user_id
        GROUP BY dealbreaker_type
    ) sub;

    RETURN jsonb_build_object(
        'user_id', p_user_id,
        'total_filtered', COALESCE(v_total_filtered, 0),
        'by_type', COALESCE(v_by_type, '{}'::jsonb)
    );
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- ==========================================
-- PART 5: Grants
-- ==========================================

GRANT EXECUTE ON FUNCTION check_dealbreakers TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION get_dealbreaker_summary TO authenticated, service_role;

-- ==========================================
-- PART 6: Comments
-- ==========================================

COMMENT ON TABLE dealbreaker_filter_stats IS 'Tracks how many potential matches were filtered due to dealbreaker violations. Useful for analytics and showing users why their match pool is limited.';
COMMENT ON FUNCTION get_dealbreaker_summary IS 'Get dealbreaker filtering statistics for a user. Shows how many matches were filtered and by which dealbreaker type.';
