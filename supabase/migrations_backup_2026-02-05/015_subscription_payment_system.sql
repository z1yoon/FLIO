-- ==========================================
-- FLIO Subscription & Payment System
-- ==========================================
-- Description: Hybrid tier system with trust score eligibility + payment requirement
-- Consolidated from: 006_subscription_payment_system.sql (entire file)
-- Date: 2026-01-23
--
-- HYBRID SYSTEM:
-- 1. trust_tier = Eligibility based on trust score (what you CAN buy)
-- 2. paid_tier = What user actually paid for (what they GET)
-- 3. Benefits come from paid_tier, not trust_tier
--
-- PRICING (per month):
-- - Pebble (조약돌): Free (0-19% trust score)
-- - Shell (조개): ₩9,900 (20-39% trust score required)
-- - Pearl (진주): ₩19,900 (40-59% trust score required)
-- - Coral (산호): ₩39,900 (60-79% trust score required)
-- - Diamond (다이아): ₩59,900 (80-100% trust score required)
-- ==========================================

-- Note: paid_tier, subscription_status, and related columns already defined in 002_core_tables.sql

-- Add index for subscription queries
CREATE INDEX IF NOT EXISTS idx_profiles_paid_tier ON profiles(paid_tier);
CREATE INDEX IF NOT EXISTS idx_profiles_subscription_status ON profiles(subscription_status);

-- ==========================================
-- SUBSCRIPTION PLANS TABLE
-- ==========================================

CREATE TABLE IF NOT EXISTS subscription_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tier_name VARCHAR(20) UNIQUE NOT NULL, -- pebble, shell, pearl, coral, diamond
    tier_name_korean VARCHAR(20) NOT NULL,
    monthly_price_krw INTEGER NOT NULL,
    required_trust_score DECIMAL NOT NULL, -- Minimum trust score to purchase
    daily_matches INTEGER NOT NULL,
    can_see_tiers TEXT[] NOT NULL,
    priority_matching BOOLEAN DEFAULT false,
    features JSONB DEFAULT '[]'::jsonb,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert tier plans
INSERT INTO subscription_plans (tier_name, tier_name_korean, monthly_price_krw, required_trust_score, daily_matches, can_see_tiers, priority_matching, features)
VALUES
    ('pebble', '조약돌', 0, 0.0, 5, ARRAY['pebble'], false, '["기본 프로필", "하루 5명 매칭"]'::jsonb),
    ('shell', '조개', 9900, 0.20, 10, ARRAY['shell', 'pebble'], false, '["기본 프로필", "하루 10명 매칭", "메시지 무제한"]'::jsonb),
    ('pearl', '진주', 19900, 0.40, 15, ARRAY['pearl', 'shell', 'pebble'], false, '["프리미엄 프로필", "하루 15명 매칭", "메시지 무제한", "매칭 필터 고급"]'::jsonb),
    ('coral', '산호', 39900, 0.60, 20, ARRAY['coral', 'pearl', 'shell', 'pebble'], true, '["프리미엄 프로필", "하루 20명 매칭", "메시지 무제한", "매칭 필터 고급", "우선 매칭"]'::jsonb),
    ('diamond', '다이아', 59900, 0.80, 30, ARRAY['diamond', 'coral', 'pearl', 'shell', 'pebble'], true, '["VIP 프로필", "하루 30명 매칭", "메시지 무제한", "매칭 필터 고급", "우선 매칭", "전담 매칭 어드바이저"]'::jsonb)
ON CONFLICT (tier_name) DO UPDATE SET
    monthly_price_krw = EXCLUDED.monthly_price_krw,
    daily_matches = EXCLUDED.daily_matches,
    features = EXCLUDED.features,
    updated_at = NOW();

-- ==========================================
-- USER SUBSCRIPTIONS TABLE
-- ==========================================

CREATE TABLE IF NOT EXISTS user_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    tier_name VARCHAR(20) NOT NULL,

    -- Subscription details
    subscription_type VARCHAR(20) DEFAULT 'monthly', -- monthly, quarterly, yearly
    status VARCHAR(20) DEFAULT 'active', -- active, expired, cancelled, suspended

    -- Dates
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    cancelled_at TIMESTAMPTZ,

    -- Billing
    amount_paid_krw INTEGER NOT NULL,
    currency VARCHAR(3) DEFAULT 'KRW',
    payment_method VARCHAR(50), -- card, bank_transfer, etc.

    -- Auto-renewal
    auto_renew BOOLEAN DEFAULT true,
    next_billing_date TIMESTAMPTZ,

    -- Metadata
    purchase_source VARCHAR(50), -- app, web, promotion
    promotion_code VARCHAR(50),
    discount_applied_krw INTEGER DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_id, started_at) -- One subscription per user per start time
);

CREATE INDEX IF NOT EXISTS idx_user_subscriptions_user_id ON user_subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_status ON user_subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_expires_at ON user_subscriptions(expires_at);

-- ==========================================
-- PAYMENT TRANSACTIONS TABLE
-- ==========================================

CREATE TABLE IF NOT EXISTS payment_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    subscription_id UUID REFERENCES user_subscriptions(id) ON DELETE SET NULL,

    -- Transaction details
    transaction_type VARCHAR(30) NOT NULL, -- subscription_purchase, subscription_renewal, refund
    status VARCHAR(20) DEFAULT 'pending', -- pending, completed, failed, refunded

    -- Amount
    amount_krw INTEGER NOT NULL,
    currency VARCHAR(3) DEFAULT 'KRW',

    -- Payment gateway
    payment_gateway VARCHAR(50), -- toss, kakaopay, etc.
    payment_method VARCHAR(50), -- card, bank_transfer, virtual_account
    gateway_transaction_id VARCHAR(200),
    gateway_response JSONB,

    -- Dates
    initiated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    refunded_at TIMESTAMPTZ,

    -- Refund info
    refund_reason TEXT,
    refund_amount_krw INTEGER,

    -- Metadata
    ip_address INET,
    user_agent TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_payment_transactions_user_id ON payment_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_payment_transactions_subscription_id ON payment_transactions(subscription_id);
CREATE INDEX IF NOT EXISTS idx_payment_transactions_status ON payment_transactions(status);
CREATE INDEX IF NOT EXISTS idx_payment_transactions_gateway_id ON payment_transactions(gateway_transaction_id);

-- ==========================================
-- FUNCTIONS FOR TIER ELIGIBILITY
-- ==========================================

-- Check if user is eligible to purchase a tier
CREATE OR REPLACE FUNCTION check_tier_eligibility(
    p_user_id UUID,
    p_target_tier VARCHAR(20)
)
RETURNS JSONB AS $$
DECLARE
    v_trust_score DECIMAL;
    v_required_score DECIMAL;
    v_current_paid_tier VARCHAR(20);
    v_is_eligible BOOLEAN := false;
    v_reason TEXT;
BEGIN
    -- Get user's trust score
    SELECT total_trust_score INTO v_trust_score
    FROM user_trust_scores
    WHERE user_id = p_user_id;

    IF v_trust_score IS NULL THEN
        v_trust_score := 0.0;
    END IF;

    -- Get required trust score for target tier
    SELECT required_trust_score INTO v_required_score
    FROM subscription_plans
    WHERE tier_name = p_target_tier AND is_active = true;

    IF v_required_score IS NULL THEN
        RETURN jsonb_build_object(
            'eligible', false,
            'reason', 'Invalid tier',
            'trust_score', v_trust_score
        );
    END IF;

    -- Get current paid tier
    SELECT paid_tier INTO v_current_paid_tier
    FROM profiles
    WHERE user_id = p_user_id;

    -- Check eligibility
    IF v_trust_score >= v_required_score THEN
        v_is_eligible := true;
        v_reason := 'Eligible to purchase';
    ELSE
        v_is_eligible := false;
        v_reason := format('신뢰도 %s%% 필요 (현재: %s%%)',
            ROUND(v_required_score * 100),
            ROUND(v_trust_score * 100)
        );
    END IF;

    RETURN jsonb_build_object(
        'eligible', v_is_eligible,
        'reason', v_reason,
        'trust_score', v_trust_score,
        'required_score', v_required_score,
        'current_paid_tier', v_current_paid_tier,
        'target_tier', p_target_tier
    );
END;
$$ LANGUAGE plpgsql;

-- ==========================================
-- FUNCTION TO PURCHASE SUBSCRIPTION
-- ==========================================

CREATE OR REPLACE FUNCTION purchase_subscription(
    p_user_id UUID,
    p_tier_name VARCHAR(20),
    p_subscription_type VARCHAR(20) DEFAULT 'monthly',
    p_payment_method VARCHAR(50) DEFAULT 'card',
    p_amount_paid_krw INTEGER DEFAULT NULL,
    p_promotion_code VARCHAR(50) DEFAULT NULL
)
RETURNS JSONB AS $$
DECLARE
    v_eligibility JSONB;
    v_plan_price INTEGER;
    v_expires_at TIMESTAMPTZ;
    v_subscription_id UUID;
    v_transaction_id UUID;
    v_discount INTEGER := 0;
BEGIN
    -- Check eligibility first
    v_eligibility := check_tier_eligibility(p_user_id, p_tier_name);

    IF NOT (v_eligibility->>'eligible')::BOOLEAN THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Not eligible for this tier',
            'details', v_eligibility
        );
    END IF;

    -- Get plan price
    SELECT monthly_price_krw INTO v_plan_price
    FROM subscription_plans
    WHERE tier_name = p_tier_name AND is_active = true;

    -- Calculate expiry date based on subscription type
    v_expires_at := CASE p_subscription_type
        WHEN 'monthly' THEN NOW() + INTERVAL '1 month'
        WHEN 'quarterly' THEN NOW() + INTERVAL '3 months'
        WHEN 'yearly' THEN NOW() + INTERVAL '1 year'
        ELSE NOW() + INTERVAL '1 month'
    END;

    -- Apply promotion if any (TODO: implement promotion logic)
    IF p_promotion_code IS NOT NULL THEN
        v_discount := 0; -- Placeholder
    END IF;

    -- Use provided amount or plan price
    IF p_amount_paid_krw IS NULL THEN
        p_amount_paid_krw := v_plan_price - v_discount;
    END IF;

    -- Create subscription record
    INSERT INTO user_subscriptions (
        user_id, tier_name, subscription_type, status,
        started_at, expires_at, amount_paid_krw,
        payment_method, promotion_code, discount_applied_krw,
        auto_renew, next_billing_date
    ) VALUES (
        p_user_id, p_tier_name, p_subscription_type, 'active',
        NOW(), v_expires_at, p_amount_paid_krw,
        p_payment_method, p_promotion_code, v_discount,
        true, v_expires_at
    )
    RETURNING id INTO v_subscription_id;

    -- Create payment transaction record
    INSERT INTO payment_transactions (
        user_id, subscription_id, transaction_type, status,
        amount_krw, payment_method, completed_at
    ) VALUES (
        p_user_id, v_subscription_id, 'subscription_purchase', 'completed',
        p_amount_paid_krw, p_payment_method, NOW()
    )
    RETURNING id INTO v_transaction_id;

    -- Update user's paid tier and subscription status
    UPDATE profiles
    SET paid_tier = p_tier_name,
        paid_tier_expires_at = v_expires_at,
        subscription_status = 'active',
        subscription_started_at = NOW(),
        subscription_renewed_at = NOW(),
        daily_match_limit = (SELECT daily_matches FROM subscription_plans WHERE tier_name = p_tier_name),
        updated_at = NOW()
    WHERE user_id = p_user_id;

    RETURN jsonb_build_object(
        'success', true,
        'subscription_id', v_subscription_id,
        'transaction_id', v_transaction_id,
        'tier_name', p_tier_name,
        'expires_at', v_expires_at,
        'amount_paid_krw', p_amount_paid_krw
    );
END;
$$ LANGUAGE plpgsql;

-- ==========================================
-- FUNCTION TO CHECK ACTIVE SUBSCRIPTION
-- ==========================================

CREATE OR REPLACE FUNCTION get_active_subscription(p_user_id UUID)
RETURNS JSONB AS $$
DECLARE
    v_subscription RECORD;
    v_plan RECORD;
BEGIN
    -- Get most recent active subscription
    SELECT * INTO v_subscription
    FROM user_subscriptions
    WHERE user_id = p_user_id
        AND status = 'active'
        AND expires_at > NOW()
    ORDER BY started_at DESC
    LIMIT 1;

    IF v_subscription IS NULL THEN
        -- Return free tier info
        RETURN jsonb_build_object(
            'has_subscription', false,
            'tier_name', 'pebble',
            'tier_name_korean', '조약돌',
            'is_free_tier', true
        );
    END IF;

    -- Get plan details
    SELECT * INTO v_plan
    FROM subscription_plans
    WHERE tier_name = v_subscription.tier_name;

    RETURN jsonb_build_object(
        'has_subscription', true,
        'subscription_id', v_subscription.id,
        'tier_name', v_subscription.tier_name,
        'tier_name_korean', v_plan.tier_name_korean,
        'status', v_subscription.status,
        'started_at', v_subscription.started_at,
        'expires_at', v_subscription.expires_at,
        'auto_renew', v_subscription.auto_renew,
        'days_remaining', EXTRACT(DAY FROM v_subscription.expires_at - NOW()),
        'daily_matches', v_plan.daily_matches,
        'features', v_plan.features,
        'is_free_tier', false
    );
END;
$$ LANGUAGE plpgsql;

-- ==========================================
-- GRANT PERMISSIONS
-- ==========================================

GRANT SELECT ON subscription_plans TO authenticated;
GRANT SELECT, INSERT, UPDATE ON user_subscriptions TO authenticated;
GRANT SELECT, INSERT, UPDATE ON payment_transactions TO authenticated;

GRANT EXECUTE ON FUNCTION check_tier_eligibility TO authenticated;
GRANT EXECUTE ON FUNCTION purchase_subscription TO authenticated;
GRANT EXECUTE ON FUNCTION get_active_subscription TO authenticated;

-- ==========================================
-- MIGRATION COMPLETE
-- ==========================================
-- Summary:
-- 1. Added paid_tier (separate from trust_tier) to profiles
-- 2. Created subscription_plans table with tier pricing
-- 3. Created user_subscriptions table for subscription tracking
-- 4. Created payment_transactions table for payment history
-- 5. Added check_tier_eligibility() function
-- 6. Added purchase_subscription() function
-- 7. Added get_active_subscription() function
--
-- Next steps:
-- 1. Implement payment gateway integration (Toss, KakaoPay)
-- 2. Create mobile app UI for subscription purchase
-- 3. Add subscription renewal logic (cron job)
-- 4. Add subscription cancellation flow
-- ==========================================
