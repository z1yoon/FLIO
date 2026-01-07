-- FLIO Initial Database Schema
-- Supabase PostgreSQL with pgvector extension

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;

-- Users table (extends Supabase auth.users)
CREATE TABLE public.profiles (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Basic info
    nickname VARCHAR(50) NOT NULL,
    birth_date DATE NOT NULL,
    gender VARCHAR(10) NOT NULL CHECK (gender IN ('male', 'female', 'other')),
    bio TEXT,
    
    -- Photos (Supabase Storage URLs)
    photos TEXT[] DEFAULT '{}',
    
    -- Profile answers (JSON)
    answers JSONB DEFAULT '{}',
    
    -- Embeddings for AI matching
    profile_embedding vector(768),  -- ko-sroberta embedding
    face_embedding vector(512),     -- InsightFace/ArcFace embedding
    
    -- Verification status (Face verification is the primary focus)
    face_verified BOOLEAN DEFAULT FALSE,
    face_verified_at TIMESTAMP WITH TIME ZONE,
    face_similarity_score FLOAT,  -- Store the 85%+ match score
    
    -- Optional future verifications
    education_verified BOOLEAN DEFAULT FALSE,
    job_verified BOOLEAN DEFAULT FALSE,
    
    -- Settings
    is_active BOOLEAN DEFAULT TRUE,
    last_active_at TIMESTAMP WITH TIME ZONE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Verifications table
CREATE TABLE public.verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    type VARCHAR(20) NOT NULL CHECK (type IN ('face', 'height', 'education', 'job', 'income')),
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'verified', 'rejected')),
    
    -- Verification data
    data JSONB DEFAULT '{}',
    
    -- Result
    verified_at TIMESTAMP WITH TIME ZONE,
    rejection_reason TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Matches table
CREATE TABLE public.matches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    user_a_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    user_b_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Match score and explanation
    score FLOAT NOT NULL,
    explanation TEXT,
    
    -- Like status
    user_a_liked BOOLEAN,
    user_b_liked BOOLEAN,
    
    -- Match timestamp (when both liked)
    matched_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure unique pairs
    CONSTRAINT unique_match_pair UNIQUE (user_a_id, user_b_id),
    CONSTRAINT different_users CHECK (user_a_id != user_b_id)
);

-- Messages table (E2EE - content is encrypted)
CREATE TABLE public.messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id UUID NOT NULL REFERENCES public.matches(id) ON DELETE CASCADE,
    sender_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Encrypted message content
    content TEXT NOT NULL,
    encrypted BOOLEAN DEFAULT TRUE,
    
    -- Read status
    read_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Community verification feedback (after meeting)
CREATE TABLE public.meeting_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    reviewer_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    reviewed_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    meeting_date DATE NOT NULL,
    
    -- Feedback fields (focus on face authenticity)
    face_matched_profile BOOLEAN,  -- Did they look like their profile?
    overall_authentic BOOLEAN,     -- Were they genuine?
    would_recommend BOOLEAN,       -- Would you recommend to others?
    
    notes TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- One feedback per meeting
    CONSTRAINT unique_feedback UNIQUE (reviewer_id, reviewed_id, meeting_date)
);

-- Indexes for performance

-- Profile embeddings for similarity search
CREATE INDEX idx_profiles_profile_embedding 
ON public.profiles 
USING ivfflat (profile_embedding vector_cosine_ops)
WITH (lists = 100);

CREATE INDEX idx_profiles_face_embedding
ON public.profiles
USING ivfflat (face_embedding vector_cosine_ops)
WITH (lists = 100);

-- Other indexes
CREATE INDEX idx_profiles_user_id ON public.profiles(user_id);
CREATE INDEX idx_profiles_gender ON public.profiles(gender);
CREATE INDEX idx_profiles_is_active ON public.profiles(is_active);

CREATE INDEX idx_verifications_user_id ON public.verifications(user_id);
CREATE INDEX idx_verifications_type ON public.verifications(type);
CREATE INDEX idx_verifications_status ON public.verifications(status);

CREATE INDEX idx_matches_user_a ON public.matches(user_a_id);
CREATE INDEX idx_matches_user_b ON public.matches(user_b_id);
CREATE INDEX idx_matches_matched_at ON public.matches(matched_at);

CREATE INDEX idx_messages_match_id ON public.messages(match_id);
CREATE INDEX idx_messages_created_at ON public.messages(created_at);

-- Row Level Security (RLS) policies

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.verifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.matches ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.meeting_feedback ENABLE ROW LEVEL SECURITY;

-- Profiles: Users can read others' profiles, but only edit their own
CREATE POLICY "Profiles are viewable by authenticated users"
ON public.profiles FOR SELECT
TO authenticated
USING (is_active = TRUE);

CREATE POLICY "Users can update own profile"
ON public.profiles FOR UPDATE
TO authenticated
USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own profile"
ON public.profiles FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = user_id);

-- Verifications: Users can only see and manage their own
CREATE POLICY "Users can view own verifications"
ON public.verifications FOR SELECT
TO authenticated
USING (auth.uid() = user_id);

CREATE POLICY "Users can create own verifications"
ON public.verifications FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = user_id);

-- Matches: Users can see matches they're part of
CREATE POLICY "Users can view own matches"
ON public.matches FOR SELECT
TO authenticated
USING (auth.uid() IN (user_a_id, user_b_id));

-- Messages: Users can see messages in their matches
CREATE POLICY "Users can view messages in their matches"
ON public.messages FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM public.matches
        WHERE matches.id = messages.match_id
        AND auth.uid() IN (matches.user_a_id, matches.user_b_id)
    )
);

CREATE POLICY "Users can send messages in their matches"
ON public.messages FOR INSERT
TO authenticated
WITH CHECK (
    auth.uid() = sender_id
    AND EXISTS (
        SELECT 1 FROM public.matches
        WHERE matches.id = match_id
        AND matches.matched_at IS NOT NULL
        AND auth.uid() IN (matches.user_a_id, matches.user_b_id)
    )
);

-- Functions

-- Update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER profiles_updated_at
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Find similar profiles using vector similarity
CREATE OR REPLACE FUNCTION find_similar_profiles(
    query_embedding vector(768),
    exclude_user_id UUID,
    match_limit INTEGER DEFAULT 20
)
RETURNS TABLE (
    user_id UUID,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.user_id,
        1 - (p.profile_embedding <=> query_embedding) AS similarity
    FROM public.profiles p
    WHERE p.user_id != exclude_user_id
        AND p.is_active = TRUE
        AND p.profile_embedding IS NOT NULL
    ORDER BY p.profile_embedding <=> query_embedding
    LIMIT match_limit;
END;
$$ LANGUAGE plpgsql;

-- Get user's authenticity score from community feedback
CREATE OR REPLACE FUNCTION get_authenticity_score(target_user_id UUID)
RETURNS TABLE (
    score FLOAT,
    review_count INTEGER,
    face_accuracy FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        AVG(
            CASE WHEN mf.overall_authentic THEN 1.0 ELSE 0.0 END
        )::FLOAT AS score,
        COUNT(*)::INTEGER AS review_count,
        AVG(
            CASE WHEN mf.face_matched_profile THEN 1.0 ELSE 0.0 END
        )::FLOAT AS face_accuracy
    FROM public.meeting_feedback mf
    WHERE mf.reviewed_id = target_user_id
    GROUP BY mf.reviewed_id;
END;
$$ LANGUAGE plpgsql;
