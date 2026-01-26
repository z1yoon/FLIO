-- ==========================================
-- FLIO Core Indexes and Row Level Security
-- ==========================================
-- Description: Indexes and RLS policies for core tables
-- Consolidated from: 001_core_schema.sql (lines 159-277)
-- ==========================================

-- ==========================================
-- INDEXES FOR PROFILES
-- ==========================================

-- Profile embeddings for similarity search
CREATE INDEX idx_profiles_profile_embedding
ON public.profiles
USING ivfflat (profile_embedding vector_cosine_ops)
WITH (lists = 100);

CREATE INDEX idx_profiles_face_embedding
ON public.profiles
USING ivfflat (face_embedding vector_cosine_ops)
WITH (lists = 100);

-- Profile indexes
CREATE INDEX idx_profiles_user_id ON public.profiles(user_id);
CREATE INDEX idx_profiles_gender ON public.profiles(gender);
CREATE INDEX idx_profiles_is_active ON public.profiles(is_active);
CREATE INDEX idx_profiles_trust_tier ON public.profiles(trust_tier);
CREATE INDEX idx_profiles_paid_tier ON public.profiles(paid_tier);
CREATE INDEX idx_profiles_subscription_status ON public.profiles(subscription_status);
CREATE INDEX idx_profiles_tier_preferences ON public.profiles USING GIN(tier_preferences);
CREATE INDEX idx_profiles_has_embedding ON public.profiles(user_id) WHERE profile_embedding IS NOT NULL;

-- ==========================================
-- INDEXES FOR MATCHES
-- ==========================================

CREATE INDEX idx_matches_user_a ON public.matches(user_a_id);
CREATE INDEX idx_matches_user_b ON public.matches(user_b_id);
CREATE INDEX idx_matches_matched_at ON public.matches(matched_at);

-- ==========================================
-- INDEXES FOR MESSAGES
-- ==========================================

CREATE INDEX idx_messages_match_id ON public.messages(match_id);
CREATE INDEX idx_messages_created_at ON public.messages(created_at);

-- ==========================================
-- ROW LEVEL SECURITY
-- ==========================================

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
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
