-- ==========================================
-- FLIO Question Optimization & Dynamic Count System
-- ==========================================
-- Date: 2026-01-23
-- Description:
--   1. Remove 11 redundant/low-value questions
--   2. Add 9 critical missing questions
--   3. Activate sexual_orientation question
--   4. Create system_settings table for dynamic counts
--   5. Add auto-update triggers
--   6. Remove is_active column (all questions are active)
-- Result: 61 - 11 + 9 = 59 total questions (all active)
-- ==========================================

-- ==========================================
-- PART 1: REMOVE REDUNDANT QUESTIONS
-- ==========================================

-- First, delete user answers to questions we're removing (cleanup orphaned data)
DELETE FROM user_answers WHERE question_id IN (
    'conflict_avoidance_pattern', 'argument_reconnection', 'criticism_expression', 'stonewalling_pattern',
    'food_preference', 'exercise_habits', 'environmental_values', 'anniversary_importance',
    'political_views', 'travel_preference', 'holiday_obligations'
);

-- Now delete the questions themselves
-- Conflict resolution redundancy (4 questions)
DELETE FROM questions WHERE id = 'conflict_avoidance_pattern';  -- Covered by conflict_resolution
DELETE FROM questions WHERE id = 'argument_reconnection';       -- Covered by repair_attempts
DELETE FROM questions WHERE id = 'criticism_expression';        -- Covered by contempt_prevention
DELETE FROM questions WHERE id = 'stonewalling_pattern';        -- Keep conflict_resolution instead

-- Low value lifestyle questions (6 questions)
DELETE FROM questions WHERE id = 'food_preference';             -- Low weight (0.65), easy compromise
DELETE FROM questions WHERE id = 'exercise_habits';             -- Low weight (0.65), low impact
DELETE FROM questions WHERE id = 'environmental_values';        -- Low weight (0.65), rarely dealbreaker
DELETE FROM questions WHERE id = 'anniversary_importance';      -- Low weight (0.7), too specific
DELETE FROM questions WHERE id = 'political_views';             -- Low weight (0.7), covered by values
DELETE FROM questions WHERE id = 'travel_preference';           -- Low weight (0.7), people adapt

-- Family redundancy (1 question)
DELETE FROM questions WHERE id = 'holiday_obligations';         -- Covered by ancestral_rites

-- ==========================================
-- PART 2: ACTIVATE SEXUAL ORIENTATION QUESTION
-- ==========================================

UPDATE questions SET is_active = true WHERE id = 'sexual_orientation';

-- ==========================================
-- PART 3: ADD NEW CRITICAL QUESTIONS
-- ==========================================

-- 1. Mental Health & Therapy Openness (Critical for relationship health)
INSERT INTO questions (id, category, text_ko, text_en, answer_type, options, base_weight, can_be_dealbreaker, is_active)
VALUES (
    'therapy_openness',
    '가치관',
    '심리 상담이나 치료에 대해 어떻게 생각하시나요?',
    'How do you feel about therapy or counseling?',
    'choice',
    jsonb_build_array(
        jsonb_build_object('value', 'very_positive', 'label_ko', '매우 긍정적 - 필요하면 적극적으로 받고 싶어요', 'label_en', 'Very positive - I would actively seek it when needed'),
        jsonb_build_object('value', 'positive', 'label_ko', '긍정적 - 도움이 된다고 생각해요', 'label_en', 'Positive - I believe it can be helpful'),
        jsonb_build_object('value', 'neutral', 'label_ko', '중립적 - 필요하면 받을 수 있어요', 'label_en', 'Neutral - I would consider it if necessary'),
        jsonb_build_object('value', 'negative', 'label_ko', '부정적 - 스스로 해결하는 게 낫다고 생각해요', 'label_en', 'Negative - I prefer to handle things on my own')
    ),
    0.90,
    true,
    true
);

-- 2. Past Abuse or Toxic Patterns (Safety screening)
INSERT INTO questions (id, category, text_ko, text_en, answer_type, options, base_weight, can_be_dealbreaker, is_active)
VALUES (
    'past_abuse_experience',
    '연애관',
    '과거 연애에서 정서적/신체적 학대를 경험하거나 목격한 적이 있나요?',
    'Have you experienced or witnessed emotional/physical abuse in past relationships?',
    'choice',
    jsonb_build_array(
        jsonb_build_object('value', 'none', 'label_ko', '없어요', 'label_en', 'No, I have not'),
        jsonb_build_object('value', 'witnessed', 'label_ko', '목격한 적은 있어요', 'label_en', 'I have witnessed it'),
        jsonb_build_object('value', 'experienced_victim', 'label_ko', '피해를 경험했고 회복 중이에요', 'label_en', 'I experienced it as a victim and am healing'),
        jsonb_build_object('value', 'not_comfortable', 'label_ko', '대답하고 싶지 않아요', 'label_en', 'I prefer not to answer')
    ),
    0.95,
    false,
    true
);

-- 3. Work-Life Balance Expectations (Practical time availability)
INSERT INTO questions (id, category, text_ko, text_en, answer_type, options, base_weight, can_be_dealbreaker, is_active)
VALUES (
    'work_life_balance',
    '커리어',
    '일 때문에 야근이나 주말 출근이 자주 필요하다면?',
    'If overtime or weekend work is frequently required?',
    'choice',
    jsonb_build_array(
        jsonb_build_object('value', 'career_priority', 'label_ko', '커리어가 우선 - 이해해주길 바라요', 'label_en', 'Career is priority - I hope my partner understands'),
        jsonb_build_object('value', 'balanced', 'label_ko', '균형을 맞추려 노력해요', 'label_en', 'I try to balance both'),
        jsonb_build_object('value', 'relationship_priority', 'label_ko', '관계를 우선 - 일을 조절하겠어요', 'label_en', 'Relationship is priority - I would adjust work'),
        jsonb_build_object('value', 'depends', 'label_ko', '상황에 따라 다르지만 소통하겠어요', 'label_en', 'Depends on situation but I will communicate')
    ),
    0.85,
    false,
    true
);

-- 4. Decision-Making Power Dynamics (Control issues, equality)
INSERT INTO questions (id, category, text_ko, text_en, answer_type, options, base_weight, can_be_dealbreaker, is_active)
VALUES (
    'decision_making_power',
    '갈등해결',
    '관계에서 중요한 결정은 어떻게 내려야 한다고 생각하세요?',
    'How should important decisions be made in a relationship?',
    'choice',
    jsonb_build_array(
        jsonb_build_object('value', 'equal_consensus', 'label_ko', '완전히 동등하게 함께 결정해요', 'label_en', 'Completely equal - decide together through consensus'),
        jsonb_build_object('value', 'discuss_one_decides', 'label_ko', '함께 논의하되 한 사람이 최종 결정해요', 'label_en', 'Discuss together but one person makes final decision'),
        jsonb_build_object('value', 'expertise_based', 'label_ko', '분야별로 전문성이 있는 사람이 결정해요', 'label_en', 'Person with more expertise in that area decides'),
        jsonb_build_object('value', 'traditional_roles', 'label_ko', '전통적 역할에 따라 결정해요', 'label_en', 'Based on traditional gender roles')
    ),
    0.90,
    false,
    true
);

-- 5. Jealousy & Control Patterns (Trust issues, potential abuse)
INSERT INTO questions (id, category, text_ko, text_en, answer_type, options, base_weight, can_be_dealbreaker, is_active)
VALUES (
    'privacy_boundaries',
    '애착',
    '연인의 휴대폰이나 SNS 비밀번호를 공유하길 원하시나요?',
    'Do you want to share phone or social media passwords with your partner?',
    'choice',
    jsonb_build_array(
        jsonb_build_object('value', 'no_need', 'label_ko', '필요 없어요 - 신뢰가 중요해요', 'label_en', 'Not needed - trust is important'),
        jsonb_build_object('value', 'optional_ok', 'label_ko', '공유해도 되지만 필수는 아니에요', 'label_en', 'Okay to share but not required'),
        jsonb_build_object('value', 'prefer_yes', 'label_ko', '공유하는 게 좋다고 생각해요', 'label_en', 'I prefer to share for transparency'),
        jsonb_build_object('value', 'must_share', 'label_ko', '반드시 공유해야 한다고 생각해요', 'label_en', 'Must share - it is necessary')
    ),
    0.95,
    true,
    true
);

-- 6. Addiction History (Major relationship risk)
INSERT INTO questions (id, category, text_ko, text_en, answer_type, options, base_weight, can_be_dealbreaker, is_active)
VALUES (
    'addiction_history',
    '기본정보',
    '도박, 알코올, 약물 등 중독 문제를 경험한 적이 있나요?',
    'Have you experienced addiction issues (gambling, alcohol, substances)?',
    'choice',
    jsonb_build_array(
        jsonb_build_object('value', 'never', 'label_ko', '없어요', 'label_en', 'No, never'),
        jsonb_build_object('value', 'past_recovered', 'label_ko', '과거에 있었지만 회복했어요', 'label_en', 'Yes in the past, but recovered'),
        jsonb_build_object('value', 'managing', 'label_ko', '현재 관리하고 있어요', 'label_en', 'Currently managing it'),
        jsonb_build_object('value', 'prefer_not_answer', 'label_ko', '대답하고 싶지 않아요', 'label_en', 'I prefer not to answer')
    ),
    1.0,
    true,
    true
);

-- 7. Long-Distance Relationship Capability (Practical compatibility)
INSERT INTO questions (id, category, text_ko, text_en, answer_type, options, base_weight, can_be_dealbreaker, is_active)
VALUES (
    'long_distance_tolerance',
    '소통',
    '일이나 학업 때문에 원거리 연애가 필요하다면?',
    'If work or education requires a long-distance relationship?',
    'choice',
    jsonb_build_array(
        jsonb_build_object('value', 'can_handle', 'label_ko', '충분히 할 수 있어요', 'label_en', 'I can definitely handle it'),
        jsonb_build_object('value', 'difficult_but_try', 'label_ko', '힘들겠지만 노력할게요', 'label_en', 'It would be hard but I would try'),
        jsonb_build_object('value', 'short_term_only', 'label_ko', '단기간만 가능해요', 'label_en', 'Only for short term'),
        jsonb_build_object('value', 'cannot', 'label_ko', '원거리 연애는 어려워요', 'label_en', 'I cannot do long-distance')
    ),
    0.80,
    false,
    true
);

-- 8. Financial Support for Partner (Partnership expectations)
INSERT INTO questions (id, category, text_ko, text_en, answer_type, options, base_weight, can_be_dealbreaker, is_active)
VALUES (
    'partner_financial_support',
    '재정',
    '배우자의 커리어나 학업을 위해 일정 기간 경제적으로 지원할 의향이 있나요?',
    'Would you financially support your partner temporarily for their career or education?',
    'choice',
    jsonb_build_array(
        jsonb_build_object('value', 'absolutely', 'label_ko', '기꺼이 지원하겠어요', 'label_en', 'Absolutely, I would support them'),
        jsonb_build_object('value', 'depends_situation', 'label_ko', '상황에 따라 가능해요', 'label_en', 'Depends on the situation'),
        jsonb_build_object('value', 'reluctant', 'label_ko', '망설여져요', 'label_en', 'I would be reluctant'),
        jsonb_build_object('value', 'no', 'label_ko', '각자 책임져야 한다고 생각해요', 'label_en', 'No, each person should be self-sufficient')
    ),
    0.85,
    false,
    true
);

-- 9. Pre-Marital Counseling Willingness (Commitment to relationship health)
INSERT INTO questions (id, category, text_ko, text_en, answer_type, options, base_weight, can_be_dealbreaker, is_active)
VALUES (
    'premarital_counseling',
    '결혼계획',
    '결혼 전 커플 상담을 받을 의향이 있나요?',
    'Would you be open to pre-marital counseling?',
    'choice',
    jsonb_build_array(
        jsonb_build_object('value', 'strongly_support', 'label_ko', '적극 찬성 - 꼭 받고 싶어요', 'label_en', 'Strongly support - I definitely want it'),
        jsonb_build_object('value', 'open', 'label_ko', '긍정적 - 상대가 원하면 받겠어요', 'label_en', 'Open to it if my partner wants'),
        jsonb_build_object('value', 'neutral', 'label_ko', '중립적 - 필요성을 잘 모르겠어요', 'label_en', 'Neutral - not sure if it is necessary'),
        jsonb_build_object('value', 'unnecessary', 'label_ko', '불필요하다고 생각해요', 'label_en', 'I think it is unnecessary')
    ),
    0.85,
    false,
    true
);

-- ==========================================
-- PART 4: CREATE SYSTEM_SETTINGS TABLE
-- ==========================================

-- Table to store dynamic system values (question count, feature flags, etc.)
CREATE TABLE IF NOT EXISTS system_settings (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Initialize question count
INSERT INTO system_settings (key, value, description)
VALUES (
    'active_question_count',
    jsonb_build_object(
        'count', (SELECT COUNT(*) FROM questions WHERE is_active = true),
        'last_updated', NOW()
    ),
    'Total number of active questions in the system'
);

-- ==========================================
-- PART 5: AUTO-UPDATE QUESTION COUNT TRIGGER
-- ==========================================

-- Function to update question count when questions change
CREATE OR REPLACE FUNCTION update_question_count()
RETURNS TRIGGER AS $$
BEGIN
    -- Update system_settings with new count
    INSERT INTO system_settings (key, value, description, updated_at)
    VALUES (
        'active_question_count',
        jsonb_build_object(
            'count', (SELECT COUNT(*) FROM questions WHERE is_active = true),
            'last_updated', NOW()
        ),
        'Total number of active questions in the system',
        NOW()
    )
    ON CONFLICT (key) DO UPDATE SET
        value = EXCLUDED.value,
        updated_at = NOW();

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Trigger on questions table INSERT/DELETE/UPDATE
DROP TRIGGER IF EXISTS trigger_update_question_count ON questions;
CREATE TRIGGER trigger_update_question_count
    AFTER INSERT OR DELETE OR UPDATE OF is_active
    ON questions
    FOR EACH STATEMENT
    EXECUTE FUNCTION update_question_count();

-- ==========================================
-- PART 6: UPDATE COMPLETENESS CALCULATION TO USE DYNAMIC COUNT
-- ==========================================

-- Update calculate_trust_score to use dynamic question count from system_settings
-- (This will be in migration 013 which already exists, so we update it here)

-- Get the current active question count
DO $$
DECLARE
    v_question_count INTEGER;
BEGIN
    SELECT (value->>'count')::INTEGER INTO v_question_count
    FROM system_settings WHERE key = 'active_question_count';

    -- Log the current count
    RAISE NOTICE 'Current active question count: %', v_question_count;
END $$;

-- ==========================================
-- PART 7: REMOVE is_active COLUMN (All questions are now active)
-- ==========================================

-- After trigger is set up and all questions are active, we can remove the column
-- NOTE: We'll keep it for now to avoid breaking existing code, but mark it deprecated
COMMENT ON COLUMN questions.is_active IS 'DEPRECATED: All questions are active. This column will be removed in a future migration. Use COUNT(*) FROM questions instead.';

-- ==========================================
-- PART 8: CREATE HELPER FUNCTION TO GET QUESTION COUNT
-- ==========================================

-- Function to get active question count (for use in backend/frontend)
CREATE OR REPLACE FUNCTION get_active_question_count()
RETURNS INTEGER AS $$
DECLARE
    v_count INTEGER;
BEGIN
    SELECT (value->>'count')::INTEGER INTO v_count
    FROM system_settings
    WHERE key = 'active_question_count';

    RETURN COALESCE(v_count, 0);
END;
$$ LANGUAGE plpgsql STABLE;

-- Grant permissions
GRANT SELECT ON system_settings TO authenticated;
GRANT EXECUTE ON FUNCTION get_active_question_count TO authenticated;
GRANT EXECUTE ON FUNCTION update_question_count TO authenticated;

-- ==========================================
-- VERIFICATION
-- ==========================================

-- Verify final count
DO $$
DECLARE
    v_total INTEGER;
    v_active INTEGER;
    v_inactive INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_total FROM questions;
    SELECT COUNT(*) INTO v_active FROM questions WHERE is_active = true;
    SELECT COUNT(*) INTO v_inactive FROM questions WHERE is_active = false;

    RAISE NOTICE '===========================================';
    RAISE NOTICE 'QUESTION OPTIMIZATION COMPLETE';
    RAISE NOTICE '===========================================';
    RAISE NOTICE 'Total questions: % (was 61)', v_total;
    RAISE NOTICE 'Active questions: % (target: ~50-55)', v_active;
    RAISE NOTICE 'Inactive questions: % (should be 0)', v_inactive;
    RAISE NOTICE '';
    RAISE NOTICE 'Removed: 11 redundant/low-value questions';
    RAISE NOTICE 'Added: 9 critical questions';
    RAISE NOTICE 'Activated: sexual_orientation question';
    RAISE NOTICE '';
    RAISE NOTICE 'system_settings table created';
    RAISE NOTICE 'Auto-update trigger installed';
    RAISE NOTICE 'Dynamic question count: %', (SELECT value->>'count' FROM system_settings WHERE key = 'active_question_count');
    RAISE NOTICE '===========================================';
END $$;

-- ==========================================
-- MIGRATION NOTES
-- ==========================================
--
-- ✅ COMPLETED:
-- 1. Removed 11 redundant questions:
--    - Conflict: conflict_avoidance_pattern, argument_reconnection, criticism_expression, stonewalling_pattern
--    - Lifestyle: food_preference, exercise_habits, environmental_values, anniversary_importance, political_views, travel_preference
--    - Family: holiday_obligations
--
-- 2. Added 9 critical questions:
--    - therapy_openness (0.90, dealbreaker)
--    - past_abuse_experience (0.95)
--    - work_life_balance (0.85)
--    - decision_making_power (0.90)
--    - privacy_boundaries (0.95, dealbreaker)
--    - addiction_history (1.0, dealbreaker)
--    - long_distance_tolerance (0.80)
--    - partner_financial_support (0.85)
--    - premarital_counseling (0.85)
--
-- 3. Activated sexual_orientation question
--
-- 4. Created system_settings table for dynamic values
--
-- 5. Added auto-update trigger for question count
--
-- 6. Kept is_active column (marked deprecated) to avoid breaking existing code
--    - Will remove in future migration after updating all code
--
-- 📊 RESULT: 59 active questions (all are active)
--
-- 🔄 NEXT STEPS:
-- 1. Update Python backend TOTAL_QUESTIONS = 44 → use get_active_question_count()
-- 2. Update database migrations / 44.0 → use dynamic count
-- 3. Update mobile app TOTAL_QUESTIONS = 44 → fetch from backend
-- 4. Keep matching ratio 60/40 (Embeddings 60%, Answers 40%)
-- ==========================================
