import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';

import { supabaseQuestionService, UserProfile } from '../../services/supabaseQuestionService';
import { getCurrentUserId } from '../../services/supabase/client';
import { FLIOAlertAPI } from '../../components/FLIOAlert';
import { aiQuestionService } from '../../services/aiQuestionService';
import TrustBadge, { getTierFromScore } from '../../components/TrustBadge';

/**
 * Profile Screen
 * Shows user's questionnaire answers and allows editing
 */
export default function ProfileScreen() {
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [currentUserId, setCurrentUserId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [trustScore, setTrustScore] = useState<any>(null);

  const loadProfileData = async (isRefresh = false) => {
    try {
      if (isRefresh) setRefreshing(true);
      else setIsLoading(true);

      const userId = currentUserId || await getCurrentUserId();
      if (!userId) {
        console.error('❌ No user ID available in profile screen');
        FLIOAlertAPI.alert('오류', '사용자 정보를 불러올 수 없습니다.');
        return;
      }

      console.log('🔄 Loading user profile data...');

      // Load user's complete profile from Supabase
      const profileData = await supabaseQuestionService.getUserProfile(userId);

      if (profileData) {
        setUserProfile(profileData);
        console.log('✅ Profile data loaded successfully');
        console.log(`📊 Profile: ${profileData.total_answers} answers, ${Math.min(100, profileData.profile_completion.completion_percentage).toFixed(0)}% complete`);
      } else {
        // If no profile found, create empty profile
        setUserProfile({
          user_id: userId,
          answers: [],
          total_answers: 0,
          embedding_status: {
            has_embedding: false,
            message: 'AI 프로필 분석 대기 중'
          },
          profile_completion: {
            total_questions: 40,
            answered_questions: 0,
            completion_percentage: 0,
            can_start_matching: false
          }
        });
      }

      // Load trust score - will throw on error (no fallback)
      const trustScoreData = await aiQuestionService.getTrustScore(userId);
      if (trustScoreData) {
        setTrustScore(trustScoreData);
        console.log(`🔐 Trust score loaded: ${trustScoreData.trust_tier} (${(trustScoreData.total_trust_score * 100).toFixed(1)}%)`);
      }

    } catch (error) {
      console.error('❌ Failed to load profile:', error);
      FLIOAlertAPI.alert('오류', '프로필 데이터를 불러올 수 없습니다.');
    } finally {
      setIsLoading(false);
      setRefreshing(false);
    }
  };

  const handleEditAnswer = (questionId: string) => {
    FLIOAlertAPI.alert(
      '답변 수정/삭제',
      '이 답변을 어떻게 하시겠습니까?',
      [
        { text: '취소', style: 'cancel' },
        { text: '삭제', style: 'destructive', onPress: () => handleDeleteAnswer(questionId) },
        { text: '수정하기', onPress: () => {
          router.push({
            pathname: '/(onboarding)/questions',
            params: { 
              editMode: 'true',
              questionId: questionId,
              userId: currentUserId || 'unknown'
            }
          });
        }}
      ]
    );
  };

  const handleDeleteAnswer = async (questionId: string) => {
    try {
      setIsLoading(true);
      
      const userId = currentUserId || await getCurrentUserId();
      if (!userId) return;
      
      const result = await supabaseQuestionService.deleteAnswer(userId, questionId);
      
      if (result.success) {
        FLIOAlertAPI.alert(
          '답변 삭제 완료',
          result.message,
          [
            { text: '프로필 새로고침', onPress: () => loadProfileData() },
            { text: '확인' }
          ]
        );
      } else {
        FLIOAlertAPI.alert('오류', result.message);
      }
    } catch (error) {
      console.error('❌ Failed to delete answer:', error);
      FLIOAlertAPI.alert('오류', '답변 삭제 중 문제가 발생했습니다.');
    } finally {
      setIsLoading(false);
    }
  };



  // Get authenticated user ID on mount
  useEffect(() => {
    const fetchUserId = async () => {
      const userId = await getCurrentUserId();
      if (userId) {
        setCurrentUserId(userId);
        loadProfileData();
      } else {
        setIsLoading(false);
        router.replace('/(auth)/login');
      }
    };
    fetchUserId();
  }, []);

  if (!userProfile) {
    return (
      <View style={styles.loadingContainer}>
        <LinearGradient
          colors={['#2E7D7A', '#4FD1C7', '#7EDDD9']}
          style={styles.backgroundGradient}
        />
        <ActivityIndicator size="large" color="#FFFFFF" />
        <Text style={styles.loadingText}>프로필을 불러오는 중...</Text>
      </View>
    );
  }

  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <LinearGradient
          colors={['#2E7D7A', '#4FD1C7', '#7EDDD9']}
          style={styles.backgroundGradient}
        />
        <ActivityIndicator size="large" color="#FFFFFF" />
        <Text style={styles.loadingText}>프로필을 불러오는 중...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <StatusBar style="light" />
      
      <LinearGradient
        colors={['#2E7D7A', '#4FD1C7', '#7EDDD9']}
        style={styles.backgroundGradient}
      />

      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerTextContainer}>
          <Text style={styles.headerTitle}>내 프로필</Text>
          <Text style={styles.headerSubtitle}>질문 답변 현황</Text>
        </View>
        <TouchableOpacity
          style={styles.accountButton}
          onPress={() => router.push('/account')}
          activeOpacity={0.7}
        >
          <Ionicons name="person-circle-outline" size={26} color="#FFFFFF" />
        </TouchableOpacity>
      </View>

      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={true}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => loadProfileData(true)}
            tintColor="#FFFFFF"
          />
        }
      >
        {/* Profile Completion Status */}
        <View style={styles.statusCard}>
          <View style={styles.statusHeader}>
            <View style={styles.statusIconContainer}>
              <Ionicons
                name="person-circle"
                size={24}
                color="#4FD1C7"
              />
            </View>
            <View style={styles.statusInfo}>
              <Text style={styles.statusTitle}>프로필 완성도</Text>
              <Text style={styles.statusSubtitle}>
                {userProfile.total_answers}개 질문 답변 완료 ({Math.min(100, userProfile.profile_completion.completion_percentage).toFixed(0)}%)
              </Text>
            </View>
          </View>
        </View>

        {/* Trust Score Card */}
        {trustScore && (
          <View style={styles.trustScoreCard}>
            <View style={styles.trustScoreHeader}>
              <View style={styles.trustScoreIconContainer}>
                <Ionicons
                  name="shield-checkmark"
                  size={24}
                  color="#4FD1C7"
                />
              </View>
              <View style={styles.trustScoreInfo}>
                <Text style={styles.trustScoreTitle}>신뢰도 점수</Text>
                <Text style={styles.trustScorePercentage}>
                  {(trustScore.total_trust_score * 100).toFixed(0)}%
                </Text>
              </View>
              <TrustBadge tier={trustScore.trust_tier} size="medium" />
            </View>

            {/* Score Breakdown */}
            <View style={styles.scoreBreakdown}>
              <Text style={styles.breakdownTitle}>점수 구성</Text>

              <View style={styles.scoreItem}>
                <View style={styles.scoreItemLeft}>
                  <Ionicons name="document-text" size={16} color="#4FD1C7" />
                  <Text style={styles.scoreItemLabel}>문서 인증</Text>
                </View>
                <Text style={styles.scoreItemValue}>
                  {(trustScore.document_score * 100).toFixed(0)}%
                </Text>
              </View>

              <View style={styles.scoreItem}>
                <View style={styles.scoreItemLeft}>
                  <Ionicons name="checkmark-done" size={16} color="#4FD1C7" />
                  <Text style={styles.scoreItemLabel}>일관성</Text>
                </View>
                <Text style={styles.scoreItemValue}>
                  {(trustScore.consistency_score * 100).toFixed(0)}%
                </Text>
              </View>

              <View style={styles.scoreItem}>
                <View style={styles.scoreItemLeft}>
                  <Ionicons name="trending-up" size={16} color="#4FD1C7" />
                  <Text style={styles.scoreItemLabel}>행동 패턴</Text>
                </View>
                <Text style={styles.scoreItemValue}>
                  {(trustScore.behavioral_score * 100).toFixed(0)}%
                </Text>
              </View>

              <View style={styles.scoreItem}>
                <View style={styles.scoreItemLeft}>
                  <Ionicons name="list" size={16} color="#4FD1C7" />
                  <Text style={styles.scoreItemLabel}>완성도</Text>
                </View>
                <Text style={styles.scoreItemValue}>
                  {(trustScore.completeness_score * 100).toFixed(0)}%
                </Text>
              </View>
            </View>

            {/* Improve Trust Button */}
            <TouchableOpacity
              style={styles.improveTrustButton}
              onPress={() => router.push('/(onboarding)/document-upload')}
            >
              <Ionicons name="arrow-up-circle" size={20} color="#FFFFFF" />
              <Text style={styles.improveTrustButtonText}>신뢰도 높이기</Text>
            </TouchableOpacity>

            <Text style={styles.trustScoreNote}>
              문서 인증을 완료하여 더 많은 매칭 기회를 얻으세요
            </Text>
          </View>
        )}

        {/* Answers Section */}
        <View style={styles.answersSection}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>내 답변 ({userProfile.total_answers})</Text>
            {userProfile.profile_completion.completion_percentage < 100 && (
              <TouchableOpacity
                style={styles.addAnswerButton}
                onPress={() => router.push('/(onboarding)/questions')}
              >
                <Ionicons name="add" size={16} color="#4FD1C7" />
                <Text style={styles.addAnswerText}>질문 답변하기</Text>
              </TouchableOpacity>
            )}
          </View>

          {userProfile.answers.length === 0 ? (
            <View style={styles.emptyAnswers}>
              <Ionicons name="help-circle-outline" size={48} color="rgba(255,255,255,0.5)" />
              <Text style={styles.emptyAnswersTitle}>아직 답변한 질문이 없어요</Text>
              <Text style={styles.emptyAnswersSubtitle}>질문에 답변하여 AI 매칭을 시작하세요!</Text>
            </View>
          ) : (
            userProfile.answers.map((answer, index) => (
              <TouchableOpacity
                key={answer.question_id}
                style={styles.answerCard}
                onPress={() => handleEditAnswer(answer.question_id)}
                activeOpacity={0.7}
              >
                <View style={styles.answerHeader}>
                  <View style={styles.questionNumberBadge}>
                    <Text style={styles.questionNumberText}>Q{index + 1}</Text>
                  </View>
                  <Text style={styles.questionText}>{answer.question_text || '질문'}</Text>
                </View>
                
                <Text style={styles.answerText}>
                  {answer.answer_value}
                </Text>

                <View style={styles.answerFooter}>
                  <Text style={styles.categoryText}>{answer.category || '기타'}</Text>
                  <TouchableOpacity style={styles.editButton}>
                    <Ionicons name="pencil" size={14} color="#4FD1C7" />
                    <Text style={styles.editButtonText}>수정</Text>
                  </TouchableOpacity>
                </View>
              </TouchableOpacity>
            ))
          )}
        </View>

      </ScrollView>
    </View>
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
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#2E7D7A',
  },
  loadingText: {
    marginTop: 12,
    fontSize: 16,
    color: '#FFFFFF',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingTop: 60,
    paddingHorizontal: 24,
    paddingBottom: 20,
  },
  headerTextContainer: {
    flex: 1,
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: '700',
    color: '#FFFFFF',
    marginBottom: 4,
  },
  headerSubtitle: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.8)',
  },
  accountButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(255,255,255,0.15)',
    alignItems: 'center',
    justifyContent: 'center',
    marginLeft: 12,
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    paddingBottom: 120,
  },
  statusCard: {
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 16,
    padding: 16,
    marginHorizontal: 20,
    marginBottom: 24,
  },
  statusHeader: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  statusIconContainer: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(255,255,255,0.1)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  statusInfo: {
    flex: 1,
    marginLeft: 12,
  },
  statusTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFFFFF',
    marginBottom: 2,
  },
  statusSubtitle: {
    fontSize: 13,
    color: 'rgba(255,255,255,0.7)',
  },
  trustScoreCard: {
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 16,
    padding: 20,
    marginHorizontal: 20,
    marginBottom: 24,
    borderWidth: 1,
    borderColor: 'rgba(79,209,199,0.3)',
  },
  trustScoreHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 20,
  },
  trustScoreIconContainer: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(79,209,199,0.2)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  trustScoreInfo: {
    flex: 1,
    marginLeft: 12,
  },
  trustScoreTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: 'rgba(255,255,255,0.8)',
    marginBottom: 4,
  },
  trustScorePercentage: {
    fontSize: 24,
    fontWeight: '700',
    color: '#4FD1C7',
  },
  scoreBreakdown: {
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
  },
  breakdownTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#FFFFFF',
    marginBottom: 12,
  },
  scoreItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
  },
  scoreItemLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  scoreItemLabel: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.8)',
  },
  scoreItemValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#4FD1C7',
  },
  improveTrustButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#4FD1C7',
    borderRadius: 12,
    paddingVertical: 14,
    gap: 8,
    marginBottom: 12,
  },
  improveTrustButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  trustScoreNote: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.6)',
    textAlign: 'center',
    fontStyle: 'italic',
  },
  answersSection: {
    paddingHorizontal: 20,
    paddingBottom: 80,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  addAnswerButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 16,
    paddingHorizontal: 12,
    paddingVertical: 6,
    gap: 4,
  },
  addAnswerText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#4FD1C7',
  },
  answerCard: {
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
  },
  answerHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
    gap: 8,
  },
  questionNumberBadge: {
    backgroundColor: '#4FD1C7',
    borderRadius: 12,
    paddingHorizontal: 8,
    paddingVertical: 4,
    minWidth: 36,
    alignItems: 'center',
    justifyContent: 'center',
  },
  questionNumberText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#1A5F5A',
  },
  questionText: {
    flex: 1,
    fontSize: 15,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  answerMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  dealbreakerBadge: {
    backgroundColor: '#FF6B6B',
    borderRadius: 8,
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  dealbreakerText: {
    fontSize: 10,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  importanceText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#4FD1C7',
  },
  answerText: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.9)',
    lineHeight: 20,
    marginBottom: 12,
  },
  answerFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  categoryText: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.6)',
    fontStyle: 'italic',
  },
  editButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  editButtonText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#4FD1C7',
  },
  emptyAnswers: {
    alignItems: 'center',
    paddingVertical: 40,
  },
  emptyAnswersTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFFFFF',
    marginTop: 12,
    marginBottom: 6,
  },
  emptyAnswersSubtitle: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.7)',
    textAlign: 'center',
  },
});