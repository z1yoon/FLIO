-- Migration: Tier-Based Matching System with Ocean Pearl Theme
-- Description: Add tier preference settings and tier-based matching filters
-- Author: FLIO Team
-- Date: 2026-01-18

-- Add tier_preferences column to profiles table
-- Stores which tiers a user wants to match with (e.g., ['pearl', 'shell'] for Pearl tier user)
ALTER TABLE profiles
ADD COLUMN IF NOT EXISTS tier_preferences TEXT[] DEFAULT NULL;

-- Create index for tier-based queries
CREATE INDEX IF NOT EXISTS idx_profiles_trust_tier ON profiles(trust_tier);
CREATE INDEX IF NOT EXISTS idx_profiles_tier_preferences ON profiles USING GIN(tier_preferences);

-- Function to calculate tier from trust score (Ocean Pearl Theme)
CREATE OR REPLACE FUNCTION calculate_tier_from_score(score DECIMAL)
RETURNS TEXT AS $$
BEGIN
  IF score >= 0.80 THEN RETURN 'diamond';
  ELSIF score >= 0.60 THEN RETURN 'coral';
  ELSIF score >= 0.40 THEN RETURN 'pearl';
  ELSIF score >= 0.20 THEN RETURN 'shell';
  ELSE RETURN 'pebble';
  END IF;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to get default tier preferences based on current tier
CREATE OR REPLACE FUNCTION get_default_tier_preferences(current_tier TEXT)
RETURNS TEXT[] AS $$
BEGIN
  CASE current_tier
    WHEN 'diamond' THEN RETURN ARRAY['diamond', 'coral', 'pearl', 'shell', 'pebble'];
    WHEN 'coral' THEN RETURN ARRAY['coral', 'pearl', 'shell', 'pebble'];
    WHEN 'pearl' THEN RETURN ARRAY['pearl', 'shell', 'pebble'];
    WHEN 'shell' THEN RETURN ARRAY['shell', 'pebble'];
    ELSE RETURN ARRAY['pebble']; -- pebble can only match pebble
  END CASE;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Update profiles.trust_tier when user_trust_scores changes
CREATE OR REPLACE FUNCTION sync_profile_trust_tier()
RETURNS TRIGGER AS $$
DECLARE
  v_new_tier TEXT;
BEGIN
  -- Calculate new tier from total_trust_score
  v_new_tier := calculate_tier_from_score(NEW.total_trust_score);

  -- Update profiles table
  UPDATE profiles
  SET trust_tier = v_new_tier,
      tier_preferences = COALESCE(tier_preferences, get_default_tier_preferences(v_new_tier))
  WHERE user_id = NEW.user_id;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger on user_trust_scores
DROP TRIGGER IF EXISTS trigger_sync_profile_trust_tier ON user_trust_scores;
CREATE TRIGGER trigger_sync_profile_trust_tier
  AFTER INSERT OR UPDATE OF total_trust_score
  ON user_trust_scores
  FOR EACH ROW
  EXECUTE FUNCTION sync_profile_trust_tier();

-- Backfill tier_preferences for existing users based on their current trust_tier
UPDATE profiles
SET tier_preferences = get_default_tier_preferences(trust_tier)
WHERE tier_preferences IS NULL;

-- Updated find_matches function with tier filtering
CREATE OR REPLACE FUNCTION find_matches_with_tier_filter(
  p_user_id UUID,
  p_min_similarity DECIMAL DEFAULT 0.4,
  p_limit INTEGER DEFAULT 10,
  p_tier_filter TEXT[] DEFAULT NULL
)
RETURNS TABLE (
  user_id UUID,
  similarity_score DECIMAL,
  trust_tier TEXT,
  name TEXT,
  age INTEGER,
  gender TEXT
) AS $$
DECLARE
  v_user_embedding VECTOR(512);
  v_user_gender TEXT;
  v_user_tier TEXT;
  v_allowed_tiers TEXT[];
BEGIN
  -- Get current user's embedding, gender, and tier
  SELECT profile_embedding, gender, trust_tier, tier_preferences
  INTO v_user_embedding, v_user_gender, v_user_tier, v_allowed_tiers
  FROM profiles
  WHERE user_id = p_user_id;

  -- If user hasn't set preferences, use tier filter parameter or defaults
  IF p_tier_filter IS NOT NULL THEN
    v_allowed_tiers := p_tier_filter;
  ELSIF v_allowed_tiers IS NULL THEN
    v_allowed_tiers := get_default_tier_preferences(v_user_tier);
  END IF;

  -- Pebble tier restriction: can ONLY match with pebble
  IF v_user_tier = 'pebble' THEN
    v_allowed_tiers := ARRAY['pebble'];
  END IF;

  RETURN QUERY
  SELECT
    p.user_id,
    (1 - (v_user_embedding <=> p.profile_embedding))::DECIMAL AS similarity,
    p.trust_tier,
    p.real_name,
    EXTRACT(YEAR FROM AGE(p.birth_date))::INTEGER AS age,
    p.gender
  FROM profiles p
  WHERE p.user_id != p_user_id
    AND p.gender != v_user_gender
    AND p.profile_embedding IS NOT NULL
    AND p.trust_tier = ANY(v_allowed_tiers)  -- Tier filter
    AND (1 - (v_user_embedding <=> p.profile_embedding)) >= p_min_similarity
  ORDER BY v_user_embedding <=> p.profile_embedding
  LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT EXECUTE ON FUNCTION calculate_tier_from_score TO authenticated;
GRANT EXECUTE ON FUNCTION get_default_tier_preferences TO authenticated;
GRANT EXECUTE ON FUNCTION find_matches_with_tier_filter TO authenticated;

-- Add comment for documentation
COMMENT ON COLUMN profiles.tier_preferences IS 'Ocean Pearl Theme tiers user wants to match with: pebble(조약돌), shell(조개), pearl(진주), coral(산호), diamond(다이아)';
COMMENT ON COLUMN profiles.trust_tier IS 'Current tier based on trust score: pebble(0-19%), shell(20-39%), pearl(40-59%), coral(60-79%), diamond(80-100%)';
