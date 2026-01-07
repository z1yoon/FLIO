-- Clear all authenticated users and their data
-- Run this when you need to reset all user accounts

-- This will cascade delete:
-- - user_answers
-- - user_profiles  
-- - user_feedback
-- - All other user-related data

TRUNCATE auth.users CASCADE;

-- Verify deletion
SELECT COUNT(*) as remaining_users FROM auth.users;
