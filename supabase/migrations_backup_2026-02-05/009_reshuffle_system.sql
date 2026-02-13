-- ==========================================
-- FLIO Reshuffle Feedback & Preference Analysis System
-- ==========================================
-- Description: User feedback when requesting new matches and AI analysis caching
-- Consolidated from: 003_reshuffle_system.sql (entire file)
-- ==========================================

-- ==========================================
-- Reshuffle Feedback Table
-- ==========================================
CREATE TABLE IF NOT EXISTS reshuffle_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(user_id) ON DELETE CASCADE,
    preference_text TEXT NOT NULL,
    rejected_match_ids UUID[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- AI-analyzed preferences
    analyzed_preferences JSONB,
    preference_categories TEXT[],

    -- Matching context
    previous_match_count INTEGER,
    new_match_count INTEGER,

    INDEX idx_reshuffle_user ON reshuffle_feedback(user_id, created_at DESC)
);

-- ==========================================
-- Preference Analysis Cache Table
-- ==========================================
CREATE TABLE IF NOT EXISTS preference_analysis_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    preference_text TEXT NOT NULL UNIQUE,
    analysis_data JSONB NOT NULL,
    usage_count INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    INDEX idx_preference_text ON preference_analysis_cache(preference_text),
    INDEX idx_usage_count ON preference_analysis_cache(usage_count DESC, created_at DESC)
);

-- ==========================================
-- Functions: Reshuffle Context
-- ==========================================
CREATE OR REPLACE FUNCTION get_user_reshuffle_context(p_user_id UUID, p_limit INT DEFAULT 3)
RETURNS TABLE (
    preference_text TEXT,
    analyzed_preferences JSONB,
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        rf.preference_text,
        rf.analyzed_preferences,
        rf.created_at
    FROM reshuffle_feedback rf
    WHERE rf.user_id = p_user_id
    ORDER BY rf.created_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- ==========================================
-- Functions: Cache Management
-- ==========================================
CREATE OR REPLACE FUNCTION increment_preference_usage(p_preference_text TEXT)
RETURNS VOID AS $$
BEGIN
    UPDATE preference_analysis_cache
    SET usage_count = usage_count + 1,
        updated_at = NOW()
    WHERE preference_text = LOWER(TRIM(p_preference_text));
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION clean_preference_cache()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    WITH ranked_preferences AS (
        SELECT id,
               ROW_NUMBER() OVER (ORDER BY usage_count DESC, updated_at DESC) as rank
        FROM preference_analysis_cache
    )
    DELETE FROM preference_analysis_cache
    WHERE id IN (
        SELECT id FROM ranked_preferences WHERE rank > 1000
    );

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ==========================================
-- Seed Cache with Common Korean Preferences
-- ==========================================
INSERT INTO preference_analysis_cache (preference_text, analysis_data, usage_count) VALUES
('매운걸 좋아하는 사람', '{
    "preference_category": "음식",
    "search_keywords": ["매운", "맵", "매콤", "화끈"],
    "answer_patterns": ["매운 음식을 좋아한다", "맵게 먹는다", "매콤한 것을 선호"],
    "matching_criteria": {
        "must_have": ["매운음식선호"],
        "nice_to_have": ["요리관심", "외식선호"],
        "avoid": ["매운음식싫어", "순한맛선호"]
    },
    "confidence_score": 0.9,
    "explanation": "매운 음식을 좋아하는 사람을 찾는 명확한 요청"
}', 10),

('운동 좋아하는 사람', '{
    "preference_category": "활동",
    "search_keywords": ["운동", "헬스", "피트니스", "체육관", "요가"],
    "answer_patterns": ["운동을 즐긴다", "헬스장을 다닌다", "피트니스에 관심"],
    "matching_criteria": {
        "must_have": ["운동관심", "건강관리"],
        "nice_to_have": ["활동적성향", "규칙적생활"],
        "avoid": ["운동싫어", "집에만있기선호"]
    },
    "confidence_score": 0.9,
    "explanation": "활동적이고 운동을 좋아하는 사람을 원하는 요청"
}', 8),

('가족을 중시하는 사람', '{
    "preference_category": "가치관",
    "search_keywords": ["가족", "가정", "부모님", "효도", "가족모임"],
    "answer_patterns": ["가족을 중요하게 생각", "가정적인 사람", "부모님께 효도"],
    "matching_criteria": {
        "must_have": ["가족중시", "가정적성향"],
        "nice_to_have": ["책임감", "전통적가치관"],
        "avoid": ["개인주의", "가족무관심"]
    },
    "confidence_score": 0.85,
    "explanation": "가족을 중요하게 생각하는 전통적 가치관을 가진 사람을 원함"
}', 6);

-- ==========================================
-- Comments
-- ==========================================
COMMENT ON TABLE reshuffle_feedback IS 'Stores user feedback when requesting new matches to improve future recommendations';
COMMENT ON TABLE preference_analysis_cache IS 'Caches AI analysis results for user preferences to reduce API costs and improve performance';
COMMENT ON FUNCTION get_user_reshuffle_context IS 'Retrieves recent reshuffle preferences for a user to provide context';
COMMENT ON FUNCTION increment_preference_usage IS 'Tracks usage statistics for preference analysis cache';
COMMENT ON FUNCTION clean_preference_cache IS 'Maintains cache size by removing least used entries';
