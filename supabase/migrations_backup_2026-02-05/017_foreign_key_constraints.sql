-- ==========================================
-- FLIO Foreign Key Constraint Fixes
-- ==========================================
-- Description: Add missing ON DELETE/UPDATE clauses to foreign keys
-- Date: 2026-02-05
-- ==========================================

-- ==========================================
-- PART 1: FIX QUESTIONS TABLE FOREIGN KEY
-- ==========================================

-- Drop and recreate foreign key with proper ON DELETE clause
ALTER TABLE user_answers
    DROP CONSTRAINT IF EXISTS user_answers_question_id_fkey;

ALTER TABLE user_answers
    ADD CONSTRAINT user_answers_question_id_fkey
    FOREIGN KEY (question_id)
    REFERENCES questions(id)
    ON DELETE CASCADE
    ON UPDATE CASCADE;

COMMENT ON CONSTRAINT user_answers_question_id_fkey ON user_answers IS 'Cascade delete answers when question is deleted';

-- ==========================================
-- PART 2: FIX USER_DOCUMENTS REVIEWED_BY
-- ==========================================

-- This should be SET NULL since reviewed_by is optional and we want to keep documents if reviewer is deleted
ALTER TABLE user_documents
    DROP CONSTRAINT IF EXISTS user_documents_reviewed_by_fkey;

ALTER TABLE user_documents
    ADD CONSTRAINT user_documents_reviewed_by_fkey
    FOREIGN KEY (reviewed_by)
    REFERENCES auth.users(id)
    ON DELETE SET NULL
    ON UPDATE CASCADE;

COMMENT ON CONSTRAINT user_documents_reviewed_by_fkey ON user_documents IS 'Set NULL if reviewer account is deleted';

-- ==========================================
-- PART 3: FIX USER_REPORTS FOREIGN KEYS
-- ==========================================

-- Reporter deleted = delete report
ALTER TABLE user_reports
    DROP CONSTRAINT IF EXISTS user_reports_reporter_user_id_fkey;

ALTER TABLE user_reports
    ADD CONSTRAINT user_reports_reporter_user_id_fkey
    FOREIGN KEY (reporter_user_id)
    REFERENCES auth.users(id)
    ON DELETE CASCADE
    ON UPDATE CASCADE;

-- Reported user deleted = keep report for records
ALTER TABLE user_reports
    DROP CONSTRAINT IF EXISTS user_reports_reported_user_id_fkey;

ALTER TABLE user_reports
    ADD CONSTRAINT user_reports_reported_user_id_fkey
    FOREIGN KEY (reported_user_id)
    REFERENCES auth.users(id)
    ON DELETE RESTRICT
    ON UPDATE CASCADE;

COMMENT ON CONSTRAINT user_reports_reporter_user_id_fkey ON user_reports IS 'Delete reports when reporter account is deleted';
COMMENT ON CONSTRAINT user_reports_reported_user_id_fkey ON user_reports IS 'Prevent deletion of reported user accounts with active reports';

-- ==========================================
-- PART 4: FIX USER_INTERACTIONS FOREIGN KEYS
-- ==========================================

-- Both users deleted = delete interaction
ALTER TABLE user_interactions
    DROP CONSTRAINT IF EXISTS user_interactions_user_id_fkey;

ALTER TABLE user_interactions
    ADD CONSTRAINT user_interactions_user_id_fkey
    FOREIGN KEY (user_id)
    REFERENCES auth.users(id)
    ON DELETE CASCADE
    ON UPDATE CASCADE;

ALTER TABLE user_interactions
    DROP CONSTRAINT IF EXISTS user_interactions_target_user_id_fkey;

ALTER TABLE user_interactions
    ADD CONSTRAINT user_interactions_target_user_id_fkey
    FOREIGN KEY (target_user_id)
    REFERENCES auth.users(id)
    ON DELETE CASCADE
    ON UPDATE CASCADE;

COMMENT ON CONSTRAINT user_interactions_user_id_fkey ON user_interactions IS 'Delete interactions when user is deleted';
COMMENT ON CONSTRAINT user_interactions_target_user_id_fkey ON user_interactions IS 'Delete interactions when target user is deleted';

-- ==========================================
-- PART 5: FIX CONVERSATION_ANALYTICS FOREIGN KEY
-- ==========================================

ALTER TABLE conversation_analytics
    DROP CONSTRAINT IF EXISTS conversation_analytics_user_id_fkey;

ALTER TABLE conversation_analytics
    ADD CONSTRAINT conversation_analytics_user_id_fkey
    FOREIGN KEY (user_id)
    REFERENCES auth.users(id)
    ON DELETE CASCADE
    ON UPDATE CASCADE;

COMMENT ON CONSTRAINT conversation_analytics_user_id_fkey ON conversation_analytics IS 'Delete analytics when user is deleted';

-- ==========================================
-- COMMENTS
-- ==========================================

COMMENT ON SCHEMA public IS 'FLIO Database Schema - Foreign key constraint fixes applied 2026-02-05:
- All foreign keys now have explicit ON DELETE and ON UPDATE clauses
- Proper cascade, restrict, and set null behaviors defined
- Data integrity and referential integrity improved
';
