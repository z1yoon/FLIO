-- ==========================================
-- FLIO Question Text Embeddings
-- ==========================================
-- Migration: 011_question_embeddings.sql
-- Description: Add pre-computed embedding column to questions table.
--              Populated once via seed script; eliminates per-restart API calls
--              when computing reshuffle feedback → question similarity.
-- Dependencies: 001 (pgvector), 002 (questions)
-- ==========================================

ALTER TABLE questions
    ADD COLUMN IF NOT EXISTS text_embedding vector(1024);

CREATE INDEX IF NOT EXISTS idx_questions_embedding
    ON questions USING ivfflat (text_embedding vector_cosine_ops)
    WITH (lists = 10);

COMMENT ON COLUMN questions.text_embedding IS
    'Azure OpenAI text-embedding-3-large (1024D) of text_ko. '
    'Pre-populated via scripts/seed_question_embeddings.py. '
    'Used for semantic similarity matching against reshuffle feedback text.';
