-- Add daily_match_limit column to profiles table
-- This column is referenced by calculate_trust_score function

ALTER TABLE profiles ADD COLUMN IF NOT EXISTS daily_match_limit INTEGER DEFAULT 5;

-- Update existing profiles based on their current tier
UPDATE profiles
SET daily_match_limit = CASE trust_tier
    WHEN 'diamond' THEN 30
    WHEN 'coral' THEN 20
    WHEN 'pearl' THEN 15
    WHEN 'shell' THEN 10
    ELSE 5
END;
