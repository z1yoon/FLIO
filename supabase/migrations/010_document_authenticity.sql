-- ==========================================
-- FLIO Migration 010: Document Authenticity Fields
-- Adds authenticity validation fields to user_documents table
-- ==========================================

-- Add authenticity validation fields to user_documents table
ALTER TABLE user_documents ADD COLUMN IF NOT EXISTS authenticity_score FLOAT;
ALTER TABLE user_documents ADD COLUMN IF NOT EXISTS issuer_validated BOOLEAN DEFAULT false;
ALTER TABLE user_documents ADD COLUMN IF NOT EXISTS format_validated BOOLEAN DEFAULT false;
ALTER TABLE user_documents ADD COLUMN IF NOT EXISTS pattern_validated BOOLEAN DEFAULT false;
ALTER TABLE user_documents ADD COLUMN IF NOT EXISTS authenticity_flags JSONB DEFAULT '[]'::jsonb;

-- Add comments for documentation
COMMENT ON COLUMN user_documents.authenticity_score IS 'Document authenticity score (0.0-1.0) based on issuer, format, and pattern validation';
COMMENT ON COLUMN user_documents.issuer_validated IS 'Whether document issuer was validated against official Korean government/institution names';
COMMENT ON COLUMN user_documents.format_validated IS 'Whether document format/structure matches official Korean document formats';
COMMENT ON COLUMN user_documents.pattern_validated IS 'Whether document numbers and patterns match official formats';
COMMENT ON COLUMN user_documents.authenticity_flags IS 'List of authenticity validation issues found (e.g., issuer_not_validated, format_not_validated)';

-- Create index for authenticity score queries
CREATE INDEX IF NOT EXISTS idx_documents_authenticity ON user_documents(authenticity_score DESC)
    WHERE authenticity_score IS NOT NULL;

-- Create index for validation status queries
CREATE INDEX IF NOT EXISTS idx_documents_validation_status ON user_documents(issuer_validated, format_validated, pattern_validated)
    WHERE issuer_validated = true OR format_validated = true OR pattern_validated = true;
