-- ==========================================
-- FLIO Database Migration: Upgrade to 1024D embeddings
-- ==========================================
-- Upgrades profile embeddings from 768D to 1024D (BGE-M3)
-- ==========================================

-- Step 1: Add new 1024D column temporarily
ALTER TABLE public.profiles
ADD COLUMN IF NOT EXISTS profile_embedding_temp vector(1024);

-- Step 2: Drop old 768D column and its index
DROP INDEX IF EXISTS idx_profiles_profile_embedding;
ALTER TABLE public.profiles DROP COLUMN IF EXISTS profile_embedding CASCADE;

-- Step 3: Rename temp column to main column name
ALTER TABLE public.profiles RENAME COLUMN profile_embedding_temp TO profile_embedding;

-- Step 4: Create new index for 1024D embeddings
CREATE INDEX IF NOT EXISTS idx_profiles_profile_embedding
ON public.profiles
USING ivfflat (profile_embedding vector_cosine_ops)
WITH (lists = 100);

-- Step 5: Add comment for documentation
COMMENT ON COLUMN public.profiles.profile_embedding IS
'BGE-M3 1024D embedding for profile matching. Upgraded from 768D embeddings.';
