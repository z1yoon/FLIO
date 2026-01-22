-- ==========================================
-- FLIO Tier-Based Matching Configuration
-- ==========================================
-- Adds tier preference settings for users
-- Matching logic is in migration 010
-- ==========================================

-- Add tier_preferences column to profiles table
-- Stores which tiers a user wants to match with (e.g., ['pearl', 'shell'] for Pearl tier user)
ALTER TABLE profiles
ADD COLUMN IF NOT EXISTS tier_preferences TEXT[] DEFAULT NULL;

-- Create index for tier-based queries
CREATE INDEX IF NOT EXISTS idx_profiles_trust_tier ON profiles(trust_tier);
CREATE INDEX IF NOT EXISTS idx_profiles_tier_preferences ON profiles USING GIN(tier_preferences);

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
SET tier_preferences = get_default_tier_preferences(COALESCE(trust_tier, 'pebble'))
WHERE tier_preferences IS NULL;

-- Grant permissions
GRANT EXECUTE ON FUNCTION get_default_tier_preferences TO authenticated;

-- Add comments
COMMENT ON COLUMN profiles.tier_preferences IS 'Ocean Pearl Theme tiers user wants to match with: pebble(조약돌), shell(조개), pearl(진주), coral(산호), diamond(다이아)';
COMMENT ON COLUMN profiles.trust_tier IS 'Current tier based on trust score: pebble(0-19%), shell(20-39%), pearl(40-59%), coral(60-79%), diamond(80-100%)';
COMMENT ON FUNCTION get_default_tier_preferences IS 'Returns default tier preferences for a given trust tier. Lower tiers can only match with same or lower tiers.';
