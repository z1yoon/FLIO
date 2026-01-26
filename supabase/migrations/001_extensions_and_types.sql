-- ==========================================
-- FLIO Database Extensions and Types
-- ==========================================
-- Description: Core PostgreSQL extensions and utility functions
-- Consolidated from: 001_core_schema.sql (lines 9-10)
-- ==========================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;

-- ==========================================
-- UTILITY FUNCTIONS
-- ==========================================

-- Update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ==========================================
-- COMMENTS
-- ==========================================

COMMENT ON EXTENSION vector IS 'PostgreSQL vector extension for similarity search (pgvector)';
COMMENT ON FUNCTION update_updated_at IS 'Trigger function to automatically update updated_at timestamps';
