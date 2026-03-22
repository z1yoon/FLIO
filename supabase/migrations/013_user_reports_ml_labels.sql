-- ==========================================
-- User reports: admin L2 labels + ML suggestion fields
-- ==========================================
-- See docs/REPORT_LABELING_AND_AUTOMATION.md
-- L1 = report_type (user)
-- L2 = admin_label (moderator, canonical code)
-- ==========================================

ALTER TABLE user_reports
    ADD COLUMN IF NOT EXISTS admin_label VARCHAR(80),
    ADD COLUMN IF NOT EXISTS ai_suggested_label VARCHAR(80),
    ADD COLUMN IF NOT EXISTS ai_confidence FLOAT CHECK (ai_confidence IS NULL OR (ai_confidence >= 0.0 AND ai_confidence <= 1.0)),
    ADD COLUMN IF NOT EXISTS ai_model_version VARCHAR(40);

COMMENT ON COLUMN user_reports.admin_label IS
    'L2 fine-grained taxonomy code set by moderator on confirm/dismiss (e.g. identity_photo_mismatch).';
COMMENT ON COLUMN user_reports.ai_suggested_label IS
    'Model-predicted L2 label before human review.';
COMMENT ON COLUMN user_reports.ai_confidence IS
    'Model confidence 0-1; auto-routing only when above policy threshold.';
