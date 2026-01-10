-- ==========================================
-- Reshuffle Feedback System
-- Store user preferences when they request new matches
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

-- Function to get user's recent reshuffle preferences
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

COMMENT ON TABLE reshuffle_feedback IS 'Stores user feedback when requesting new matches to improve future recommendations';
COMMENT ON FUNCTION get_user_reshuffle_context IS 'Retrieves recent reshuffle preferences for a user to provide context';
