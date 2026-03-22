-- ==========================================
-- FLIO Questions and Answers System
-- ==========================================
-- Description: Complete questions and answers system with 60 research-based questions
-- Migration: 002_questions_and_answers.sql
-- Created: 2026-02-05 | Expanded: 2026-03-22
--
-- Includes:
-- - 4 dealbreaker questions (hard filter — exact match required)
-- - 4 marriage planning questions (weighted scoring)
-- - 9 Gottman Four Horsemen questions (conflict resolution — 94% predictive accuracy)
-- - 8 attachment & emotional support questions
-- - 8 Korean family culture questions
-- - 9 lifestyle & values questions
-- - 6 financial compatibility questions
-- - 2 emotional intelligence questions
-- - 10 open-ended text questions (semantic AI matching via embedding + cosine)
--
-- Matching architecture:
--   Dealbreakers (can_be_dealbreaker=true): hard filter, eliminates incompatible pairs
--   Choice questions: base_weight × learned_weight × option-distance similarity
--   Text questions: Azure OpenAI embedding → cosine similarity (40% of total score)
--
-- Tables: questions, user_answers, user_feedback, system_settings
-- ==========================================

-- ==========================================
-- DROP EXISTING TABLES
-- ==========================================

DROP TABLE IF EXISTS question_performance CASCADE;
DROP TABLE IF EXISTS user_answers CASCADE;
DROP TABLE IF EXISTS user_feedback CASCADE;
DROP TABLE IF EXISTS questions CASCADE;
DROP TABLE IF EXISTS system_settings CASCADE;

-- ==========================================
-- TABLE: questions
-- ==========================================
-- Research-based questions for compatibility matching
-- 35 choice questions + 5 text questions = 40 total

CREATE TABLE questions (
    id VARCHAR(100) PRIMARY KEY,
    category VARCHAR(50) NOT NULL CHECK (category IN (
        '기본정보', '가치관', '결혼계획', '갈등해결', '애착',
        '감정지원', '가족', '소통', '애정표현', '재정',
        '커리어', '가사', '종교', '라이프스타일', '주거',
        '음주', '흡연', '연애관', '성장'
    )),
    text_ko TEXT NOT NULL,
    text_en TEXT NOT NULL,
    answer_type VARCHAR(50) NOT NULL CHECK (answer_type IN ('choice', 'text')),
    options JSONB NOT NULL,
    base_weight FLOAT DEFAULT 0.5 CHECK (base_weight >= 0 AND base_weight <= 1),
    effectiveness_score FLOAT DEFAULT 5.0,
    can_be_dealbreaker BOOLEAN DEFAULT false,
    tags TEXT[],
    placeholder TEXT,
    max_length INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE questions IS '60 research-based questions (50 choice + 10 text) for matching compatibility';
COMMENT ON COLUMN questions.id IS 'Unique question identifier (snake_case)';
COMMENT ON COLUMN questions.category IS 'Question category in Korean';
COMMENT ON COLUMN questions.text_ko IS 'Question text in Korean';
COMMENT ON COLUMN questions.text_en IS 'Question text in English';
COMMENT ON COLUMN questions.answer_type IS 'Type of answer: choice or text';
COMMENT ON COLUMN questions.options IS 'JSON array of answer options for choice questions — order defines similarity distance';
COMMENT ON COLUMN questions.base_weight IS 'Research-based importance weight (0-1). Multiplied by learned_weight for final score';
COMMENT ON COLUMN questions.effectiveness_score IS 'Research-based effectiveness score (1-10)';
COMMENT ON COLUMN questions.can_be_dealbreaker IS 'True = hard filter (exact match required). False = weighted similarity scoring';
COMMENT ON COLUMN questions.tags IS 'Optional tags for categorization';
COMMENT ON COLUMN questions.placeholder IS 'Placeholder text for text input questions';
COMMENT ON COLUMN questions.max_length IS 'Maximum character length for text questions';

-- ==========================================
-- TABLE: user_answers
-- ==========================================
-- User responses to questions with importance ratings

CREATE TABLE user_answers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    question_id VARCHAR(100) NOT NULL REFERENCES questions(id) ON DELETE CASCADE,

    -- Answer data
    answer_value VARCHAR(100),
    answer_text TEXT,
    importance INTEGER DEFAULT 3 CHECK (importance >= 1 AND importance <= 5),
    is_dealbreaker BOOLEAN DEFAULT false,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    UNIQUE(user_id, question_id),
    CHECK (
        (answer_value IS NOT NULL AND answer_text IS NULL) OR
        (answer_value IS NULL AND answer_text IS NOT NULL)
    )
);

COMMENT ON TABLE user_answers IS 'User responses to questions with importance ratings';
COMMENT ON COLUMN user_answers.answer_value IS 'Selected option value for choice questions';
COMMENT ON COLUMN user_answers.answer_text IS 'Free text answer for text questions';
COMMENT ON COLUMN user_answers.importance IS 'User-defined importance (1-5) for weighted matching';
COMMENT ON COLUMN user_answers.is_dealbreaker IS 'User override: mark this question as dealbreaker for matching';

-- ==========================================
-- TABLE: user_feedback
-- ==========================================
-- General app feedback from users

CREATE TABLE user_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    feedback_type VARCHAR(50) NOT NULL CHECK (feedback_type IN (
        'bug_report', 'feature_request', 'question_quality',
        'match_quality', 'general', 'complaint'
    )),
    content TEXT NOT NULL,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE user_feedback IS 'General app feedback from users';
COMMENT ON COLUMN user_feedback.feedback_type IS 'Type of feedback: bug_report, feature_request, etc.';
COMMENT ON COLUMN user_feedback.content IS 'Feedback content';
COMMENT ON COLUMN user_feedback.rating IS 'Optional rating (1-5)';

-- ==========================================
-- TABLE: system_settings
-- ==========================================
-- System-wide settings stored as key-value pairs

CREATE TABLE system_settings (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE system_settings IS 'System-wide settings stored as key-value pairs';
COMMENT ON COLUMN system_settings.key IS 'Setting key identifier';
COMMENT ON COLUMN system_settings.value IS 'Setting value as JSONB';

-- ==========================================
-- INDEXES
-- ==========================================

-- Questions table indexes
CREATE INDEX idx_questions_category ON questions(category);
CREATE INDEX idx_questions_weight ON questions(base_weight DESC);
CREATE INDEX idx_questions_answer_type ON questions(answer_type);

-- User answers table indexes
CREATE INDEX idx_user_answers_user_id ON user_answers(user_id);
CREATE INDEX idx_user_answers_question_id ON user_answers(question_id);
CREATE INDEX idx_user_answers_dealbreaker ON user_answers(is_dealbreaker) WHERE is_dealbreaker = true;

-- User feedback table indexes
CREATE INDEX idx_user_feedback_user_id ON user_feedback(user_id);
CREATE INDEX idx_user_feedback_type ON user_feedback(feedback_type);

-- ==========================================
-- QUESTIONS DATA (40 total)
-- ==========================================

INSERT INTO questions (id, category, text_ko, text_en, answer_type, options, base_weight, can_be_dealbreaker) VALUES

-- ==========================================
-- DEALBREAKERS (4 questions - Weight 1.0)
-- Exact match filtering - hard requirements
-- ==========================================

('gender_preference', '기본정보', '어떤 성별의 분을 만나고 싶으세요?', 'What gender are you looking to match with?', 'choice',
'[{"value":"male","label_ko":"남성","label_en":"Male"},{"value":"female","label_ko":"여성","label_en":"Female"},{"value":"any","label_ko":"상관없어요","label_en":"Any"}]'::jsonb,
1.0, true),

('age_range_preference', '기본정보', '선호하는 상대방의 나이 범위는?', 'What is your preferred age range?', 'choice',
'[{"value":"same_age","label_ko":"동갑 ±2세","label_en":"Same age ±2 years"},{"value":"younger_5","label_ko":"나보다 최대 5세 어려도 괜찮아요","label_en":"Up to 5 years younger"},{"value":"older_5","label_ko":"나보다 최대 5세 많아도 괜찮아요","label_en":"Up to 5 years older"},{"value":"age_gap_ok","label_ko":"나이 차이는 상관없어요","label_en":"Age gap doesn''t matter"}]'::jsonb,
1.0, true),

('disability_acceptance', '가치관', '신체적 차이가 있는 분과의 연애에 대해 어떻게 생각하시나요?', 'How do you feel about dating someone with physical differences?', 'choice',
'[{"value":"fully_open","label_ko":"전혀 문제없어요","label_en":"Completely open"},{"value":"depends","label_ko":"상황에 따라 달라요","label_en":"Depends on situation"},{"value":"prefer_not","label_ko":"조금 어려울 것 같아요","label_en":"Prefer not"}]'::jsonb,
1.0, true),

('divorce_status', '기본정보', '이혼 경험이 있는 분에 대해 어떻게 생각하세요?', 'How do you feel about a partner who has been divorced?', 'choice',
'[{"value":"no_problem","label_ko":"전혀 문제없어요","label_en":"No problem at all"},{"value":"depends","label_ko":"상황에 따라 달라요","label_en":"Depends on situation"},{"value":"prefer_not","label_ko":"선호하지 않아요","label_en":"Prefer not"}]'::jsonb,
1.0, true),

-- ==========================================
-- MARRIAGE PLANNING (2 questions - Weight 0.95)
-- Important but use weighted scoring, not exact match
-- ==========================================

('marriage_timeline', '결혼계획', '결혼은 언제쯤 생각하고 계세요?', 'When are you thinking about marriage?', 'choice',
'[{"value":"within_1_year","label_ko":"1년 이내","label_en":"Within 1 year"},{"value":"1_2_years","label_ko":"1-2년 내","label_en":"1-2 years"},{"value":"3_5_years","label_ko":"3-5년 후","label_en":"3-5 years"},{"value":"not_decided","label_ko":"아직 생각 중","label_en":"Still thinking"},{"value":"not_priority","label_ko":"결혼보다 연애가 우선","label_en":"Dating is priority"}]'::jsonb,
0.95, false),

('children_plan', '결혼계획', '결혼 후 자녀 계획은?', 'What are your thoughts on having children?', 'choice',
'[{"value":"want_2_3","label_ko":"2-3명 갖고 싶어요","label_en":"Want 2-3"},{"value":"want_1","label_ko":"1명 갖고 싶어요","label_en":"Want 1"},{"value":"undecided","label_ko":"아직 생각 중","label_en":"Still thinking"},{"value":"no_children","label_ko":"자녀 없이 살고 싶어요","label_en":"Prefer no children"}]'::jsonb,
0.95, false),

-- ==========================================
-- GOTTMAN FOUR HORSEMEN (6 questions - Weight 0.90-0.95)
-- Most predictive of relationship success (94% accuracy)
-- ==========================================

('conflict_resolution', '갈등해결', '연인과 심하게 다투었을 때 어떻게 해결하시나요?', 'How do you resolve serious disagreements?', 'choice',
'[{"value":"calm_then_talk","label_ko":"진정한 후 대화해요","label_en":"Calm down first, then talk"},{"value":"immediate_talk","label_ko":"바로 대화로 풀어요","label_en":"Talk it out immediately"},{"value":"need_time","label_ko":"혼자 생각할 시간이 필요해요","label_en":"Need time to think alone"},{"value":"avoid","label_ko":"갈등 상황을 피하는 편이에요","label_en":"Tend to avoid conflict"}]'::jsonb,
0.95, false),

('contempt_prevention', '갈등해결', '화가 날 때도 상대를 존중하며 말할 수 있나요?', 'Can you speak respectfully even when angry?', 'choice',
'[{"value":"always_respectful","label_ko":"항상 존중하며 말해요","label_en":"Always speak respectfully"},{"value":"usually_yes","label_ko":"대부분 그래요","label_en":"Usually yes"},{"value":"sometimes_difficult","label_ko":"때때로 어려워요","label_en":"Sometimes difficult"},{"value":"struggle","label_ko":"화나면 힘들어요","label_en":"Struggle when angry"}]'::jsonb,
0.95, false),

('defensive_communication', '갈등해결', '파트너가 불만을 이야기할 때 첫 반응은?', 'What is your first reaction when your partner expresses dissatisfaction?', 'choice',
'[{"value":"listen_understand","label_ko":"경청하고 이해하려 해요","label_en":"Listen and try to understand"},{"value":"explain_perspective","label_ko":"제 입장을 설명해요","label_en":"Explain my perspective"},{"value":"feel_defensive","label_ko":"방어적으로 느껴져요","label_en":"Feel defensive"},{"value":"counter_criticize","label_ko":"상대의 잘못도 지적해요","label_en":"Point out their faults too"}]'::jsonb,
0.95, false),

('repair_attempts', '갈등해결', '다툰 후 관계 회복을 위해 어떻게 하시나요?', 'How do you repair the relationship after a fight?', 'choice',
'[{"value":"apologize_first","label_ko":"먼저 사과하고 대화해요","label_en":"Apologize first and talk"},{"value":"show_affection","label_ko":"애정 표현으로 풀어요","label_en":"Show affection"},{"value":"give_time","label_ko":"시간을 주고 자연스럽게","label_en":"Give time, resolve naturally"},{"value":"discuss_solution","label_ko":"해결책을 함께 찾아요","label_en":"Find solutions together"}]'::jsonb,
0.90, false),

('disagreement_comfort', '갈등해결', '연인과 의견이 다를 때 얼마나 편안하세요?', 'How comfortable are you with disagreements?', 'choice',
'[{"value":"very_comfortable","label_ko":"편안해요, 건강한 대화라고 생각해요","label_en":"Very comfortable, see it as healthy"},{"value":"okay_minor","label_ko":"작은 의견 차이는 괜찮아요","label_en":"Okay with minor differences"},{"value":"somewhat_anxious","label_ko":"조금 불안하지만 해결하려 노력해요","label_en":"Somewhat anxious but try to resolve"},{"value":"very_uncomfortable","label_ko":"매우 불편하고 피하고 싶어요","label_en":"Very uncomfortable, want to avoid"}]'::jsonb,
0.90, false),

('partner_mistake_reaction', '갈등해결', '연인이 실수했을 때 첫 반응은?', 'What is your first reaction when your partner makes a mistake?', 'choice',
'[{"value":"understanding","label_ko":"이해하고 격려해요","label_en":"Show understanding and encouragement"},{"value":"discuss_calmly","label_ko":"차분하게 이야기해요","label_en":"Discuss it calmly"},{"value":"disappointed","label_ko":"실망감을 느껴요","label_en":"Feel disappointed"},{"value":"criticize","label_ko":"비판하는 편이에요","label_en":"Tend to criticize"}]'::jsonb,
0.95, false),

-- ==========================================
-- ATTACHMENT & EMOTIONAL SUPPORT (5 questions - Weight 0.85-0.90)
-- ==========================================

('relationship_security', '애착', '연애 관계에서 안정감을 느끼기 위해 무엇이 필요하세요?', 'What do you need to feel secure in a relationship?', 'choice',
'[{"value":"consistent_communication","label_ko":"꾸준한 소통과 확인","label_en":"Consistent communication and reassurance"},{"value":"quality_time","label_ko":"함께하는 시간","label_en":"Quality time together"},{"value":"trust_freedom","label_ko":"신뢰와 자유","label_en":"Trust and freedom"},{"value":"physical_affection","label_ko":"스킨십과 애정 표현","label_en":"Physical affection and love expressions"}]'::jsonb,
0.90, false),

('trust_jealousy', '애착', '연인이 이성 친구와 단둘이 만난다면?', 'How would you feel if your partner met a friend of the opposite gender alone?', 'choice',
'[{"value":"trust_fully","label_ko":"전적으로 믿어요","label_en":"Completely trust them"},{"value":"express_feeling","label_ko":"솔직하게 제 마음을 표현해요","label_en":"Express my feelings honestly"},{"value":"feel_anxious","label_ko":"불안하지만 참아요","label_en":"Feel anxious but endure"},{"value":"cannot_accept","label_ko":"받아들이기 어려워요","label_en":"Difficult to accept"}]'::jsonb,
0.90, false),

('emotional_support', '감정지원', '연인이 힘들어할 때 어떻게 해주시나요?', 'How do you support your partner when they are struggling?', 'choice',
'[{"value":"listen_empathize","label_ko":"공감하며 이야기를 들어줘요","label_en":"Listen with empathy"},{"value":"give_solution","label_ko":"해결책을 함께 찾아봐요","label_en":"Help find solutions"},{"value":"cheer_up","label_ko":"기분 전환을 도와줘요","label_en":"Help cheer them up"},{"value":"give_space","label_ko":"혼자 생각할 시간을 줘요","label_en":"Give them space"}]'::jsonb,
0.85, false),

('good_news_response', '감정지원', '좋은 소식을 나눴을 때 어떤 반응을 받으면 가장 행복하세요?', 'When sharing good news, what response makes you feel closest?', 'choice',
'[{"value":"enthusiastic","label_ko":"진심으로 기뻐하며 함께 축하해줘요","label_en":"Enthusiastically celebrate together"},{"value":"ask_details","label_ko":"자세히 물어보며 관심을 보여요","label_en":"Ask for details and show interest"},{"value":"quiet_support","label_ko":"조용히 지지해줘요","label_en":"Quietly supportive"},{"value":"brief_congrats","label_ko":"간단히 축하해줘요","label_en":"Brief congratulations"}]'::jsonb,
0.90, false),

('emotional_regulation', '감정지원', '스트레스나 힘든 감정이 들 때 어떻게 대처하시나요?', 'How do you cope with stress or difficult emotions?', 'choice',
'[{"value":"talk_to_partner","label_ko":"연인과 이야기해요","label_en":"Talk to my partner"},{"value":"alone_time","label_ko":"혼자 시간을 보내요","label_en":"Spend time alone"},{"value":"physical_activity","label_ko":"운동이나 활동으로 풀어요","label_en":"Through physical activity"},{"value":"distraction","label_ko":"다른 일로 기분 전환해요","label_en":"Distract myself with other things"}]'::jsonb,
0.90, false),

-- ==========================================
-- KOREAN FAMILY CULTURE (5 questions - Weight 0.85-0.90)
-- ==========================================

('family_approval_importance', '가족', '연애에서 가족의 동의가 얼마나 중요하세요?', 'How important is family approval for your relationship?', 'choice',
'[{"value":"very_important","label_ko":"매우 중요해요, 꼭 받고 싶어요","label_en":"Very important, must have it"},{"value":"important","label_ko":"중요하지만 최종 결정은 제가 해요","label_en":"Important but I make final decision"},{"value":"prefer","label_ko":"있으면 좋지만 필수는 아니에요","label_en":"Nice to have but not required"},{"value":"not_important","label_ko":"크게 중요하지 않아요","label_en":"Not very important"}]'::jsonb,
0.90, false),

('filial_piety', '가족', '부모님 모시는 것에 대해 어떻게 생각하세요?', 'How do you feel about taking care of aging parents?', 'choice',
'[{"value":"live_together","label_ko":"함께 모시고 살고 싶어요","label_en":"Want to live together"},{"value":"nearby","label_ko":"가까이 살며 자주 뵙고 싶어요","label_en":"Live nearby and visit often"},{"value":"regular_visits","label_ko":"정기적으로 방문하고 싶어요","label_en":"Regular visits"},{"value":"as_needed","label_ko":"필요할 때 도와드리고 싶어요","label_en":"Help when needed"}]'::jsonb,
0.90, false),

('ancestral_rites', '가족', '명절이나 제사 등 가족 행사 참여에 대해 어떻게 생각하세요?', 'How do you feel about participating in ancestral rites and family ceremonies?', 'choice',
'[{"value":"very_important","label_ko":"매우 중요해요, 꼭 지켜요","label_en":"Very important, always participate"},{"value":"important","label_ko":"중요하게 생각해요","label_en":"Consider it important"},{"value":"flexible","label_ko":"상황에 따라 유연하게","label_en":"Flexible based on situation"},{"value":"not_priority","label_ko":"크게 중요하지 않아요","label_en":"Not a priority"}]'::jsonb,
0.85, false),

('education_priority', '가족', '자녀 교육에서 가장 중요하게 생각하는 것은?', 'What is most important in children''s education?', 'choice',
'[{"value":"happiness","label_ko":"아이의 행복과 관심사","label_en":"Child''s happiness and interests"},{"value":"balanced","label_ko":"학업과 인성의 균형","label_en":"Balance academics and character"},{"value":"academic","label_ko":"학업 성취와 명문대","label_en":"Academic achievement and top universities"},{"value":"independence","label_ko":"독립성과 자율성","label_en":"Independence and autonomy"}]'::jsonb,
0.85, false),

('parents_relationship', '가족', '부모님과의 관계는 어떠세요?', 'How is your relationship with your parents?', 'choice',
'[{"value":"very_close","label_ko":"매우 친밀해요","label_en":"Very close"},{"value":"close","label_ko":"친밀한 편이에요","label_en":"Quite close"},{"value":"moderate","label_ko":"보통이에요","label_en":"Average"},{"value":"distant","label_ko":"약간 거리감이 있어요","label_en":"Somewhat distant"}]'::jsonb,
0.80, false),

-- ==========================================
-- LIFESTYLE & VALUES (7 questions - Weight 0.75-0.85)
-- ==========================================

('communication_frequency', '소통', '연인과 얼마나 자주 연락하고 만나고 싶으세요?', 'How often would you like to communicate and meet your partner?', 'choice',
'[{"value":"daily","label_ko":"매일 연락하고 자주 만나요","label_en":"Daily contact and frequent meetings"},{"value":"frequent","label_ko":"자주 연락하고 주 2-3회 만나요","label_en":"Frequent contact and meet 2-3 times/week"},{"value":"moderate","label_ko":"적당히 연락하고 주 1회 만나요","label_en":"Moderate contact and meet once weekly"},{"value":"independent","label_ko":"각자 시간을 존중하며 편하게","label_en":"Respect each other''s time, relaxed"}]'::jsonb,
0.80, false),

('love_language', '애정표현', '언제 가장 사랑받는다고 느끼세요?', 'When do you feel most loved?', 'choice',
'[{"value":"words","label_ko":"사랑한다는 말을 들을 때","label_en":"When hearing words of affirmation"},{"value":"quality_time","label_ko":"함께 시간을 보낼 때","label_en":"When spending quality time together"},{"value":"physical_touch","label_ko":"스킨십을 할 때","label_en":"Through physical affection"},{"value":"acts_service","label_ko":"배려하는 행동을 받을 때","label_en":"When they do thoughtful things"},{"value":"gifts","label_ko":"선물을 받을 때","label_en":"When receiving gifts"}]'::jsonb,
0.80, false),

('financial_transparency', '재정', '결혼 후 재정 관리는 어떻게 하고 싶으세요?', 'What is your approach to finances in marriage?', 'choice',
'[{"value":"fully_shared","label_ko":"완전 공동관리","label_en":"Fully shared management"},{"value":"mostly_shared","label_ko":"대부분 공동, 일부 개인","label_en":"Mostly shared, some personal"},{"value":"proportional","label_ko":"수입 비율로 분담","label_en":"Split by income proportion"},{"value":"separate","label_ko":"각자 관리","label_en":"Separate management"}]'::jsonb,
0.85, false),

('major_purchase_decision', '재정', '큰 지출 결정은 어떻게 하고 싶으세요?', 'How would you make major purchase decisions?', 'choice',
'[{"value":"together","label_ko":"항상 함께 결정해요","label_en":"Always decide together"},{"value":"discuss_first","label_ko":"먼저 상의하고 결정해요","label_en":"Discuss first then decide"},{"value":"inform","label_ko":"결정 후 알려요","label_en":"Decide then inform"},{"value":"independent","label_ko":"각자 자유롭게","label_en":"Each decides independently"}]'::jsonb,
0.90, false),

('career_priority', '커리어', '일과 가정의 우선순위는?', 'How do you prioritize work and family?', 'choice',
'[{"value":"family_first","label_ko":"가정이 최우선","label_en":"Family comes first"},{"value":"balanced","label_ko":"일과 가정의 균형","label_en":"Balance work and family"},{"value":"career_important","label_ko":"커리어도 중요해요","label_en":"Career is also important"},{"value":"career_first","label_ko":"커리어를 우선시","label_en":"Career comes first"}]'::jsonb,
0.85, false),

('household_division', '가사', '가사 분담은 어떻게 하고 싶으세요?', 'How would you like to divide household chores?', 'choice',
'[{"value":"equal","label_ko":"동등하게 나눠요","label_en":"Split equally"},{"value":"flexible","label_ko":"상황에 따라 유연하게","label_en":"Flexible based on situation"},{"value":"by_strength","label_ko":"각자 잘하는 것을","label_en":"Based on each person''s strengths"},{"value":"hire_help","label_ko":"도움을 고용하고 싶어요","label_en":"Prefer to hire help"}]'::jsonb,
0.80, false),

('religion_spirituality', '종교', '종교는 얼마나 중요하세요?', 'How important is religion to you?', 'choice',
'[{"value":"very_important","label_ko":"매우 중요해요","label_en":"Very important"},{"value":"somewhat","label_ko":"어느 정도 중요해요","label_en":"Somewhat important"},{"value":"not_important","label_ko":"크게 중요하지 않아요","label_en":"Not very important"},{"value":"respect_all","label_ko":"모든 종교를 존중해요","label_en":"Respect all religions"}]'::jsonb,
0.75, false),

-- ==========================================
-- ADDITIONAL IMPORTANT QUESTIONS (3 questions - Weight 0.75-0.80)
-- ==========================================

('pet_preference', '라이프스타일', '반려동물에 대해 어떻게 생각하세요?', 'How do you feel about having pets?', 'choice',
'[{"value":"love_pets","label_ko":"반려동물을 키우고 싶어요","label_en":"Want to have pets"},{"value":"okay","label_ko":"괜찮아요","label_en":"Okay with it"},{"value":"prefer_not","label_ko":"별로 선호하지 않아요","label_en":"Prefer not"},{"value":"allergic","label_ko":"알레르기나 두려움이 있어요","label_en":"Have allergies or concerns"}]'::jsonb,
0.75, false),

('social_life_balance', '라이프스타일', '친구들과 보내는 시간과 연인과의 시간, 어떻게 균형을 맞추시나요?', 'How do you balance time with friends and time with your partner?', 'choice',
'[{"value":"partner_priority","label_ko":"연인과의 시간을 우선시해요","label_en":"Prioritize time with partner"},{"value":"balanced","label_ko":"둘 다 중요하게 생각해요","label_en":"Balance both equally"},{"value":"social_important","label_ko":"친구들과의 시간도 중요해요","label_en":"Social life is also important"},{"value":"independent","label_ko":"각자 자유롭게","label_en":"Each has independence"}]'::jsonb,
0.80, false),

('physical_affection', '애정표현', '스킨십에 대해 어떻게 생각하세요?', 'How do you feel about physical affection?', 'choice',
'[{"value":"very_important","label_ko":"매우 중요해요","label_en":"Very important"},{"value":"important","label_ko":"중요한 편이에요","label_en":"Quite important"},{"value":"moderate","label_ko":"적당히 필요해요","label_en":"Moderately important"},{"value":"not_priority","label_ko":"크게 중요하지 않아요","label_en":"Not a priority"}]'::jsonb,
0.80, false),

-- ==========================================
-- LIFESTYLE BASICS (3 questions - Weight 0.75-0.85)
-- ==========================================

('living_location', '주거', '어디에서 살고 싶으세요?', 'Where would you like to live?', 'choice',
'[{"value":"city","label_ko":"도심이 좋아요","label_en":"Prefer city center"},{"value":"suburbs","label_ko":"교외가 좋아요","label_en":"Prefer suburbs"},{"value":"countryside","label_ko":"시골이 좋아요","label_en":"Prefer countryside"},{"value":"flexible","label_ko":"어디든 괜찮아요","label_en":"Anywhere is fine"}]'::jsonb,
0.75, false),

('drinking_habits', '음주', '술은 얼마나 자주 드세요?', 'How often do you drink alcohol?', 'choice',
'[{"value":"never","label_ko":"마시지 않아요","label_en":"Don''t drink"},{"value":"social","label_ko":"사교적으로만","label_en":"Only socially"},{"value":"weekly","label_ko":"주 1-2회","label_en":"1-2 times a week"},{"value":"frequent","label_ko":"자주 마시는 편","label_en":"Drink frequently"}]'::jsonb,
0.80, false),

('smoking_status', '흡연', '흡연은 하세요?', 'Do you smoke?', 'choice',
'[{"value":"never","label_ko":"안 피워요","label_en":"Don''t smoke"},{"value":"quit","label_ko":"금연했어요","label_en":"Quit smoking"},{"value":"occasional","label_ko":"가끔 피워요","label_en":"Occasionally"},{"value":"regular","label_ko":"피우는 편이에요","label_en":"Smoke regularly"}]'::jsonb,
0.85, false),

-- ==========================================
-- TEXT QUESTIONS (5 open-ended - Weight 0.90-0.95)
-- Used for semantic AI matching via embeddings
-- ==========================================

('personal_values_lifestyle', '가치관', '당신의 삶에서 가장 중요한 가치는 무엇이며, 어떤 순간에 행복을 느끼시나요?',
'What values are most important in your life, and when do you feel happiest?', 'text', '[]'::jsonb, 0.95, false),

('ideal_relationship_dynamic', '연애관', '이상적인 연애 관계는 어떤 모습이며, 5-10년 후 파트너와 어떤 삶을 살고 싶으세요?',
'What is your ideal relationship, and what life do you envision with your partner in 5-10 years?', 'text', '[]'::jsonb, 0.95, false),

('relationship_deal_makers', '연애관', '과거 연애에서 "이 사람과 함께하고 싶다"고 느꼈던 순간이나 특성은 무엇이었나요? 반대로 "이건 안 되겠다"고 느낀 순간은?',
'What moments or qualities made you feel "I want to be with this person" in past relationships? Conversely, what made you feel "this won''t work"?', 'text', '[]'::jsonb, 0.95, false),

('conflict_growth_philosophy', '성장', '관계에서 어려움이나 갈등이 생겼을 때, 어떻게 극복하고 성장해왔나요?',
'How have you overcome difficulties in relationships and grown from them?', 'text', '[]'::jsonb, 0.90, false),

('life_challenges_response', '성장', '인생에서 가장 어려웠던 순간은 언제였고, 어떻게 극복하셨나요? 그 경험이 현재의 당신에게 어떤 영향을 주었나요?',
'What was the most challenging moment in your life, how did you overcome it, and how did it shape who you are today?', 'text', '[]'::jsonb, 0.95, false);

-- ==========================================
-- QUESTIONS DATA EXPANSION (+20 → 60 total)
-- ==========================================
-- 15 new choice questions + 5 new text questions

INSERT INTO questions (id, category, text_ko, text_en, answer_type, options, base_weight, can_be_dealbreaker) VALUES

-- Gottman expansion (+3 choice, weight 0.90-0.95)
('stonewalling_pattern', '갈등해결', '갈등 상황에서 대화를 멈추고 침묵하거나 회피한 적이 있나요?',
'Have you ever stopped talking and withdrawn during conflict?', 'choice',
'[{"value":"rarely","label_ko":"거의 없어요, 끝까지 대화하려 해요","label_en":"Rarely, I try to talk through it"},{"value":"when_overwhelmed","label_ko":"압도되면 잠시 쉬었다가 돌아와요","label_en":"When overwhelmed, I take breaks then return"},{"value":"sometimes","label_ko":"가끔 대화를 멈추고 싶어요","label_en":"Sometimes I want to stop talking"},{"value":"often","label_ko":"자주 침묵하거나 물러나요","label_en":"Often withdraw or go silent"}]'::jsonb,
0.95, false),

('criticism_style', '갈등해결', '파트너의 행동이 불만스러울 때, 어떻게 표현하시나요?',
'When dissatisfied with partner''s behavior, how do you express it?', 'choice',
'[{"value":"specific_behavior","label_ko":"구체적 행동을 말해요 (''설거지를 안 했네'')","label_en":"Talk about specific behavior"},{"value":"feeling_focus","label_ko":"제 감정을 전달해요 (''걱정됐어'')","label_en":"Express my feelings"},{"value":"character_attack","label_ko":"성격 문제로 말하게 돼요 (''넌 항상 게을러'')","label_en":"Attribute to character"},{"value":"generalize","label_ko":"''항상'', ''절대'' 같은 말을 써요","label_en":"Use ''always'', ''never'' language"}]'::jsonb,
0.95, false),

('repair_acceptance', '갈등해결', '다툼 중에 상대방이 농담이나 애정 표현으로 분위기를 풀려 할 때, 어떻게 반응하세요?',
'When partner tries to lighten mood during conflict, how do you respond?', 'choice',
'[{"value":"accept","label_ko":"감사하게 받아들이고 분위기가 풀려요","label_en":"Appreciate it and mood lightens"},{"value":"pause_accept","label_ko":"잠시 후 받아들여요","label_en":"Accept after a pause"},{"value":"reject_gentle","label_ko":"지금은 안 되고 나중에 해결하자고 해요","label_en":"Say not now, let''s resolve later"},{"value":"reject_harsh","label_ko":"진지하게 받아들이지 않는다고 느껴요","label_en":"Feel they''re not taking it seriously"}]'::jsonb,
0.90, false),

-- Attachment expansion (+3 choice, weight 0.85-0.90)
('abandonment_response', '애착', '연인이 갑자기 연락이 안 되면 어떤 생각이 드시나요?',
'When partner suddenly doesn''t respond, what goes through your mind?', 'choice',
'[{"value":"trust","label_ko":"바쁘겠다 생각하고 기다려요","label_en":"Trust they''re busy and wait"},{"value":"slight_worry","label_ko":"조금 걱정되지만 괜찮아요","label_en":"Slightly worried but okay"},{"value":"anxious","label_ko":"불안하고 계속 확인하게 돼요","label_en":"Anxious and keep checking"},{"value":"catastrophize","label_ko":"관계에 문제가 생긴 건 아닐까 걱정돼요","label_en":"Worry something''s wrong with relationship"}]'::jsonb,
0.90, false),

('emotional_intimacy_comfort', '애착', '연인과 깊은 감정을 나누는 것에 대해 어떻게 느끼세요?',
'How do you feel about sharing deep emotions with partner?', 'choice',
'[{"value":"comfortable","label_ko":"편안하고 친밀함을 느껴요","label_en":"Comfortable and feel close"},{"value":"takes_time","label_ko":"시간이 걸리지만 결국 나눠요","label_en":"Takes time but eventually share"},{"value":"uncomfortable","label_ko":"약간 불편하고 부담스러워요","label_en":"Somewhat uncomfortable"},{"value":"avoid","label_ko":"깊은 감정 표현을 피하게 돼요","label_en":"Tend to avoid deep emotional expression"}]'::jsonb,
0.90, false),

('dependency_independence', '애착', '연인에게 의지하고 도움을 구하는 것에 대해 어떻게 생각하세요?',
'How do you feel about depending on and asking help from partner?', 'choice',
'[{"value":"natural","label_ko":"자연스럽고 서로 의지하는 게 좋아요","label_en":"Natural and good to depend on each other"},{"value":"selective","label_ko":"중요한 일은 도움을 구해요","label_en":"Ask for help on important things"},{"value":"prefer_independent","label_ko":"스스로 해결하는 걸 선호해요","label_en":"Prefer to solve things myself"},{"value":"uncomfortable","label_ko":"의지하는 게 불편해요","label_en":"Uncomfortable depending on others"}]'::jsonb,
0.85, false),

-- Korean family culture expansion (+3 choice, weight 0.85-0.90)
('inlaw_hierarchy', '가족', '시댁/처가 어른들의 의견이 본인 의견과 다를 때 어떻게 하시겠어요?',
'When in-laws'' opinions differ from yours, what would you do?', 'choice',
'[{"value":"respect_follow","label_ko":"어른을 존중하고 따라요","label_en":"Respect elders and follow"},{"value":"discuss_compromise","label_ko":"대화로 절충점을 찾아요","label_en":"Discuss and find compromise"},{"value":"partner_decide","label_ko":"파트너와 함께 결정해요","label_en":"Decide together with partner"},{"value":"own_decision","label_ko":"우리 결정을 우선시해요","label_en":"Prioritize our own decision"}]'::jsonb,
0.90, false),

('traditional_ceremonies', '가족', '명절에 세배나 차례 등 전통 의식을 어떻게 생각하세요?',
'How do you feel about traditional ceremonies?', 'choice',
'[{"value":"important_tradition","label_ko":"중요한 전통이라 꼭 지켜요","label_en":"Important tradition, must observe"},{"value":"participate","label_ko":"가족이 중요하게 생각하면 참여해요","label_en":"Participate if family values it"},{"value":"simplified","label_ko":"간소화해서 하고 싶어요","label_en":"Prefer simplified versions"},{"value":"optional","label_ko":"선택적으로 하면 돼요","label_en":"Should be optional"}]'::jsonb,
0.85, false),

('parent_financial_support', '가족', '결혼 후 부모님께 경제적 지원을 어떻게 할 계획이세요?',
'How do you plan to provide financial support to parents after marriage?', 'choice',
'[{"value":"regular_significant","label_ko":"정기적으로 넉넉히 드려요","label_en":"Regularly and generously"},{"value":"regular_modest","label_ko":"정기적으로 적당히 드려요","label_en":"Regularly but modestly"},{"value":"as_needed","label_ko":"필요할 때 도와드려요","label_en":"Help when needed"},{"value":"minimal","label_ko":"최소한으로 하고 싶어요","label_en":"Prefer minimal support"}]'::jsonb,
0.90, false),

-- Marriage planning expansion (+2 choice, weight 0.85-0.90)
('marriage_housing', '결혼계획', '결혼 후 주거는 어떻게 하고 싶으세요?',
'What are your housing plans after marriage?', 'choice',
'[{"value":"buy_house","label_ko":"집을 사서 독립하고 싶어요","label_en":"Want to buy and live independently"},{"value":"rent_independent","label_ko":"전세/월세로 독립하고 싶어요","label_en":"Want to rent independently"},{"value":"near_family","label_ko":"가족 근처에 살고 싶어요","label_en":"Want to live near family"},{"value":"with_family","label_ko":"가족과 함께 살 수 있어요","label_en":"Can live with family"}]'::jsonb,
0.90, false),

('gender_roles_marriage', '결혼계획', '결혼 생활에서 성역할에 대해 어떻게 생각하세요?',
'What are your views on gender roles in marriage?', 'choice',
'[{"value":"equal_partnership","label_ko":"완전히 평등한 파트너십","label_en":"Completely equal partnership"},{"value":"flexible","label_ko":"상황에 맞게 유연하게","label_en":"Flexible based on situation"},{"value":"some_traditional","label_ko":"어느 정도 전통적 역할이 있어요","label_en":"Some traditional roles"},{"value":"traditional","label_ko":"전통적 역할이 중요해요","label_en":"Traditional roles are important"}]'::jsonb,
0.85, false),

-- Financial compatibility expansion (+2 choice, weight 0.85-0.90)
('savings_spending_style', '재정', '돈 관리 스타일은 어떤가요?',
'What''s your money management style?', 'choice',
'[{"value":"aggressive_saver","label_ko":"철저히 저축해요 (월급의 40% 이상)","label_en":"Aggressive saver (40%+ of income)"},{"value":"balanced","label_ko":"저축과 지출의 균형 (20-30%)","label_en":"Balanced (20-30% savings)"},{"value":"enjoy_present","label_ko":"현재를 즐기는 편 (10-20%)","label_en":"Enjoy present (10-20% savings)"},{"value":"spend_freely","label_ko":"자유롭게 쓰는 편","label_en":"Spend freely"}]'::jsonb,
0.85, false),

('debt_attitude', '재정', '빚/대출에 대해 어떻게 생각하세요?',
'How do you feel about debt and loans?', 'choice',
'[{"value":"avoid_completely","label_ko":"절대 피하고 싶어요","label_en":"Want to avoid completely"},{"value":"only_necessary","label_ko":"필요한 것만 (집, 차)","label_en":"Only for necessities"},{"value":"strategic","label_ko":"전략적으로 활용해요","label_en":"Use strategically"},{"value":"comfortable","label_ko":"편하게 생각해요","label_en":"Comfortable with it"}]'::jsonb,
0.90, false),

-- Lifestyle expansion (+1 choice, weight 0.80)
('weekend_preference', '라이프스타일', '이상적인 주말은 어떤 모습인가요?',
'What''s your ideal weekend?', 'choice',
'[{"value":"active_outdoor","label_ko":"활발하게 야외활동","label_en":"Active outdoor activities"},{"value":"cultural","label_ko":"문화생활 (영화, 전시, 공연)","label_en":"Cultural activities"},{"value":"social","label_ko":"친구들과 만남","label_en":"Meeting friends"},{"value":"rest_home","label_ko":"집에서 푹 쉬기","label_en":"Rest at home"}]'::jsonb,
0.80, false),

-- Emotional intelligence expansion (+1 choice, weight 0.85)
('emotional_self_awareness', '감정지원', '본인의 감정 상태를 얼마나 잘 인식하시나요?',
'How well do you recognize your emotional state?', 'choice',
'[{"value":"very_aware","label_ko":"항상 잘 인식해요","label_en":"Always very aware"},{"value":"usually","label_ko":"대체로 잘 알아차려요","label_en":"Usually recognize well"},{"value":"sometimes","label_ko":"때때로 놓칠 때가 있어요","label_en":"Sometimes miss it"},{"value":"struggle","label_ko":"감정 인식이 어려워요","label_en":"Struggle with emotional awareness"}]'::jsonb,
0.85, false);

-- Text question expansion (+5 text)
INSERT INTO questions (id, category, text_ko, text_en, answer_type, options, base_weight, can_be_dealbreaker, placeholder, max_length) VALUES

('past_conflict_learning', '성장', '과거 연애에서 가장 힘들었던 갈등은 무엇이었고, 그 경험에서 무엇을 배우셨나요?',
'What was the most difficult conflict in past relationships, and what did you learn?', 'text', '[]'::jsonb, 0.95, false,
'예: ''전 파트너는 대화를 회피했는데, 저는 끝까지 풀고 싶어했어요. 이제는 상대의 대화 스타일을 먼저 이해하려 노력해요.''', 500),

('family_relationship_impact', '가족', '가족과의 관계가 연애/결혼 생활에 어떤 영향을 줄 것 같나요? 파트너에게 바라는 가족관은?',
'How will your family relationships influence your romantic life? What family values do you want in a partner?', 'text', '[]'::jsonb, 0.90, false,
'예: ''명절에는 양가를 공평하게 방문하고 싶어요. 서로 가족을 존중하되 우리 가정을 우선시하는 분이면 좋겠어요.''', 500),

('money_philosophy_goals', '재정', '돈에 대한 본인의 철학과 5-10년 후 재정 목표는 무엇인가요?',
'What''s your financial philosophy and your financial goals in 5-10 years?', 'text', '[]'::jsonb, 0.90, false,
'예: ''저축을 중요하게 생각하지만 경험에도 투자하는 편이에요. 5년 후에는 전세 자금을 마련하고 싶어요.''', 500),

('love_expression_style', '애정표현', '사랑받는다고 느끼는 순간은 언제이며, 연인에게 어떤 방식으로 사랑을 표현하시나요?',
'When do you feel loved, and how do you express love?', 'text', '[]'::jsonb, 0.85, false,
'예: ''작은 것도 기억해줄 때 사랑받는다고 느껴요. 저는 응원의 말과 깜짝 선물로 사랑을 표현해요.''', 500),

('growth_support_philosophy', '성장', '개인적 성장과 꿈을 위해 파트너에게 바라는 지원은 무엇이며, 파트너의 꿈을 어떻게 지원하고 싶으세요?',
'What support do you need from partner for personal growth, and how would you support their dreams?', 'text', '[]'::jsonb, 0.90, false,
'예: ''제 커리어 목표를 존중하고 응원해주는 사람이면 좋겠어요. 저도 파트너의 도전을 적극 응원하고 싶어요.''', 500);

-- ==========================================
-- SYSTEM SETTINGS INITIALIZATION
-- ==========================================

INSERT INTO system_settings (key, value, updated_at)
VALUES ('active_question_count', jsonb_build_object('count', 60), NOW())
ON CONFLICT (key) DO UPDATE SET
    value = EXCLUDED.value,
    updated_at = NOW();

-- ==========================================
-- FUNCTIONS
-- ==========================================

-- Function: Get active question count
CREATE OR REPLACE FUNCTION get_active_question_count()
RETURNS INTEGER
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
AS $$
BEGIN
    RETURN (SELECT COUNT(*) FROM questions);
END;
$$;

COMMENT ON FUNCTION get_active_question_count() IS 'Returns the total number of active questions in the system';

-- Function: Update question count in system settings
CREATE OR REPLACE FUNCTION update_question_count()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    INSERT INTO system_settings (key, value, updated_at)
    VALUES (
        'active_question_count',
        jsonb_build_object('count', (SELECT COUNT(*) FROM questions)),
        NOW()
    )
    ON CONFLICT (key) DO UPDATE SET
        value = EXCLUDED.value,
        updated_at = NOW();
    RETURN NULL;
END;
$$;

COMMENT ON FUNCTION update_question_count() IS 'Trigger function to update question count in system_settings';

-- ==========================================
-- TRIGGERS
-- ==========================================

-- Trigger: Update question count when questions table changes
DROP TRIGGER IF EXISTS trigger_update_question_count ON questions;
CREATE TRIGGER trigger_update_question_count
    AFTER INSERT OR DELETE ON questions
    FOR EACH STATEMENT
    EXECUTE FUNCTION update_question_count();

COMMENT ON TRIGGER trigger_update_question_count ON questions IS 'Updates active_question_count in system_settings when questions are added or removed';

-- Trigger: Update updated_at on user_answers
CREATE TRIGGER user_answers_updated_at
    BEFORE UPDATE ON user_answers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

COMMENT ON TRIGGER user_answers_updated_at ON user_answers IS 'Automatically updates updated_at timestamp when user_answers are modified';

-- Trigger: Update updated_at on questions
CREATE TRIGGER questions_updated_at
    BEFORE UPDATE ON questions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

COMMENT ON TRIGGER questions_updated_at ON questions IS 'Automatically updates updated_at timestamp when questions are modified';

-- ==========================================
-- ROW LEVEL SECURITY (RLS)
-- ==========================================

-- Enable RLS on all tables
ALTER TABLE questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_answers ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_settings ENABLE ROW LEVEL SECURITY;

-- RLS Policies: questions table
DROP POLICY IF EXISTS "Questions are viewable by all" ON questions;
CREATE POLICY "Questions are viewable by all"
    ON questions
    FOR SELECT
    TO authenticated
    USING (true);

COMMENT ON POLICY "Questions are viewable by all" ON questions IS 'All authenticated users can view questions';

-- RLS Policies: user_answers table
DROP POLICY IF EXISTS "Users can view own answers" ON user_answers;
CREATE POLICY "Users can view own answers"
    ON user_answers
    FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own answers" ON user_answers;
CREATE POLICY "Users can insert own answers"
    ON user_answers
    FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own answers" ON user_answers;
CREATE POLICY "Users can update own answers"
    ON user_answers
    FOR UPDATE
    TO authenticated
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete own answers" ON user_answers;
CREATE POLICY "Users can delete own answers"
    ON user_answers
    FOR DELETE
    TO authenticated
    USING (auth.uid() = user_id);

COMMENT ON POLICY "Users can view own answers" ON user_answers IS 'Users can only view their own answers';
COMMENT ON POLICY "Users can insert own answers" ON user_answers IS 'Users can only insert their own answers';
COMMENT ON POLICY "Users can update own answers" ON user_answers IS 'Users can only update their own answers';
COMMENT ON POLICY "Users can delete own answers" ON user_answers IS 'Users can only delete their own answers';

-- RLS Policies: user_feedback table
DROP POLICY IF EXISTS "Users can view own feedback" ON user_feedback;
CREATE POLICY "Users can view own feedback"
    ON user_feedback
    FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own feedback" ON user_feedback;
CREATE POLICY "Users can insert own feedback"
    ON user_feedback
    FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = user_id);

COMMENT ON POLICY "Users can view own feedback" ON user_feedback IS 'Users can only view their own feedback';
COMMENT ON POLICY "Users can insert own feedback" ON user_feedback IS 'Users can only insert their own feedback';

-- RLS Policies: system_settings table
DROP POLICY IF EXISTS "System settings are viewable by all" ON system_settings;
CREATE POLICY "System settings are viewable by all"
    ON system_settings
    FOR SELECT
    TO authenticated
    USING (true);

COMMENT ON POLICY "System settings are viewable by all" ON system_settings IS 'All authenticated users can view system settings';

-- ==========================================
-- GRANT PERMISSIONS
-- ==========================================

GRANT SELECT ON questions TO authenticated;
GRANT SELECT ON system_settings TO authenticated;
GRANT EXECUTE ON FUNCTION get_active_question_count TO authenticated;

-- ==========================================
-- VERIFICATION
-- ==========================================

DO $$
DECLARE
    v_total INTEGER;
    v_choice INTEGER;
    v_text INTEGER;
    v_dealbreakers INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_total FROM questions;
    SELECT COUNT(*) INTO v_choice FROM questions WHERE answer_type = 'choice';
    SELECT COUNT(*) INTO v_text FROM questions WHERE answer_type = 'text';
    SELECT COUNT(*) INTO v_dealbreakers FROM questions WHERE can_be_dealbreaker = true;

    RAISE NOTICE '==========================================';
    RAISE NOTICE 'FLIO 60-Question Database Created';
    RAISE NOTICE '==========================================';
    RAISE NOTICE 'Total questions: % (target: 60)', v_total;
    RAISE NOTICE 'Choice questions: % (target: 50)', v_choice;
    RAISE NOTICE 'Text questions: % (target: 10)', v_text;
    RAISE NOTICE '';
    RAISE NOTICE 'Dealbreakers: % (gender, age, disability, divorce — hard filter)', v_dealbreakers;
    RAISE NOTICE 'Choice questions: weighted by base_weight × option-distance similarity';
    RAISE NOTICE 'Text questions: Azure embedding → cosine similarity (40%% of total score)';
    RAISE NOTICE '==========================================';

    IF v_total != 60 THEN
        RAISE EXCEPTION 'Question count mismatch: expected 60, got %', v_total;
    END IF;

    IF v_choice != 50 THEN
        RAISE EXCEPTION 'Choice question count mismatch: expected 50, got %', v_choice;
    END IF;

    IF v_text != 10 THEN
        RAISE EXCEPTION 'Text question count mismatch: expected 10, got %', v_text;
    END IF;

    IF v_dealbreakers != 4 THEN
        RAISE EXCEPTION 'Dealbreaker count mismatch: expected 4, got %', v_dealbreakers;
    END IF;
END $$;
