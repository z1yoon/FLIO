-- ==========================================
-- FLIO Subscription & Payment System Migration
-- Migration: 006_subscriptions_and_payments.sql
-- ==========================================
-- Description: Complete subscription tier system with payment processing
-- Created: 2026-02-05
-- Dependencies: 002_core_tables.sql (profiles table)
--
-- HYBRID TIER SYSTEM:
-- 1. trust_tier = Eligibility based on trust score (what user CAN buy)
-- 2. paid_tier = What user actually paid for (what user GETS)
-- 3. All benefits derive from paid_tier, not trust_tier
--
-- TIER PRICING (monthly):
-- - Pebble (조약돌): Free - 0-19% trust score eligibility
-- - Shell (조개): ₩9,900 - 20-39% trust score required
-- - Pearl (진주): ₩19,900 - 40-59% trust score required
-- - Coral (산호): ₩39,900 - 60-79% trust score required
-- - Diamond (다이아): ₩59,900 - 80-100% trust score required
-- ==========================================

-- ==========================================
-- TABLE: subscription_plans
-- ==========================================
-- Purpose: Defines all available subscription tiers with pricing and features
-- Note: This is the single source of truth for tier definitions

CREATE TABLE IF NOT EXISTS subscription_plans (
    -- Primary identification
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tier_name VARCHAR(20) UNIQUE NOT NULL CHECK (tier_name IN ('pebble', 'shell', 'pearl', 'coral', 'diamond')),
    tier_name_korean VARCHAR(20) NOT NULL,

    -- Pricing
    monthly_price_krw INTEGER NOT NULL CHECK (monthly_price_krw >= 0),
    quarterly_price_krw INTEGER NOT NULL CHECK (quarterly_price_krw >= 0),
    yearly_price_krw INTEGER NOT NULL CHECK (yearly_price_krw >= 0),
    currency VARCHAR(3) NOT NULL DEFAULT 'KRW',

    -- Eligibility requirements
    required_trust_score DECIMAL(5,2) NOT NULL CHECK (required_trust_score >= 0.0 AND required_trust_score <= 1.0),

    -- Features and benefits
    daily_matches INTEGER NOT NULL CHECK (daily_matches > 0),
    can_see_tiers TEXT[] NOT NULL,
    priority_matching BOOLEAN NOT NULL DEFAULT false,
    features JSONB NOT NULL DEFAULT '[]'::jsonb,

    -- Display order and availability
    display_order INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT true,

    -- Metadata
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT check_tier_ordering CHECK (display_order >= 0)
);

-- ==========================================
-- TABLE: user_subscriptions
-- ==========================================
-- Purpose: Tracks individual user subscription records and history
-- Note: Users can have multiple records (historical subscriptions)

CREATE TABLE IF NOT EXISTS user_subscriptions (
    -- Primary identification
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    tier_name VARCHAR(20) NOT NULL CHECK (tier_name IN ('pebble', 'shell', 'pearl', 'coral', 'diamond')),

    -- Subscription configuration
    subscription_type VARCHAR(20) NOT NULL DEFAULT 'monthly' CHECK (subscription_type IN ('monthly', 'quarterly', 'yearly')),
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'expired', 'cancelled', 'suspended')),

    -- Lifecycle timestamps
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    cancelled_at TIMESTAMPTZ,
    suspended_at TIMESTAMPTZ,

    -- Billing information
    amount_paid_krw INTEGER NOT NULL CHECK (amount_paid_krw >= 0),
    currency VARCHAR(3) NOT NULL DEFAULT 'KRW',
    payment_method VARCHAR(50) CHECK (payment_method IN ('card', 'bank_transfer', 'kakaopay', 'tosspay', 'payco', 'naverpay', 'virtual_account')),

    -- Auto-renewal configuration
    auto_renew BOOLEAN NOT NULL DEFAULT true,
    next_billing_date TIMESTAMPTZ,

    -- Purchase metadata
    purchase_source VARCHAR(50) CHECK (purchase_source IN ('app', 'web', 'promotion', 'admin')),
    promotion_code VARCHAR(50),
    discount_applied_krw INTEGER NOT NULL DEFAULT 0 CHECK (discount_applied_krw >= 0),

    -- Cancellation tracking
    cancellation_reason TEXT,
    cancelled_by UUID REFERENCES auth.users(id),

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT check_expires_after_start CHECK (expires_at > started_at),
    CONSTRAINT check_cancelled_after_start CHECK (cancelled_at IS NULL OR cancelled_at >= started_at),
    CONSTRAINT check_suspended_after_start CHECK (suspended_at IS NULL OR suspended_at >= started_at),
    CONSTRAINT check_discount_not_exceeds_amount CHECK (discount_applied_krw <= amount_paid_krw)
);

-- ==========================================
-- TABLE: payment_transactions
-- ==========================================
-- Purpose: Complete audit trail of all payment operations
-- Note: Immutable record - never delete, only update status

CREATE TABLE IF NOT EXISTS payment_transactions (
    -- Primary identification
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    subscription_id UUID REFERENCES user_subscriptions(id) ON DELETE SET NULL,

    -- Transaction classification
    transaction_type VARCHAR(30) NOT NULL CHECK (transaction_type IN ('subscription_purchase', 'subscription_renewal', 'refund', 'partial_refund', 'chargeback')),
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'failed', 'refunded', 'partially_refunded', 'cancelled')),

    -- Amount details
    amount_krw INTEGER NOT NULL CHECK (amount_krw > 0),
    currency VARCHAR(3) NOT NULL DEFAULT 'KRW',
    refund_amount_krw INTEGER DEFAULT 0 CHECK (refund_amount_krw >= 0 AND refund_amount_krw <= amount_krw),

    -- Payment gateway integration
    payment_gateway VARCHAR(50) CHECK (payment_gateway IN ('toss', 'kakaopay', 'payco', 'naverpay', 'stripe', 'manual')),
    payment_method VARCHAR(50) CHECK (payment_method IN ('card', 'bank_transfer', 'kakaopay', 'tosspay', 'payco', 'naverpay', 'virtual_account')),
    gateway_transaction_id VARCHAR(200),
    gateway_response JSONB,

    -- State timestamps
    initiated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    refunded_at TIMESTAMPTZ,

    -- Failure and refund details
    failure_reason TEXT,
    refund_reason TEXT,
    refund_requested_by UUID REFERENCES auth.users(id),

    -- Security and audit
    ip_address INET,
    user_agent TEXT,
    device_fingerprint TEXT,

    -- Metadata
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT check_completed_timestamp CHECK (status != 'completed' OR completed_at IS NOT NULL),
    CONSTRAINT check_failed_timestamp CHECK (status != 'failed' OR failed_at IS NOT NULL),
    CONSTRAINT check_refunded_timestamp CHECK (status NOT IN ('refunded', 'partially_refunded') OR refunded_at IS NOT NULL),
    CONSTRAINT check_gateway_id_when_completed CHECK (status != 'completed' OR gateway_transaction_id IS NOT NULL)
);

-- ==========================================
-- SEED DATA: Subscription Plans
-- ==========================================
-- Insert all 5 tier plans with Korean names and comprehensive pricing

INSERT INTO subscription_plans (
    tier_name,
    tier_name_korean,
    monthly_price_krw,
    quarterly_price_krw,
    yearly_price_krw,
    required_trust_score,
    daily_matches,
    can_see_tiers,
    priority_matching,
    features,
    display_order,
    description
) VALUES
    (
        'pebble',
        '조약돌',
        0,
        0,
        0,
        0.0,
        5,
        ARRAY['pebble'],
        false,
        '["기본 프로필", "하루 5명 매칭", "제한된 메시지"]'::jsonb,
        1,
        '신뢰도 시작 단계 - 기본 기능 제공'
    ),
    (
        'shell',
        '조개',
        9900,
        26730,
        95040,
        0.20,
        10,
        ARRAY['shell', 'pebble'],
        false,
        '["기본 프로필", "하루 10명 매칭", "메시지 무제한", "기본 필터"]'::jsonb,
        2,
        '신뢰도 20% 필요 - 일상적 사용에 적합'
    ),
    (
        'pearl',
        '진주',
        19900,
        53730,
        190320,
        0.40,
        15,
        ARRAY['pearl', 'shell', 'pebble'],
        false,
        '["프리미엄 프로필", "하루 15명 매칭", "메시지 무제한", "고급 필터", "읽음 확인"]'::jsonb,
        3,
        '신뢰도 40% 필요 - 프리미엄 경험 제공'
    ),
    (
        'coral',
        '산호',
        39900,
        107730,
        382320,
        0.60,
        20,
        ARRAY['coral', 'pearl', 'shell', 'pebble'],
        true,
        '["프리미엄 프로필", "하루 20명 매칭", "메시지 무제한", "고급 필터", "읽음 확인", "우선 매칭", "프로필 강조"]'::jsonb,
        4,
        '신뢰도 60% 필요 - 우선 매칭 제공'
    ),
    (
        'diamond',
        '다이아',
        59900,
        161730,
        574320,
        0.80,
        30,
        ARRAY['diamond', 'coral', 'pearl', 'shell', 'pebble'],
        true,
        '["VIP 프로필", "하루 30명 매칭", "메시지 무제한", "고급 필터", "읽음 확인", "우선 매칭", "프로필 강조", "전담 매칭 어드바이저", "독점 이벤트 초대"]'::jsonb,
        5,
        '신뢰도 80% 필요 - VIP 전용 혜택'
    )
ON CONFLICT (tier_name) DO UPDATE SET
    tier_name_korean = EXCLUDED.tier_name_korean,
    monthly_price_krw = EXCLUDED.monthly_price_krw,
    quarterly_price_krw = EXCLUDED.quarterly_price_krw,
    yearly_price_krw = EXCLUDED.yearly_price_krw,
    required_trust_score = EXCLUDED.required_trust_score,
    daily_matches = EXCLUDED.daily_matches,
    can_see_tiers = EXCLUDED.can_see_tiers,
    priority_matching = EXCLUDED.priority_matching,
    features = EXCLUDED.features,
    display_order = EXCLUDED.display_order,
    description = EXCLUDED.description,
    updated_at = NOW();

-- ==========================================
-- INDEXES: Foreign Keys and Query Optimization
-- ==========================================

-- Profiles table indexes (for subscription queries)
CREATE INDEX IF NOT EXISTS idx_profiles_paid_tier ON profiles(paid_tier);
CREATE INDEX IF NOT EXISTS idx_profiles_subscription_status ON profiles(subscription_status);
CREATE INDEX IF NOT EXISTS idx_profiles_subscription_expires ON profiles(paid_tier_expires_at);

-- User subscriptions indexes
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_user_id ON user_subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_tier_name ON user_subscriptions(tier_name);
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_status ON user_subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_expires_at ON user_subscriptions(expires_at);
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_next_billing ON user_subscriptions(next_billing_date) WHERE auto_renew = true AND status = 'active';
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_active_user ON user_subscriptions(user_id, status) WHERE status = 'active';

-- Payment transactions indexes
CREATE INDEX IF NOT EXISTS idx_payment_transactions_user_id ON payment_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_payment_transactions_subscription_id ON payment_transactions(subscription_id);
CREATE INDEX IF NOT EXISTS idx_payment_transactions_status ON payment_transactions(status);
CREATE INDEX IF NOT EXISTS idx_payment_transactions_gateway_id ON payment_transactions(gateway_transaction_id);
CREATE INDEX IF NOT EXISTS idx_payment_transactions_type ON payment_transactions(transaction_type);
CREATE INDEX IF NOT EXISTS idx_payment_transactions_created_at ON payment_transactions(created_at DESC);

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_user_active ON user_subscriptions(user_id, status, expires_at) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_payment_transactions_user_completed ON payment_transactions(user_id, status, completed_at) WHERE status = 'completed';

-- ==========================================
-- FUNCTION: check_tier_eligibility
-- ==========================================
-- Purpose: Validate if user's trust score qualifies them to purchase a tier
-- Returns: JSON object with eligibility status and detailed reasoning

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
    v_plan RECORD;
BEGIN
    -- Get user's current trust score
    SELECT total_trust_score INTO v_trust_score
    FROM user_trust_scores
    WHERE user_id = p_user_id;

    -- Default to 0 if no score exists
    IF v_trust_score IS NULL THEN
        v_trust_score := 0.0;
    END IF;

    -- Get target tier plan details
    SELECT * INTO v_plan
    FROM subscription_plans
    WHERE tier_name = p_target_tier AND is_active = true;

    -- Validate tier exists
    IF v_plan.tier_name IS NULL THEN
        RETURN jsonb_build_object(
            'eligible', false,
            'reason', 'Invalid or inactive tier',
            'trust_score', v_trust_score,
            'target_tier', p_target_tier
        );
    END IF;

    v_required_score := v_plan.required_trust_score;

    -- Get user's current paid tier
    SELECT paid_tier INTO v_current_paid_tier
    FROM profiles
    WHERE user_id = p_user_id;

    -- Determine eligibility
    IF v_trust_score >= v_required_score THEN
        v_is_eligible := true;
        v_reason := format('구매 가능: %s (%s)', v_plan.tier_name_korean, v_plan.tier_name);
    ELSE
        v_is_eligible := false;
        v_reason := format('신뢰도 %s%% 필요 (현재: %s%%, 부족: %s%%)',
            ROUND(v_required_score * 100),
            ROUND(v_trust_score * 100),
            ROUND((v_required_score - v_trust_score) * 100)
        );
    END IF;

    -- Return comprehensive eligibility details
    RETURN jsonb_build_object(
        'eligible', v_is_eligible,
        'reason', v_reason,
        'trust_score', v_trust_score,
        'required_score', v_required_score,
        'trust_score_percentage', ROUND(v_trust_score * 100, 1),
        'required_percentage', ROUND(v_required_score * 100, 1),
        'current_paid_tier', v_current_paid_tier,
        'target_tier', p_target_tier,
        'target_tier_korean', v_plan.tier_name_korean,
        'monthly_price_krw', v_plan.monthly_price_krw,
        'quarterly_price_krw', v_plan.quarterly_price_krw,
        'yearly_price_krw', v_plan.yearly_price_krw,
        'daily_matches', v_plan.daily_matches,
        'features', v_plan.features
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ==========================================
-- FUNCTION: purchase_subscription
-- ==========================================
-- Purpose: Process a new subscription purchase with eligibility validation
-- Returns: JSON object with purchase result and subscription details

CREATE OR REPLACE FUNCTION purchase_subscription(
    p_user_id UUID,
    p_tier_name VARCHAR(20),
    p_subscription_type VARCHAR(20) DEFAULT 'monthly',
    p_payment_method VARCHAR(50) DEFAULT 'card',
    p_payment_gateway VARCHAR(50) DEFAULT 'toss',
    p_gateway_transaction_id VARCHAR(200) DEFAULT NULL,
    p_amount_paid_krw INTEGER DEFAULT NULL,
    p_promotion_code VARCHAR(50) DEFAULT NULL,
    p_purchase_source VARCHAR(50) DEFAULT 'app',
    p_ip_address INET DEFAULT NULL,
    p_user_agent TEXT DEFAULT NULL
)
RETURNS JSONB AS $$
DECLARE
    v_eligibility JSONB;
    v_plan RECORD;
    v_final_price INTEGER;
    v_expires_at TIMESTAMPTZ;
    v_next_billing_date TIMESTAMPTZ;
    v_subscription_id UUID;
    v_transaction_id UUID;
    v_discount INTEGER := 0;
    v_existing_subscription RECORD;
BEGIN
    -- Step 1: Validate tier eligibility
    v_eligibility := check_tier_eligibility(p_user_id, p_tier_name);

    IF NOT (v_eligibility->>'eligible')::BOOLEAN THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'not_eligible',
            'message', v_eligibility->>'reason',
            'details', v_eligibility
        );
    END IF;

    -- Step 2: Get plan pricing details
    SELECT * INTO v_plan
    FROM subscription_plans
    WHERE tier_name = p_tier_name AND is_active = true;

    IF v_plan.tier_name IS NULL THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'invalid_tier',
            'message', 'Tier plan not found or inactive'
        );
    END IF;

    -- Step 3: Calculate final price based on subscription type
    v_final_price := CASE p_subscription_type
        WHEN 'monthly' THEN v_plan.monthly_price_krw
        WHEN 'quarterly' THEN v_plan.quarterly_price_krw
        WHEN 'yearly' THEN v_plan.yearly_price_krw
        ELSE v_plan.monthly_price_krw
    END;

    -- Step 4: Apply promotion discount if provided (TODO: implement promotion logic)
    IF p_promotion_code IS NOT NULL THEN
        -- Placeholder for promotion code validation and discount calculation
        v_discount := 0;
    END IF;

    -- Step 5: Calculate expiry and next billing date
    v_expires_at := CASE p_subscription_type
        WHEN 'monthly' THEN NOW() + INTERVAL '1 month'
        WHEN 'quarterly' THEN NOW() + INTERVAL '3 months'
        WHEN 'yearly' THEN NOW() + INTERVAL '1 year'
        ELSE NOW() + INTERVAL '1 month'
    END;

    v_next_billing_date := v_expires_at;

    -- Use provided amount or calculated price
    IF p_amount_paid_krw IS NULL THEN
        p_amount_paid_krw := v_final_price - v_discount;
    END IF;

    -- Step 6: Validate payment amount
    IF p_amount_paid_krw < (v_final_price - v_discount) THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'insufficient_payment',
            'message', format('Payment amount ₩%s is less than required ₩%s', p_amount_paid_krw, v_final_price - v_discount)
        );
    END IF;

    -- Step 7: Cancel any existing active subscriptions
    UPDATE user_subscriptions
    SET status = 'cancelled',
        cancelled_at = NOW(),
        cancellation_reason = 'Replaced by new subscription',
        updated_at = NOW()
    WHERE user_id = p_user_id
        AND status = 'active'
        AND expires_at > NOW();

    -- Step 8: Create new subscription record
    INSERT INTO user_subscriptions (
        user_id, tier_name, subscription_type, status,
        started_at, expires_at, amount_paid_krw,
        payment_method, promotion_code, discount_applied_krw,
        auto_renew, next_billing_date, purchase_source
    ) VALUES (
        p_user_id, p_tier_name, p_subscription_type, 'active',
        NOW(), v_expires_at, p_amount_paid_krw,
        p_payment_method, p_promotion_code, v_discount,
        true, v_next_billing_date, p_purchase_source
    )
    RETURNING id INTO v_subscription_id;

    -- Step 9: Create payment transaction record
    INSERT INTO payment_transactions (
        user_id, subscription_id, transaction_type, status,
        amount_krw, payment_method, payment_gateway,
        gateway_transaction_id, completed_at,
        ip_address, user_agent
    ) VALUES (
        p_user_id, v_subscription_id, 'subscription_purchase', 'completed',
        p_amount_paid_krw, p_payment_method, p_payment_gateway,
        p_gateway_transaction_id, NOW(),
        p_ip_address, p_user_agent
    )
    RETURNING id INTO v_transaction_id;

    -- Step 10: Update user profile with new subscription details
    UPDATE profiles
    SET paid_tier = p_tier_name,
        paid_tier_expires_at = v_expires_at,
        subscription_status = 'active',
        subscription_started_at = NOW(),
        subscription_renewed_at = NOW(),
        daily_match_limit = v_plan.daily_matches,
        updated_at = NOW()
    WHERE user_id = p_user_id;

    -- Step 11: Return success response
    RETURN jsonb_build_object(
        'success', true,
        'subscription_id', v_subscription_id,
        'transaction_id', v_transaction_id,
        'tier_name', p_tier_name,
        'tier_name_korean', v_plan.tier_name_korean,
        'subscription_type', p_subscription_type,
        'started_at', NOW(),
        'expires_at', v_expires_at,
        'amount_paid_krw', p_amount_paid_krw,
        'discount_applied_krw', v_discount,
        'daily_matches', v_plan.daily_matches,
        'features', v_plan.features,
        'message', format('성공적으로 %s 구독을 시작했습니다', v_plan.tier_name_korean)
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ==========================================
-- FUNCTION: get_active_subscription
-- ==========================================
-- Purpose: Retrieve user's current active subscription with plan details
-- Returns: JSON object with subscription info or free tier default

CREATE OR REPLACE FUNCTION get_active_subscription(p_user_id UUID)
RETURNS JSONB AS $$
DECLARE
    v_subscription RECORD;
    v_plan RECORD;
    v_days_remaining INTEGER;
BEGIN
    -- Get most recent active subscription
    SELECT * INTO v_subscription
    FROM user_subscriptions
    WHERE user_id = p_user_id
        AND status = 'active'
        AND expires_at > NOW()
    ORDER BY started_at DESC
    LIMIT 1;

    -- If no active subscription, return free tier (pebble)
    IF v_subscription IS NULL THEN
        SELECT * INTO v_plan
        FROM subscription_plans
        WHERE tier_name = 'pebble';

        RETURN jsonb_build_object(
            'has_subscription', false,
            'tier_name', 'pebble',
            'tier_name_korean', '조약돌',
            'is_free_tier', true,
            'daily_matches', v_plan.daily_matches,
            'features', v_plan.features,
            'message', '무료 구독 중'
        );
    END IF;

    -- Get plan details for active subscription
    SELECT * INTO v_plan
    FROM subscription_plans
    WHERE tier_name = v_subscription.tier_name;

    -- Calculate days remaining
    v_days_remaining := EXTRACT(DAY FROM v_subscription.expires_at - NOW())::INTEGER;

    -- Return active subscription details
    RETURN jsonb_build_object(
        'has_subscription', true,
        'subscription_id', v_subscription.id,
        'tier_name', v_subscription.tier_name,
        'tier_name_korean', v_plan.tier_name_korean,
        'subscription_type', v_subscription.subscription_type,
        'status', v_subscription.status,
        'started_at', v_subscription.started_at,
        'expires_at', v_subscription.expires_at,
        'auto_renew', v_subscription.auto_renew,
        'next_billing_date', v_subscription.next_billing_date,
        'days_remaining', v_days_remaining,
        'daily_matches', v_plan.daily_matches,
        'priority_matching', v_plan.priority_matching,
        'can_see_tiers', v_plan.can_see_tiers,
        'features', v_plan.features,
        'is_free_tier', false,
        'amount_paid_krw', v_subscription.amount_paid_krw,
        'message', format('%s일 남음', v_days_remaining)
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ==========================================
-- FUNCTION: cancel_subscription
-- ==========================================
-- Purpose: Cancel a user's active subscription
-- Returns: JSON object with cancellation result

CREATE OR REPLACE FUNCTION cancel_subscription(
    p_user_id UUID,
    p_cancellation_reason TEXT DEFAULT NULL,
    p_cancelled_by UUID DEFAULT NULL
)
RETURNS JSONB AS $$
DECLARE
    v_subscription RECORD;
    v_rows_updated INTEGER;
BEGIN
    -- Find active subscription
    SELECT * INTO v_subscription
    FROM user_subscriptions
    WHERE user_id = p_user_id
        AND status = 'active'
        AND expires_at > NOW()
    ORDER BY started_at DESC
    LIMIT 1;

    IF v_subscription IS NULL THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'no_active_subscription',
            'message', '활성 구독이 없습니다'
        );
    END IF;

    -- Update subscription status to cancelled
    UPDATE user_subscriptions
    SET status = 'cancelled',
        cancelled_at = NOW(),
        cancellation_reason = p_cancellation_reason,
        cancelled_by = COALESCE(p_cancelled_by, p_user_id),
        auto_renew = false,
        updated_at = NOW()
    WHERE id = v_subscription.id;

    GET DIAGNOSTICS v_rows_updated = ROW_COUNT;

    IF v_rows_updated = 0 THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'update_failed',
            'message', '구독 취소에 실패했습니다'
        );
    END IF;

    -- Note: We don't update the profile immediately
    -- The subscription remains active until expires_at
    -- A cron job will handle the actual tier downgrade at expiry

    RETURN jsonb_build_object(
        'success', true,
        'subscription_id', v_subscription.id,
        'tier_name', v_subscription.tier_name,
        'cancelled_at', NOW(),
        'expires_at', v_subscription.expires_at,
        'message', format('구독이 취소되었습니다. %s까지 계속 사용 가능합니다.',
            TO_CHAR(v_subscription.expires_at, 'YYYY-MM-DD'))
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ==========================================
-- FUNCTION: process_expired_subscriptions
-- ==========================================
-- Purpose: Batch process expired subscriptions and downgrade users
-- Note: Should be called by a cron job (e.g., daily)

CREATE OR REPLACE FUNCTION process_expired_subscriptions()
RETURNS JSONB AS $$
DECLARE
    v_expired_count INTEGER := 0;
    v_downgraded_count INTEGER := 0;
    v_subscription RECORD;
BEGIN
    -- Find all expired subscriptions that haven't been processed
    FOR v_subscription IN
        SELECT id, user_id, tier_name
        FROM user_subscriptions
        WHERE status = 'active'
            AND expires_at <= NOW()
            AND auto_renew = false
    LOOP
        -- Update subscription status to expired
        UPDATE user_subscriptions
        SET status = 'expired',
            updated_at = NOW()
        WHERE id = v_subscription.id;

        v_expired_count := v_expired_count + 1;

        -- Downgrade user to free tier (pebble)
        UPDATE profiles
        SET paid_tier = 'pebble',
            paid_tier_expires_at = NULL,
            subscription_status = 'expired',
            daily_match_limit = (SELECT daily_matches FROM subscription_plans WHERE tier_name = 'pebble'),
            updated_at = NOW()
        WHERE user_id = v_subscription.user_id;

        v_downgraded_count := v_downgraded_count + 1;
    END LOOP;

    RETURN jsonb_build_object(
        'success', true,
        'expired_subscriptions', v_expired_count,
        'downgraded_users', v_downgraded_count,
        'processed_at', NOW()
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ==========================================
-- FUNCTION: process_refund
-- ==========================================
-- Purpose: Process payment refund and update subscription status
-- Returns: JSON object with refund processing result

CREATE OR REPLACE FUNCTION process_refund(
    p_transaction_id UUID,
    p_refund_amount_krw INTEGER,
    p_refund_reason TEXT,
    p_refunded_by UUID
)
RETURNS JSONB AS $$
DECLARE
    v_transaction RECORD;
    v_is_full_refund BOOLEAN;
    v_new_status VARCHAR(20);
BEGIN
    -- Get transaction details
    SELECT * INTO v_transaction
    FROM payment_transactions
    WHERE id = p_transaction_id
        AND status = 'completed';

    IF v_transaction IS NULL THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'transaction_not_found',
            'message', '완료된 거래를 찾을 수 없습니다'
        );
    END IF;

    -- Validate refund amount
    IF p_refund_amount_krw > v_transaction.amount_krw THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'invalid_refund_amount',
            'message', '환불 금액이 거래 금액을 초과합니다'
        );
    END IF;

    -- Determine if full or partial refund
    v_is_full_refund := (p_refund_amount_krw = v_transaction.amount_krw);
    v_new_status := CASE WHEN v_is_full_refund THEN 'refunded' ELSE 'partially_refunded' END;

    -- Update transaction record
    UPDATE payment_transactions
    SET status = v_new_status,
        refund_amount_krw = p_refund_amount_krw,
        refund_reason = p_refund_reason,
        refund_requested_by = p_refunded_by,
        refunded_at = NOW(),
        updated_at = NOW()
    WHERE id = p_transaction_id;

    -- If full refund, cancel the associated subscription
    IF v_is_full_refund AND v_transaction.subscription_id IS NOT NULL THEN
        UPDATE user_subscriptions
        SET status = 'cancelled',
            cancelled_at = NOW(),
            cancellation_reason = format('전액 환불: %s', p_refund_reason),
            auto_renew = false,
            updated_at = NOW()
        WHERE id = v_transaction.subscription_id;

        -- Downgrade user immediately on full refund
        UPDATE profiles
        SET paid_tier = 'pebble',
            paid_tier_expires_at = NULL,
            subscription_status = 'cancelled',
            daily_match_limit = (SELECT daily_matches FROM subscription_plans WHERE tier_name = 'pebble'),
            updated_at = NOW()
        WHERE user_id = v_transaction.user_id;
    END IF;

    RETURN jsonb_build_object(
        'success', true,
        'transaction_id', p_transaction_id,
        'refund_type', CASE WHEN v_is_full_refund THEN 'full' ELSE 'partial' END,
        'refund_amount_krw', p_refund_amount_krw,
        'original_amount_krw', v_transaction.amount_krw,
        'refunded_at', NOW(),
        'message', format('₩%s 환불 처리 완료', p_refund_amount_krw)
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ==========================================
-- FUNCTION: get_subscription_analytics
-- ==========================================
-- Purpose: Get subscription statistics for a user (admin view)
-- Returns: JSON object with detailed subscription history and spending

CREATE OR REPLACE FUNCTION get_subscription_analytics(p_user_id UUID)
RETURNS JSONB AS $$
DECLARE
    v_total_spent INTEGER;
    v_total_subscriptions INTEGER;
    v_active_subscription JSONB;
    v_subscription_history JSONB;
    v_payment_history JSONB;
BEGIN
    -- Get total amount spent
    SELECT COALESCE(SUM(amount_krw), 0) INTO v_total_spent
    FROM payment_transactions
    WHERE user_id = p_user_id
        AND status = 'completed';

    -- Get total subscription count
    SELECT COUNT(*) INTO v_total_subscriptions
    FROM user_subscriptions
    WHERE user_id = p_user_id;

    -- Get active subscription
    v_active_subscription := get_active_subscription(p_user_id);

    -- Get subscription history
    SELECT jsonb_agg(
        jsonb_build_object(
            'id', id,
            'tier_name', tier_name,
            'subscription_type', subscription_type,
            'status', status,
            'started_at', started_at,
            'expires_at', expires_at,
            'amount_paid_krw', amount_paid_krw
        ) ORDER BY started_at DESC
    ) INTO v_subscription_history
    FROM user_subscriptions
    WHERE user_id = p_user_id;

    -- Get payment history
    SELECT jsonb_agg(
        jsonb_build_object(
            'id', id,
            'transaction_type', transaction_type,
            'status', status,
            'amount_krw', amount_krw,
            'payment_method', payment_method,
            'completed_at', completed_at,
            'created_at', created_at
        ) ORDER BY created_at DESC
    ) INTO v_payment_history
    FROM payment_transactions
    WHERE user_id = p_user_id;

    RETURN jsonb_build_object(
        'user_id', p_user_id,
        'total_spent_krw', v_total_spent,
        'total_subscriptions', v_total_subscriptions,
        'active_subscription', v_active_subscription,
        'subscription_history', COALESCE(v_subscription_history, '[]'::jsonb),
        'payment_history', COALESCE(v_payment_history, '[]'::jsonb)
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ==========================================
-- TRIGGERS: Auto-update timestamps
-- ==========================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to subscription_plans
CREATE TRIGGER trigger_subscription_plans_updated_at
    BEFORE UPDATE ON subscription_plans
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply to user_subscriptions
CREATE TRIGGER trigger_user_subscriptions_updated_at
    BEFORE UPDATE ON user_subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply to payment_transactions
CREATE TRIGGER trigger_payment_transactions_updated_at
    BEFORE UPDATE ON payment_transactions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ==========================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ==========================================

-- Enable RLS on all tables
ALTER TABLE subscription_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE payment_transactions ENABLE ROW LEVEL SECURITY;

-- ==========================================
-- RLS: subscription_plans
-- ==========================================

-- Everyone can view active subscription plans
CREATE POLICY policy_subscription_plans_select_all
    ON subscription_plans
    FOR SELECT
    TO authenticated
    USING (is_active = true);

-- Only service role can modify plans
CREATE POLICY policy_subscription_plans_all_service_role
    ON subscription_plans
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- ==========================================
-- RLS: user_subscriptions
-- ==========================================

-- Users can view their own subscriptions
CREATE POLICY policy_user_subscriptions_select_own
    ON user_subscriptions
    FOR SELECT
    TO authenticated
    USING (user_id = auth.uid());

-- Users can insert their own subscriptions (via function)
CREATE POLICY policy_user_subscriptions_insert_own
    ON user_subscriptions
    FOR INSERT
    TO authenticated
    WITH CHECK (user_id = auth.uid());

-- Users can update their own subscriptions (limited fields)
CREATE POLICY policy_user_subscriptions_update_own
    ON user_subscriptions
    FOR UPDATE
    TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- Service role has full access
CREATE POLICY policy_user_subscriptions_all_service_role
    ON user_subscriptions
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- ==========================================
-- RLS: payment_transactions
-- ==========================================

-- Users can view their own payment transactions
CREATE POLICY policy_payment_transactions_select_own
    ON payment_transactions
    FOR SELECT
    TO authenticated
    USING (user_id = auth.uid());

-- Users can create their own payment transactions (via function)
CREATE POLICY policy_payment_transactions_insert_own
    ON payment_transactions
    FOR INSERT
    TO authenticated
    WITH CHECK (user_id = auth.uid());

-- Only service role can update payment transactions
CREATE POLICY policy_payment_transactions_update_service_role
    ON payment_transactions
    FOR UPDATE
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Service role has full access
CREATE POLICY policy_payment_transactions_all_service_role
    ON payment_transactions
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- ==========================================
-- GRANT PERMISSIONS
-- ==========================================

-- Subscription plans (read-only for authenticated users)
GRANT SELECT ON subscription_plans TO authenticated;
GRANT ALL ON subscription_plans TO service_role;

-- User subscriptions (read/write own data)
GRANT SELECT, INSERT, UPDATE ON user_subscriptions TO authenticated;
GRANT ALL ON user_subscriptions TO service_role;

-- Payment transactions (read/write own data)
GRANT SELECT, INSERT ON payment_transactions TO authenticated;
GRANT ALL ON payment_transactions TO service_role;

-- Functions (execute permissions)
GRANT EXECUTE ON FUNCTION check_tier_eligibility TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION purchase_subscription TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION get_active_subscription TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION cancel_subscription TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION process_expired_subscriptions TO service_role;
GRANT EXECUTE ON FUNCTION process_refund TO service_role;
GRANT EXECUTE ON FUNCTION get_subscription_analytics TO authenticated, service_role;

-- ==========================================
-- COMMENTS: Table and Column Documentation
-- ==========================================

-- Subscription plans table
COMMENT ON TABLE subscription_plans IS 'Master table defining all subscription tier plans with pricing and features';
COMMENT ON COLUMN subscription_plans.tier_name IS 'Unique tier identifier (pebble, shell, pearl, coral, diamond)';
COMMENT ON COLUMN subscription_plans.tier_name_korean IS 'Korean display name for tier (조약돌, 조개, 진주, 산호, 다이아)';
COMMENT ON COLUMN subscription_plans.required_trust_score IS 'Minimum trust score (0.0-1.0) required to purchase this tier';
COMMENT ON COLUMN subscription_plans.daily_matches IS 'Number of daily matches allowed for this tier';
COMMENT ON COLUMN subscription_plans.can_see_tiers IS 'Array of tier names this tier can view in matching';
COMMENT ON COLUMN subscription_plans.priority_matching IS 'Whether this tier gets priority in matching algorithm';

-- User subscriptions table
COMMENT ON TABLE user_subscriptions IS 'Individual user subscription records and history';
COMMENT ON COLUMN user_subscriptions.subscription_type IS 'Billing cycle (monthly, quarterly, yearly)';
COMMENT ON COLUMN user_subscriptions.status IS 'Current status (active, expired, cancelled, suspended)';
COMMENT ON COLUMN user_subscriptions.auto_renew IS 'Whether subscription will automatically renew at expiry';
COMMENT ON COLUMN user_subscriptions.next_billing_date IS 'Next scheduled billing date if auto_renew is enabled';

-- Payment transactions table
COMMENT ON TABLE payment_transactions IS 'Immutable audit trail of all payment operations';
COMMENT ON COLUMN payment_transactions.transaction_type IS 'Type of transaction (subscription_purchase, subscription_renewal, refund)';
COMMENT ON COLUMN payment_transactions.status IS 'Payment status (pending, completed, failed, refunded)';
COMMENT ON COLUMN payment_transactions.gateway_transaction_id IS 'External payment gateway transaction identifier';
COMMENT ON COLUMN payment_transactions.gateway_response IS 'Full JSON response from payment gateway';

-- ==========================================
-- MIGRATION COMPLETE
-- ==========================================
-- Summary:
-- 1. Created subscription_plans table with 5 tiers and Korean pricing
-- 2. Created user_subscriptions table with comprehensive tracking
-- 3. Created payment_transactions table with full audit trail
-- 4. Added seed data for all 5 subscription tiers
-- 5. Created indexes for all foreign keys and common queries
-- 6. Implemented check_tier_eligibility() function
-- 7. Implemented purchase_subscription() function with validation
-- 8. Implemented get_active_subscription() function
-- 9. Implemented cancel_subscription() function
-- 10. Implemented process_expired_subscriptions() batch function
-- 11. Implemented process_refund() function
-- 12. Implemented get_subscription_analytics() function
-- 13. Added updated_at triggers for all tables
-- 14. Configured complete RLS policies for security
-- 15. Added comprehensive comments and documentation
--
-- Next Steps:
-- 1. Integrate payment gateways (Toss, KakaoPay, etc.)
-- 2. Set up cron job for process_expired_subscriptions()
-- 3. Implement promotion code system
-- 4. Create admin dashboard for subscription management
-- 5. Add subscription renewal notification system
-- 6. Implement subscription downgrade/upgrade flows
-- ==========================================
