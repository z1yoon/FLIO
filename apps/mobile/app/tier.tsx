import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  SafeAreaView,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';

import { getCurrentUserId, supabase } from '../services/supabase/client';
import { FLIOAlertAPI } from '../components/FLIOAlert';
import TrustBadge, { getTierFromScore } from '../components/TrustBadge';

interface TierPlan {
  tier: 'pebble' | 'shell' | 'pearl' | 'coral' | 'diamond';
  name: string;
  emoji: string;
  price: string;
  priceMonthly?: string;
  description: string;
  features: string[];
  scoreRange: string;
  color: string;
  gradientColors: readonly [string, string, ...string[]];
}

const TIER_PLANS: TierPlan[] = [
  {
    tier: 'pebble',
    name: '조약돌',
    emoji: '🪨',
    price: '무료',
    description: '기본 매칭 서비스를 시작하세요',
    scoreRange: '0-19% 신뢰도',
    features: [
      '기본 프로필 작성',
      '44개 질문 답변',
      '하루 5명 프로필 보기',
      '기본 매칭 알고리즘',
      '문서 인증 없음',
    ],
    color: '#4FD1C7',
    gradientColors: ['#2E7D7A', '#4FD1C7'] as const,
  },
  {
    tier: 'shell',
    name: '조개',
    emoji: '🐚',
    price: '₩9,900',
    priceMonthly: '/월',
    description: '신분증 인증으로 신뢰 구축',
    scoreRange: '20-39% 신뢰도',
    features: [
      '조약돌 모든 기능',
      '✅ 신분증 인증 필수 (주민등록증/운전면허증)',
      '하루 10명 프로필 보기',
      '고급 필터 사용',
      '매칭 우선순위 상승',
      '신뢰도 배지 표시 (조개 🐚)',
    ],
    color: '#4FD1C7',
    gradientColors: ['#2E7D7A', '#4FD1C7'] as const,
  },
  {
    tier: 'pearl',
    name: '진주',
    emoji: '🫧',
    price: '₩19,900',
    priceMonthly: '/월',
    description: '학력 인증으로 신뢰도 상승',
    scoreRange: '40-59% 신뢰도',
    features: [
      '조개 모든 기능',
      '✅ 신분증 인증 필수',
      '✅ 학력증명서 인증 필수 (졸업증명서)',
      '하루 15명 프로필 보기',
      '무제한 좋아요',
      '매칭 알고리즘 우선 적용',
      '프로필 통계 확인',
      '신뢰 배지 (진주 🫧)',
    ],
    color: '#4FD1C7',
    gradientColors: ['#2E7D7A', '#4FD1C7'] as const,
  },
  {
    tier: 'coral',
    name: '산호',
    emoji: '🪸',
    price: '₩39,900',
    priceMonthly: '/월',
    description: '경제력/직장 인증으로 고신뢰 회원',
    scoreRange: '60-79% 신뢰도',
    features: [
      '진주 모든 기능',
      '✅ 신분증 + 학력 인증 필수',
      '✅ 소득증명서 OR 재직증명서 인증 필수',
      '하루 20명 프로필 보기',
      '1:1 매칭 코디네이터',
      '프리미엄 인증 뱃지 (산호 🪸)',
      '매칭 성공률 분석',
      '우선 고객 지원',
      '특별 이벤트 초대',
    ],
    color: '#4FD1C7',
    gradientColors: ['#2E7D7A', '#4FD1C7'] as const,
  },
  {
    tier: 'diamond',
    name: '다이아',
    emoji: '💎',
    price: '₩99,900',
    priceMonthly: '/월',
    description: 'VIP 완전 인증 - 최고 신뢰도',
    scoreRange: '80-100% 신뢰도',
    features: [
      '산호 모든 기능',
      '✅ 신분증 + 학력 인증 필수',
      '✅ 소득증명서 + 재직증명서 인증 필수 (모두)',
      '하루 25명 프로필 보기',
      '전담 매칭 전문가',
      'VIP 매칭 이벤트 참가',
      '프리미엄 파트너 인증 (다이아 💎)',
      '오프라인 만남 주선',
      '최우선 매칭 알고리즘',
      '진실된 만남 보장',
    ],
    color: '#4FD1C7',
    gradientColors: ['#2E7D7A', '#4FD1C7'] as const,
  },
];

/**
 * Tier/Pricing Page
 * Dedicated page for tier information and upgrades
 */
export default function TierScreen() {
  const [trustScore, setTrustScore] = useState(0);
  const [currentTier, setCurrentTier] = useState<'pebble' | 'shell' | 'pearl' | 'coral' | 'diamond'>('pebble');

  useEffect(() => {
    const fetchUserInfo = async () => {
      try {
        const userId = await getCurrentUserId();

        if (userId) {
          const { data: trustData } = await supabase
            .from('user_trust_scores')
            .select('total_trust_score')
            .eq('user_id', userId)
            .single();

          if (trustData) {
            const score = trustData.total_trust_score;
            setTrustScore(Math.round(score * 100));
            const tier = getTierFromScore(score);
            // Filter out old tier names, only use new ones
            if (['pebble', 'shell', 'pearl', 'coral', 'diamond'].includes(tier)) {
              setCurrentTier(tier as 'pebble' | 'shell' | 'pearl' | 'coral' | 'diamond');
            }
          }
        }
      } catch (error) {
        console.error('❌ Failed to fetch user info:', error);
      }
    };

    fetchUserInfo();
  }, []);

  const goBack = () => {
    router.back();
  };

  const handleUpgrade = (plan: TierPlan) => {
    if (plan.tier === currentTier) {
      FLIOAlertAPI.alert(
        '현재 등급',
        `이미 ${plan.name} 등급을 사용 중입니다.`,
        [{ text: '확인' }]
      );
      return;
    }

    if (plan.tier === 'pebble') {
      FLIOAlertAPI.alert(
        '기본 등급',
        '조약돌은 기본 등급입니다.\n\n구독 결제 + 문서 인증으로 상위 등급으로 올라가세요!',
        [{ text: '확인' }]
      );
      return;
    }

    // Redirect to verification page
    const verificationRequirements = plan.features.filter(f => f.startsWith('✅')).join('\n');

    FLIOAlertAPI.alert(
      `${plan.name} 등급으로 업그레이드`,
      `${plan.name} 등급은 구독 결제 + 문서 인증 둘 다 필요합니다.\n\n필요한 인증:\n${verificationRequirements}\n\n⚠️ 두 조건 모두 충족해야 업그레이드 가능\n\n계정 페이지에서 문서를 인증하시겠습니까?`,
      [
        { text: '취소', style: 'cancel' },
        {
          text: '인증하러 가기',
          style: 'default',
          onPress: () => router.push('/account'),
        },
      ]
    );
  };

  const renderTierCard = (plan: TierPlan) => {
    const isCurrentTier = plan.tier === currentTier;

    return (
      <View key={plan.tier} style={styles.tierCard}>
        <LinearGradient
          colors={plan.gradientColors}
          style={styles.tierCardGradient}
        >
          <View style={styles.tierCardHeader}>
            <Text style={styles.tierEmoji}>{plan.emoji}</Text>
            <Text style={styles.tierName}>{plan.name}</Text>
            {isCurrentTier && (
              <View style={styles.currentBadge}>
                <Text style={styles.currentBadgeText}>현재 등급</Text>
              </View>
            )}
          </View>

          <View style={styles.tierPricing}>
            <Text style={styles.tierPrice}>{plan.price}</Text>
            {plan.priceMonthly && (
              <Text style={styles.tierPriceMonthly}>{plan.priceMonthly}</Text>
            )}
          </View>

          <Text style={styles.tierDescription}>{plan.description}</Text>
          <Text style={styles.tierScoreRange}>신뢰도 범위: {plan.scoreRange}</Text>

          <View style={styles.tierFeatures}>
            {plan.features.map((feature, index) => (
              <View key={index} style={styles.featureRow}>
                <Ionicons name="checkmark-circle" size={16} color="#FFFFFF" />
                <Text style={styles.featureText}>{feature}</Text>
              </View>
            ))}
          </View>

          <TouchableOpacity
            style={[
              styles.upgradeButton,
              isCurrentTier && styles.upgradeButtonDisabled,
            ]}
            onPress={() => handleUpgrade(plan)}
            activeOpacity={0.8}
            disabled={isCurrentTier}
          >
            <Text style={styles.upgradeButtonText}>
              {isCurrentTier ? '현재 등급' : plan.tier === 'pebble' ? '무료 등급' : '구독 + 인증하기'}
            </Text>
          </TouchableOpacity>
        </LinearGradient>
      </View>
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="light" />

      <LinearGradient
        colors={['#2E7D7A', '#4FD1C7', '#7EDDD9']}
        style={styles.backgroundGradient}
      />

      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity
          style={styles.backButton}
          onPress={goBack}
          activeOpacity={0.7}
        >
          <Ionicons name="chevron-back" size={24} color="#FFFFFF" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>등급 & 요금제</Text>
        <View style={styles.headerSpacer} />
      </View>

      <ScrollView
        style={styles.scrollView}
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
      >
        {/* Current Status */}
        <View style={styles.currentStatusCard}>
          <View style={styles.statusHeader}>
            <Text style={styles.statusTitle}>현재 등급</Text>
            <TrustBadge tier={currentTier} size="medium" />
          </View>
          <Text style={styles.statusScore}>신뢰도: {trustScore}%</Text>
          <Text style={styles.statusDescription}>
            문서 인증으로 더 많은 기능 사용
          </Text>
        </View>

        {/* Tier Plans */}
        <Text style={styles.sectionTitle}>모든 등급</Text>
        {TIER_PLANS.map(renderTierCard)}

        {/* Info Section */}
        <View style={styles.infoSection}>
          <View style={styles.infoCard}>
            <Ionicons name="shield-checkmark" size={24} color="#4FD1C7" />
            <Text style={styles.infoTitle}>등급별 요금 및 인증</Text>
            <Text style={styles.infoText}>
              • 조개 🐚: ₩9,900/월 + 신분증 인증{'\n'}
              • 진주 🫧: ₩19,900/월 + 학력증명서{'\n'}
              • 산호 🪸: ₩39,900/월 + 소득/재직 중 하나{'\n'}
              • 다이아 💎: ₩99,900/월 + 소득 + 재직 모두
            </Text>
            <TouchableOpacity
              style={styles.verificationButton}
              onPress={() => router.push('/account')}
            >
              <Text style={styles.verificationButtonText}>인증하기</Text>
              <Ionicons name="arrow-forward" size={16} color="#2E7D7A" />
            </TouchableOpacity>
          </View>

          <View style={styles.infoCard}>
            <Ionicons name="heart" size={24} color="#FF6B6B" />
            <Text style={styles.infoTitle}>신뢰할 수 있는 매칭</Text>
            <Text style={styles.infoText}>
              문서 인증을 통해:{'\n'}
              • 진실한 정보로 매칭{'\n'}
              • 신뢰할 수 있는 파트너 발견{'\n'}
              • 결혼을 진지하게 생각하는 사람들{'\n\n'}
              FLIO는 <Text style={{fontWeight: 'bold'}}>진실된 결혼 중개</Text>를 목표로 합니다.
            </Text>
          </View>

          <View style={styles.infoCard}>
            <Ionicons name="information-circle" size={24} color="#4FD1C7" />
            <Text style={styles.infoTitle}>등급별 매칭 수</Text>
            <Text style={styles.infoText}>
              문서 인증 수준에 따라 매칭 수가 증가합니다:{'\n\n'}
              • 조약돌 🪨: 하루 5명 (인증 없음){'\n'}
              • 조개 🐚: 하루 10명 (신분증){'\n'}
              • 진주 🫧: 하루 15명 (+ 학력){'\n'}
              • 산호 🪸: 하루 20명 (+ 경제력){'\n'}
              • 다이아 💎: 하루 25명 (완전 인증){'\n\n'}
              <Text style={{fontWeight: 'bold'}}>더 많이 인증할수록 더 좋은 매칭!</Text>
            </Text>
          </View>

          <View style={styles.infoCard}>
            <Ionicons name="document-text" size={24} color="#4FD1C7" />
            <Text style={styles.infoTitle}>안전한 인증 시스템</Text>
            <Text style={styles.infoText}>
              • Azure AI Vision OCR 기술 사용{'\n'}
              • 주민번호는 뒷자리 4자리만 저장{'\n'}
              • 문서 진위 여부 자동 검증{'\n'}
              • 평균 처리 시간: 30초 이내{'\n'}
              • 개인정보 암호화 보관
            </Text>
          </View>
        </View>

        <View style={styles.bottomSpacer} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#2E7D7A',
  },
  backgroundGradient: {
    ...StyleSheet.absoluteFillObject,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingVertical: 16,
    paddingTop: 20,
  },
  backButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(255,255,255,0.1)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  headerSpacer: {
    width: 40,
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    paddingHorizontal: 20,
    paddingBottom: 40,
  },
  currentStatusCard: {
    backgroundColor: 'rgba(255,255,255,0.25)',
    borderRadius: 16,
    padding: 20,
    marginBottom: 24,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.3)',
  },
  statusHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  statusTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  statusScore: {
    fontSize: 16,
    color: '#FFFFFF',
    marginBottom: 8,
    fontWeight: '600',
  },
  statusDescription: {
    fontSize: 14,
    color: '#FFFFFF',
    opacity: 0.9,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#FFFFFF',
    marginBottom: 16,
  },
  tierCard: {
    marginBottom: 20,
    borderRadius: 16,
    overflow: 'hidden',
    position: 'relative',
  },
  tierCardGradient: {
    padding: 20,
  },
  tierCardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
    gap: 8,
  },
  tierEmoji: {
    fontSize: 32,
  },
  tierName: {
    fontSize: 24,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  currentBadge: {
    backgroundColor: 'rgba(255,255,255,0.3)',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 8,
    marginLeft: 8,
  },
  currentBadgeText: {
    color: '#FFFFFF',
    fontSize: 11,
    fontWeight: '600',
  },
  tierPricing: {
    flexDirection: 'row',
    alignItems: 'baseline',
    marginBottom: 8,
  },
  tierPrice: {
    fontSize: 28,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  tierPriceMonthly: {
    fontSize: 16,
    color: 'rgba(255,255,255,0.8)',
    marginLeft: 4,
  },
  tierDescription: {
    fontSize: 15,
    color: 'rgba(255,255,255,0.9)',
    marginBottom: 4,
  },
  tierScoreRange: {
    fontSize: 13,
    color: 'rgba(255,255,255,0.7)',
    marginBottom: 16,
  },
  tierFeatures: {
    marginBottom: 20,
  },
  featureRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
    gap: 8,
  },
  featureText: {
    fontSize: 14,
    color: '#FFFFFF',
    flex: 1,
  },
  upgradeButton: {
    backgroundColor: 'rgba(255,255,255,0.9)',
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
  },
  upgradeButtonDisabled: {
    backgroundColor: 'rgba(255,255,255,0.3)',
  },
  upgradeButtonText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#2E7D7A',
  },
  infoSection: {
    marginTop: 20,
  },
  infoCard: {
    backgroundColor: 'rgba(255,255,255,0.25)',
    borderRadius: 16,
    padding: 20,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.3)',
  },
  infoTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#FFFFFF',
    marginTop: 8,
    marginBottom: 8,
  },
  infoText: {
    fontSize: 14,
    color: '#FFFFFF',
    lineHeight: 20,
    opacity: 0.95,
  },
  verificationButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    paddingVertical: 12,
    marginTop: 12,
    gap: 6,
  },
  verificationButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#2E7D7A',
  },
  bottomSpacer: {
    height: 20,
  },
});
