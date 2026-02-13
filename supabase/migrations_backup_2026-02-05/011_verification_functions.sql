-- ==========================================
-- FLIO Verification Functions and RLS
-- ==========================================
-- Description: Functions, triggers, and RLS policies for verification system
-- Consolidated from: 004_verification_system.sql (lines 245-467)
-- ==========================================

-- ===================
-- ROW LEVEL SECURITY
-- ===================

ALTER TABLE photo_verifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE phone_verifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE social_verifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_family_background ENABLE ROW LEVEL SECURITY;
ALTER TABLE consistency_checks ENABLE ROW LEVEL SECURITY;

-- Photo verifications
CREATE POLICY "Users can view own photo verifications"
    ON photo_verifications FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can upload own photo verifications"
    ON photo_verifications FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Documents
CREATE POLICY "Users can view own documents"
    ON user_documents FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can upload own documents"
    ON user_documents FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Phone verifications
CREATE POLICY "Users can view own phone verifications"
    ON phone_verifications FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own phone verifications"
    ON phone_verifications FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own phone verifications"
    ON phone_verifications FOR UPDATE USING (auth.uid() = user_id);

-- Social verifications
CREATE POLICY "Users can view own social verifications"
    ON social_verifications FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own social verifications"
    ON social_verifications FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own social verifications"
    ON social_verifications FOR UPDATE USING (auth.uid() = user_id);

-- Family background
CREATE POLICY "Users can view own family background"
    ON user_family_background FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own family background"
    ON user_family_background FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own family background"
    ON user_family_background FOR UPDATE USING (auth.uid() = user_id);

-- Consistency checks (service-managed)
CREATE POLICY "Service can manage consistency checks"
    ON consistency_checks FOR ALL USING (true);

-- ===================
-- HELPER FUNCTIONS
-- ===================

-- Log user behavior (no scoring logic - just logging)
CREATE OR REPLACE FUNCTION log_user_behavior(
    p_user_id UUID,
    p_event_type VARCHAR(50),
    p_event_data JSONB DEFAULT '{}',
    p_field_changed VARCHAR(100) DEFAULT NULL,
    p_old_value TEXT DEFAULT NULL,
    p_new_value TEXT DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_risk_level VARCHAR(20) := 'low';
    v_risk_reason TEXT := NULL;
    v_event_category VARCHAR(30) := 'general';
    v_log_id UUID;
BEGIN
    CASE p_event_type
        WHEN 'income_change' THEN
            v_risk_level := 'high';
            v_risk_reason := 'Income information changed';
            v_event_category := 'critical';
        WHEN 'education_change' THEN
            v_risk_level := 'high';
            v_risk_reason := 'Education information changed';
            v_event_category := 'critical';
        WHEN 'real_name_change' THEN
            v_risk_level := 'critical';
            v_risk_reason := 'Real name changed';
            v_event_category := 'critical';
        WHEN 'answer_rewrite' THEN
            v_risk_level := 'medium';
            v_risk_reason := 'Question answer changed';
            v_event_category := 'important';
        ELSE
            v_risk_level := 'low';
            v_event_category := 'general';
    END CASE;

    INSERT INTO user_behavior_logs (
        user_id, event_type, event_category, event_data,
        field_changed, old_value, new_value,
        risk_level, risk_reason
    ) VALUES (
        p_user_id, p_event_type, v_event_category, p_event_data,
        p_field_changed, p_old_value, p_new_value,
        v_risk_level, v_risk_reason
    )
    RETURNING id INTO v_log_id;

    RETURN v_log_id;
END;
$$ LANGUAGE plpgsql;

-- ===================
-- TRIGGERS
-- ===================

-- Timestamp update trigger
CREATE OR REPLACE FUNCTION trigger_update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_photo_verifications_timestamp ON photo_verifications;
CREATE TRIGGER update_photo_verifications_timestamp
    BEFORE UPDATE ON photo_verifications
    FOR EACH ROW EXECUTE FUNCTION trigger_update_timestamp();

DROP TRIGGER IF EXISTS update_documents_timestamp ON user_documents;
CREATE TRIGGER update_documents_timestamp
    BEFORE UPDATE ON user_documents
    FOR EACH ROW EXECUTE FUNCTION trigger_update_timestamp();

DROP TRIGGER IF EXISTS update_family_background_timestamp ON user_family_background;
CREATE TRIGGER update_family_background_timestamp
    BEFORE UPDATE ON user_family_background
    FOR EACH ROW EXECUTE FUNCTION trigger_update_timestamp();

-- Profile change logging trigger
CREATE OR REPLACE FUNCTION trigger_log_profile_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.annual_income_range IS DISTINCT FROM NEW.annual_income_range THEN
        PERFORM log_user_behavior(
            NEW.user_id, 'income_change',
            jsonb_build_object('field', 'annual_income_range'),
            'annual_income_range', OLD.annual_income_range, NEW.annual_income_range
        );
    END IF;

    IF OLD.education_level IS DISTINCT FROM NEW.education_level THEN
        PERFORM log_user_behavior(
            NEW.user_id, 'education_change',
            jsonb_build_object('field', 'education_level'),
            'education_level', OLD.education_level, NEW.education_level
        );
    END IF;

    IF OLD.real_name IS DISTINCT FROM NEW.real_name THEN
        PERFORM log_user_behavior(
            NEW.user_id, 'real_name_change',
            jsonb_build_object('field', 'real_name'),
            'real_name', OLD.real_name, NEW.real_name
        );
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS log_profile_changes_trigger ON profiles;
CREATE TRIGGER log_profile_changes_trigger
    AFTER UPDATE ON profiles
    FOR EACH ROW EXECUTE FUNCTION trigger_log_profile_changes();
