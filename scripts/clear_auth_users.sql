-- Clear all authenticated users and their data
-- Run this when you need to reset all user accounts

-- This will cascade delete:
-- - profiles
-- - user_answers
-- - user_documents
-- - photo_verifications
-- - social_verifications
-- - user_trust_scores
-- - All other user-related data

TRUNCATE auth.users CASCADE;

-- Verify deletion
SELECT COUNT(*) as remaining_users FROM auth.users;
