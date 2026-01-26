-- ==========================================
-- FLIO Questions & User Answers
-- ==========================================
-- Consolidates: 003_questions_database + 005_user_answers_table
-- 40 research-based questions + user answers storage
-- ==========================================

-- Drop old tables
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
CREATE OR REPLACE FUNCTION update_updated_at_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER user_answers_updated_at
    BEFORE UPDATE ON user_answers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_timestamp();

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
-- 40 QUESTIONS DATA
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
-- INITIALIZE SYSTEM SETTINGS
-- ==========================================

INSERT INTO system_settings (key, value)
VALUES ('active_question_count', jsonb_build_object('count', 40))
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;

-- ==========================================
-- GRANT PERMISSIONS
-- ==========================================

GRANT SELECT ON questions TO authenticated;
GRANT SELECT ON system_settings TO authenticated;
GRANT EXECUTE ON FUNCTION get_active_question_count TO authenticated;

-- ==========================================
-- COMMENTS
-- ==========================================

COMMENT ON TABLE questions IS '40 research-based questions (35 choice + 5 text) for matching compatibility';
COMMENT ON TABLE user_answers IS 'User responses to questions with importance ratings';
COMMENT ON TABLE user_feedback IS 'General app feedback from users';
COMMENT ON COLUMN questions.can_be_dealbreaker IS 'True = exact match filtering, False = weighted scoring';

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
    RAISE NOTICE 'FLIO 40-Question Database Created';
    RAISE NOTICE '==========================================';
    RAISE NOTICE 'Total questions: % (target: 40)', v_total;
    RAISE NOTICE 'Choice questions: % (target: 35)', v_choice;
    RAISE NOTICE 'Text questions: % (target: 5)', v_text;
    RAISE NOTICE '';
    RAISE NOTICE 'Dealbreakers: % (gender, age, disability, divorce)', v_dealbreakers;
    RAISE NOTICE 'Marriage Planning: 2 (timeline, children - weighted scoring)';
    RAISE NOTICE 'Gottman Four Horsemen: 6 (conflict resolution)';
    RAISE NOTICE 'Attachment & Emotional: 5 (security, trust, support)';
    RAISE NOTICE 'Korean Family Culture: 5 (approval, filial piety, rites)';
    RAISE NOTICE 'Lifestyle & Values: 7';
    RAISE NOTICE 'Additional Important: 3 (pets, social balance, physical affection)';
    RAISE NOTICE 'Lifestyle Basics: 3 (location, drinking, smoking)';
    RAISE NOTICE 'Open-ended Text: 5 (semantic AI matching)';
    RAISE NOTICE '==========================================';
END $$;
