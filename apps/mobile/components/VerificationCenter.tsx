/**
 * Verification Center Component
 * Shows current tier, benefits, and document verification options
 * Ocean Pearl Theme: 조약돌 → 조개 → 진주 → 산호
 */

import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import TrustBadge, { getTierFromScore } from './TrustBadge';

type TrustTier = 'coral' | 'pearl' | 'shell' | 'pebble';

interface VerificationCenterProps {
  currentTier: TrustTier;
  trustScore: number;
  verifiedDocuments: string[];
  onVerifyDocument: (documentType: string) => void;
  onClose?: () => void;
}

interface TierInfo {
  name: string;
  emoji: string;
  color: string;
  minScore: number;
  dailyMatches: string;
  benefits: string[];
}

const TIER_INFO: Record<TrustTier, TierInfo> = {
  coral: {
    name: '산호 회원',
    emoji: '🪸',
    color: '#FFD700',
    minScore: 60,
    dailyMatches: '20명/일',
    benefits: ['모든 회원 매칭', '하루 20회 조회', '검증 배지', '우선 매칭', 'VIP 지원']
  },
  pearl: {
    name: '진주 회원',
    emoji: '🫧',
    color: '#C0C0C0',
    minScore: 40,
    dailyMatches: '10명/일',
    benefits: ['진주급 이하 매칭', '하루 10회 조회', '기본 검증 배지']
  },
  shell: {
    name: '조개 회원',
    emoji: '🐚',
    color: '#CD7F32',
    minScore: 20,
    dailyMatches: '5명/일',
    benefits: ['조개급 이하 매칭', '하루 5회 조회']
  },
  pebble: {
    name: '조약돌 회원',
    emoji: '🪨',
    color: '#9E9E9E',
    minScore: 0,
    dailyMatches: '3명/일',
    benefits: ['조약돌 회원만 매칭', '하루 3회 조회', '제한된 기능']
  }
};

const DOCUMENT_TYPES = [
  {
    id: 'id',
    name: '신분증 인증',
    icon: 'card-outline' as const,
    trustBoost: 8.75,
    description: '정부 발급 신분증 확인',
    color: '#4FD1C7'
  },
  {
    id: 'education',
    name: '학력 인증',
    icon: 'school-outline' as const,
    trustBoost: 8.75,
    description: '졸업증명서 확인',
    color: '#7EDDD9'
  },
  {
    id: 'income',
    name: '소득 인증',
    icon: 'cash-outline' as const,
    trustBoost: 8.75,
    description: '소득증명서 확인',
    color: '#4FD1C7'
  },
  {
    id: 'employment',
    name: '재직 인증',
    icon: 'briefcase-outline' as const,
    trustBoost: 8.75,
    description: '재직증명서 확인',
    color: '#7EDDD9'
  }
];

export default function VerificationCenter({
  currentTier,
  trustScore,
  verifiedDocuments,
  onVerifyDocument,
  onClose
}: VerificationCenterProps) {
  const tierInfo = TIER_INFO[currentTier];
  const nextTier = getNextTier(currentTier);
  const nextTierInfo = nextTier ? TIER_INFO[nextTier] : null;
  const scoreNeeded = nextTierInfo ? nextTierInfo.minScore - trustScore : 0;

  return (
    <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
      <LinearGradient
        colors={['#2E7D7A', '#4FD1C7', '#7EDDD9']}
        style={styles.backgroundGradient}
      />

      {/* Header */}
      {onClose && (
        <TouchableOpacity style={styles.closeButton} onPress={onClose}>
          <Ionicons name="close" size={24} color="#FFFFFF" />
        </TouchableOpacity>
      )}

      <View style={styles.header}>
        <Text style={styles.title}>신뢰도 인증 센터</Text>
        <Text style={styles.subtitle}>문서 인증으로 신뢰도를 높이세요</Text>
      </View>

      {/* Current Tier Card */}
      <View style={styles.currentTierCard}>
        <View style={styles.tierHeader}>
          <Text style={styles.tierEmoji}>{tierInfo.emoji}</Text>
          <View style={styles.tierInfo}>
            <Text style={styles.tierName}>{tierInfo.name}</Text>
            <Text style={styles.trustScoreText}>{trustScore}% 신뢰도</Text>
          </View>
        </View>

        <View style={styles.progressBarContainer}>
          <View style={styles.progressBarTrack}>
            <View
              style={[
                styles.progressBarFill,
                { width: `${trustScore}%`, backgroundColor: tierInfo.color }
              ]}
            />
          </View>
          <View style={styles.progressLabels}>
            <Text style={styles.progressLabel}>{tierInfo.minScore}%</Text>
            {nextTierInfo && (
              <Text style={styles.progressLabel}>{nextTierInfo.minScore}%</Text>
            )}
          </View>
        </View>

        <View style={styles.benefitsContainer}>
          <Text style={styles.benefitsTitle}>현재 혜택</Text>
          <View style={styles.benefitsList}>
            <View style={styles.benefitItem}>
              <Ionicons name="checkmark-circle" size={16} color="#4FD1C7" />
              <Text style={styles.benefitText}>하루 {tierInfo.dailyMatches} 매칭</Text>
            </View>
            {tierInfo.benefits.slice(0, 3).map((benefit, index) => (
              <View key={index} style={styles.benefitItem}>
                <Ionicons name="checkmark-circle" size={16} color="#4FD1C7" />
                <Text style={styles.benefitText}>{benefit}</Text>
              </View>
            ))}
          </View>
        </View>
      </View>

      {/* Upgrade Suggestion */}
      {nextTierInfo && (
        <View style={styles.upgradeCard}>
          <View style={styles.upgradeHeader}>
            <Text style={styles.upgradeEmoji}>{nextTierInfo.emoji}</Text>
            <Text style={styles.upgradeTitle}>
              {nextTierInfo.name}까지 {scoreNeeded}% 남았어요!
            </Text>
          </View>
          <Text style={styles.upgradeSubtitle}>
            문서 인증을 완료하면 더 많은 검증된 회원과 매칭됩니다
          </Text>
        </View>
      )}

      {/* Document Verification Options */}
      <View style={styles.documentsSection}>
        <Text style={styles.sectionTitle}>문서 인증</Text>
        {DOCUMENT_TYPES.map((doc) => {
          const isVerified = verifiedDocuments.includes(doc.id);
          return (
            <TouchableOpacity
              key={doc.id}
              style={[
                styles.documentCard,
                isVerified && styles.documentCardVerified
              ]}
              onPress={() => {
                console.log('🔘 Document card pressed:', doc.id, 'isVerified:', isVerified);
                if (!isVerified) {
                  console.log('✅ Calling onVerifyDocument for:', doc.id);
                  onVerifyDocument(doc.id);
                }
              }}
              disabled={isVerified}
            >
              <View style={styles.documentIcon}>
                <Ionicons
                  name={doc.icon}
                  size={24}
                  color={isVerified ? '#4FD1C7' : '#FFFFFF'}
                />
              </View>
              <View style={styles.documentInfo}>
                <Text style={styles.documentName}>{doc.name}</Text>
                <Text style={styles.documentDescription}>{doc.description}</Text>
              </View>
              <View style={styles.documentAction}>
                {isVerified ? (
                  <View style={styles.verifiedBadge}>
                    <Ionicons name="checkmark-circle" size={20} color="#4FD1C7" />
                    <Text style={styles.verifiedText}>인증완료</Text>
                  </View>
                ) : (
                  <Ionicons name="arrow-forward" size={20} color="#FFFFFF" />
                )}
              </View>
            </TouchableOpacity>
          );
        })}
      </View>

      {/* Trust Score Explanation */}
      <View style={styles.explanationCard}>
        <Text style={styles.explanationTitle}>💡 신뢰도 점수란?</Text>
        <Text style={styles.explanationText}>
          FLIO는 결혼정보회사 스타일의 신뢰도 시스템을 운영합니다. 문서 인증을 통해 신뢰도를 높이면 더 많은 검증된 회원들과 매칭되고, 매일 확인할 수 있는 매칭 수도 늘어납니다.
        </Text>
      </View>
    </ScrollView>
  );
}

function getNextTier(currentTier: TrustTier): TrustTier | null {
  const tiers: TrustTier[] = ['pebble', 'shell', 'pearl', 'coral'];
  const currentIndex = tiers.indexOf(currentTier);
  return currentIndex < tiers.length - 1 ? tiers[currentIndex + 1] : null;
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#2E7D7A',
  },
  backgroundGradient: {
    ...StyleSheet.absoluteFillObject,
  },
  closeButton: {
    position: 'absolute',
    top: 60,
    right: 20,
    zIndex: 10,
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(255,255,255,0.2)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  header: {
    paddingTop: 60,
    paddingHorizontal: 24,
    paddingBottom: 20,
    alignItems: 'center',
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    color: '#FFFFFF',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.8)',
  },
  currentTierCard: {
    marginHorizontal: 20,
    marginBottom: 16,
    backgroundColor: 'rgba(255,255,255,0.15)',
    borderRadius: 16,
    padding: 20,
  },
  tierHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 20,
  },
  tierEmoji: {
    fontSize: 48,
    marginRight: 16,
  },
  tierInfo: {
    flex: 1,
  },
  tierName: {
    fontSize: 20,
    fontWeight: '700',
    color: '#FFFFFF',
    marginBottom: 4,
  },
  trustScoreText: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.8)',
  },
  progressBarContainer: {
    marginBottom: 20,
  },
  progressBarTrack: {
    height: 8,
    backgroundColor: 'rgba(255,255,255,0.2)',
    borderRadius: 4,
    overflow: 'hidden',
  },
  progressBarFill: {
    height: '100%',
    borderRadius: 4,
  },
  progressLabels: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 4,
  },
  progressLabel: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.6)',
  },
  benefitsContainer: {
    marginTop: 8,
  },
  benefitsTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#FFFFFF',
    marginBottom: 12,
  },
  benefitsList: {
    gap: 8,
  },
  benefitItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  benefitText: {
    fontSize: 13,
    color: 'rgba(255,255,255,0.9)',
  },
  upgradeCard: {
    marginHorizontal: 20,
    marginBottom: 16,
    backgroundColor: 'rgba(79,209,199,0.2)',
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: 'rgba(79,209,199,0.4)',
  },
  upgradeHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  upgradeEmoji: {
    fontSize: 24,
    marginRight: 8,
  },
  upgradeTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  upgradeSubtitle: {
    fontSize: 13,
    color: 'rgba(255,255,255,0.8)',
    lineHeight: 18,
  },
  documentsSection: {
    marginHorizontal: 20,
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#FFFFFF',
    marginBottom: 16,
  },
  documentCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  documentCardVerified: {
    backgroundColor: 'rgba(79,209,199,0.15)',
    borderWidth: 1,
    borderColor: 'rgba(79,209,199,0.3)',
  },
  documentIcon: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: 'rgba(255,255,255,0.15)',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 16,
  },
  documentInfo: {
    flex: 1,
  },
  documentName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFFFFF',
    marginBottom: 4,
  },
  documentDescription: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.7)',
  },
  documentAction: {
    marginLeft: 12,
  },
  verifiedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  verifiedText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#4FD1C7',
  },
  boostBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(79,209,199,0.3)',
    borderRadius: 16,
    paddingHorizontal: 12,
    paddingVertical: 6,
    gap: 4,
  },
  boostText: {
    fontSize: 14,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  explanationCard: {
    marginHorizontal: 20,
    marginBottom: 40,
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 12,
    padding: 16,
  },
  explanationTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#FFFFFF',
    marginBottom: 8,
  },
  explanationText: {
    fontSize: 13,
    color: 'rgba(255,255,255,0.8)',
    lineHeight: 20,
  },
});
