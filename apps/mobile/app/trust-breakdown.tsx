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

/**
 * Trust Score Breakdown Screen
 * Shows detailed breakdown of trust score components
 */
export default function TrustBreakdownScreen() {
  const [trustScore, setTrustScore] = useState(0);
  const [componentScores, setComponentScores] = useState({
    document_score: 0,
    consistency_score: 0,
    behavioral_score: 0,
    completeness_score: 0,
  });

  useEffect(() => {
    const fetchTrustScore = async () => {
      try {
        const userId = await getCurrentUserId();
        if (!userId) return;

        const { data: trustData } = await supabase
          .from('user_trust_scores')
          .select('*')
          .eq('user_id', userId)
          .single();

        if (trustData) {
          setTrustScore(Math.round(trustData.total_trust_score * 100));
          setComponentScores({
            document_score: trustData.document_score,
            consistency_score: trustData.consistency_score,
            behavioral_score: trustData.behavioral_score,
            completeness_score: trustData.completeness_score,
          });
        }
      } catch (error) {
        console.error('❌ Failed to fetch trust score:', error);
      }
    };

    fetchTrustScore();
  }, []);

  const goBack = () => {
    router.back();
  };

  const components = [
    {
      icon: 'document-text',
      title: '문서 인증',
      weight: 35,
      score: componentScores.document_score,
      description: '신분증, 학력, 소득, 재직 증명서 인증',
      actionable: true,
      action: () => router.push('/document-verification'),
      actionText: '문서 인증하기',
    },
    {
      icon: 'list',
      title: '프로필 완성도',
      weight: 20,
      score: componentScores.completeness_score,
      description: '질문 답변, 프로필 정보, 가족 배경 입력',
      actionable: true,
      action: () => router.push('/(tabs)/profile'),
      actionText: '프로필 보기',
    },
    {
      icon: 'checkmark-done',
      title: '일관성 검증',
      weight: 25,
      score: componentScores.consistency_score,
      description: '답변 간 논리적 일관성 자동 검증',
      actionable: false,
    },
    {
      icon: 'trending-up',
      title: '활동 안정성',
      weight: 20,
      score: componentScores.behavioral_score,
      description: '계정 활동 기록 및 안정성 평가',
      actionable: false,
    },
  ];

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
        <Text style={styles.headerTitle}>신뢰도 구성</Text>
        <View style={styles.headerSpacer} />
      </View>

      <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
        {/* Total Score Card */}
        <View style={styles.totalScoreCard}>
          <Text style={styles.totalScoreLabel}>총 신뢰도</Text>
          <Text style={styles.totalScoreValue}>{trustScore}%</Text>
          <View style={styles.progressBar}>
            <View
              style={[
                styles.progressBarFill,
                { width: `${trustScore}%` }
              ]}
            />
          </View>
          <Text style={styles.totalScoreDescription}>
            4가지 요소로 계산된 종합 신뢰도 점수입니다
          </Text>
        </View>

        {/* Component Breakdown */}
        <View style={styles.componentsSection}>
          <Text style={styles.sectionTitle}>구성 요소</Text>

          {components.map((component, index) => {
            const percentageScore = Math.round(component.score * 100);
            const contributionScore = Math.round(component.score * component.weight);

            return (
              <View
                key={index}
                style={[
                  styles.componentCard,
                  !component.actionable && styles.componentCardAuto,
                ]}
              >
                <View style={styles.componentHeader}>
                  <View style={styles.componentTitleRow}>
                    <View
                      style={[
                        styles.componentIcon,
                        !component.actionable && styles.componentIconAuto,
                      ]}
                    >
                      <Ionicons
                        name={component.icon as any}
                        size={24}
                        color={component.actionable ? '#4FD1C7' : 'rgba(255,255,255,0.7)'}
                      />
                    </View>
                    <View style={styles.componentInfo}>
                      <Text
                        style={[
                          styles.componentTitle,
                          !component.actionable && styles.componentTitleAuto,
                        ]}
                      >
                        {component.title}
                      </Text>
                      <Text style={styles.componentDescription}>
                        {component.description}
                      </Text>
                    </View>
                  </View>
                  {!component.actionable && (
                    <View style={styles.autoTag}>
                      <Text style={styles.autoTagText}>자동</Text>
                    </View>
                  )}
                </View>

                <View style={styles.componentScores}>
                  <View style={styles.scoreItem}>
                    <Text style={styles.scoreLabel}>가중치</Text>
                    <Text style={styles.scoreValue}>{component.weight}%</Text>
                  </View>
                  <View style={styles.scoreDivider} />
                  <View style={styles.scoreItem}>
                    <Text style={styles.scoreLabel}>현재 점수</Text>
                    <Text style={styles.scoreValue}>{percentageScore}%</Text>
                  </View>
                  <View style={styles.scoreDivider} />
                  <View style={styles.scoreItem}>
                    <Text style={styles.scoreLabel}>기여도</Text>
                    <Text style={[styles.scoreValue, styles.contributionValue]}>
                      +{contributionScore}%
                    </Text>
                  </View>
                </View>

                {component.actionable && component.action && (
                  <TouchableOpacity
                    style={styles.actionButton}
                    onPress={component.action}
                    activeOpacity={0.7}
                  >
                    <Text style={styles.actionButtonText}>{component.actionText}</Text>
                    <Ionicons name="arrow-forward" size={16} color="#FFFFFF" />
                  </TouchableOpacity>
                )}
              </View>
            );
          })}
        </View>

        {/* Info Card */}
        <View style={styles.infoCard}>
          <View style={styles.infoHeader}>
            <Ionicons name="information-circle" size={24} color="#4FD1C7" />
            <Text style={styles.infoTitle}>신뢰도 계산 방식</Text>
          </View>
          <Text style={styles.infoText}>
            총 신뢰도 = (문서 인증 × 35%) + (프로필 완성도 × 20%) + (일관성 검증 × 25%) + (활동 안정성 × 20%)
          </Text>
          <View style={styles.infoTip}>
            <Ionicons name="bulb" size={16} color="#00FFC8" />
            <Text style={styles.infoTipText}>
              문서 인증은 가중치가 가장 높아 신뢰도를 빠르게 높일 수 있습니다
            </Text>
          </View>
          <View style={styles.tierNote}>
            <Text style={styles.tierNoteText}>
              💡 신뢰도는 등급 구매 자격을 결정합니다
            </Text>
          </View>
        </View>
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
    paddingHorizontal: 20,
  },
  totalScoreCard: {
    backgroundColor: 'rgba(79,209,199,0.25)',
    borderRadius: 20,
    padding: 24,
    marginBottom: 24,
    alignItems: 'center',
    borderWidth: 1.5,
    borderColor: 'rgba(79,209,199,0.5)',
  },
  totalScoreLabel: {
    fontSize: 16,
    color: 'rgba(255,255,255,0.95)',
    marginBottom: 8,
    fontWeight: '600',
  },
  totalScoreValue: {
    fontSize: 48,
    fontWeight: '700',
    color: '#FFFFFF',
    marginBottom: 16,
  },
  progressBar: {
    width: '100%',
    height: 8,
    backgroundColor: 'rgba(0,0,0,0.3)',
    borderRadius: 4,
    overflow: 'hidden',
    marginBottom: 16,
  },
  progressBarFill: {
    height: '100%',
    backgroundColor: '#00FFC8',
    borderRadius: 4,
  },
  totalScoreDescription: {
    fontSize: 13,
    color: 'rgba(255,255,255,0.9)',
    textAlign: 'center',
  },
  componentsSection: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 19,
    fontWeight: '700',
    color: '#FFFFFF',
    marginBottom: 16,
  },
  componentCard: {
    backgroundColor: 'rgba(255,255,255,0.15)',
    borderRadius: 16,
    padding: 20,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: 'rgba(79,209,199,0.4)',
  },
  componentCardAuto: {
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderColor: 'rgba(255,255,255,0.2)',
  },
  componentHeader: {
    marginBottom: 16,
  },
  componentTitleRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
    marginBottom: 8,
  },
  componentIcon: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: 'rgba(79,209,199,0.3)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  componentIconAuto: {
    backgroundColor: 'rgba(255,255,255,0.15)',
  },
  componentInfo: {
    flex: 1,
  },
  componentTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#FFFFFF',
    marginBottom: 4,
  },
  componentTitleAuto: {
    color: 'rgba(255,255,255,0.85)',
  },
  componentDescription: {
    fontSize: 13,
    color: 'rgba(255,255,255,0.85)',
    lineHeight: 18,
  },
  autoTag: {
    position: 'absolute',
    top: 0,
    right: 0,
    backgroundColor: 'rgba(0,0,0,0.3)',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  autoTagText: {
    fontSize: 11,
    fontWeight: '600',
    color: 'rgba(255,255,255,0.7)',
  },
  componentScores: {
    flexDirection: 'row',
    backgroundColor: 'rgba(0,0,0,0.2)',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  scoreItem: {
    flex: 1,
    alignItems: 'center',
  },
  scoreDivider: {
    width: 1,
    backgroundColor: 'rgba(255,255,255,0.2)',
    marginHorizontal: 8,
  },
  scoreLabel: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.9)',
    marginBottom: 6,
    fontWeight: '600',
  },
  scoreValue: {
    fontSize: 20,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  contributionValue: {
    color: '#00FFC8',
  },
  actionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(79,209,199,0.3)',
    borderRadius: 12,
    paddingVertical: 12,
    gap: 8,
    borderWidth: 1.5,
    borderColor: 'rgba(79,209,199,0.6)',
  },
  actionButtonText: {
    fontSize: 15,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  infoCard: {
    backgroundColor: 'rgba(0,255,200,0.15)',
    borderRadius: 16,
    padding: 20,
    marginBottom: 40,
    borderWidth: 1.5,
    borderColor: 'rgba(0,255,200,0.3)',
  },
  infoHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginBottom: 12,
  },
  infoTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  infoText: {
    fontSize: 13,
    color: 'rgba(255,255,255,0.95)',
    lineHeight: 20,
    marginBottom: 12,
    fontWeight: '500',
  },
  infoTip: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    backgroundColor: 'rgba(0,255,200,0.2)',
    padding: 12,
    borderRadius: 8,
  },
  infoTipText: {
    flex: 1,
    fontSize: 13,
    color: '#FFFFFF',
    lineHeight: 18,
    fontWeight: '500',
  },
  tierNote: {
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255,255,255,0.2)',
  },
  tierNoteText: {
    fontSize: 13,
    color: 'rgba(255,255,255,0.9)',
    textAlign: 'center',
    fontWeight: '500',
  },
});
