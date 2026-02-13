-- ==========================================
-- FLIO Timestamp Standardization
-- ==========================================
-- Description: Standardize all TIMESTAMP WITH TIME ZONE to TIMESTAMPTZ
-- Date: 2026-02-05
-- Note: TIMESTAMP WITH TIME ZONE and TIMESTAMPTZ are equivalent, this is for consistency
-- ==========================================

-- No actual changes needed as TIMESTAMP WITH TIME ZONE === TIMESTAMPTZ
-- This file documents that the inconsistency is cosmetic only
-- Future migrations should use TIMESTAMPTZ for consistency

-- ==========================================
-- COMMENTS
-- ==========================================

COMMENT ON SCHEMA public IS 'FLIO Database Schema - Timestamp types standardized 2026-02-05:
Note: TIMESTAMP WITH TIME ZONE and TIMESTAMPTZ are equivalent in PostgreSQL.
All future migrations should use TIMESTAMPTZ for consistency.
No data migration required.
';
