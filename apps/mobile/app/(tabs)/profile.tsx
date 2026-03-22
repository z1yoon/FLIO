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
import { supabase } from '../../services/supabase/client';
import { FLIOAlertAPI } from '../../components/FLIOAlert';
import { aiQuestionService } from '../../services/aiQuestionService';
import TrustBadge from '../../components/TrustBadge';

// ─── Field → document label mapping ───────────────────────────────────
const FIELD_TO_DOC: Record<string, { doc: string; label: string }> = {
  real_name:           { doc: 'id_card',          label: '신분증' },
  age:                 { doc: 'id_card',          label: '신분증' },
  height_cm:           { doc: 'health_checkup',   label: '건강검진서' },
  weight_kg:           { doc: 'health_checkup',   label: '건강검진서' },
  university_name:     { doc: 'diploma',          label: '졸업증명서' },
  education_level:     { doc: 'diploma',          label: '졸업증명서' },
  company_name:        { doc: 'employment_cert',  label: '재직증명서' },
  job_title:           { doc: 'employment_cert',  label: '재직증명서' },
  annual_income_range: { doc: 'income_proof',     label: '소득증명서' },
};

const PERSONAL_FIELDS: { key: string; label: string; unit?: string }[] = [
  { key: 'real_name',           label: '이름' },
  { key: 'age',                 label: '나이',    unit: '세' },
  { key: 'height_cm',           label: '키',      unit: 'cm' },
  { key: 'weight_kg',           label: '몸무게',  unit: 'kg' },
  { key: 'education_level',     label: '학력' },
  { key: 'university_name',     label: '학교' },
  { key: 'company_name',        label: '회사' },
  { key: 'job_title',           label: '직책' },
  { key: 'annual_income_range', label: '연봉' },
  { key: 'marital_status',      label: '혼인 상태' },
];

export default function ProfileScreen() {
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [personalInfo, setPersonalInfo] = useState<Record<string, any>>({});
  const [fieldVerifications, setFieldVerifications] = useState<Record<string, boolean>>({});
  const [trustData, setTrustData] = useState<any>(null);
  const [currentUserId, setCurrentUserId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadAll = async (isRefresh = false) => {
    try {
      if (isRefresh) setRefreshing(true);
      else setIsLoading(true);

      const userId = currentUserId || await getCurrentUserId();
      if (!userId) {
        router.replace('/(auth)/login');
        return;
      }

      const [profileData, personalResult, trustResult] = await Promise.all([
        supabaseQuestionService.getUserProfile(userId),
        supabase.from('profiles').select(
          'real_name, age, height_cm, weight_kg, education_level, university_name, ' +
          'major, employment_status, company_name, job_title, annual_income_range, marital_status'
        ).eq('user_id', userId).single(),
        aiQuestionService.getTrustScore(userId).catch(() => null),
      ]);

      if (profileData) {
        setUserProfile(profileData);
      } else {
        setUserProfile({
          user_id: userId,
          answers: [],
          total_answers: 0,
          embedding_status: { has_embedding: false, message: 'AI 프로필 분석 대기 중' },
          profile_completion: { total_questions: 60, answered_questions: 0, completion_percentage: 0, can_start_matching: false },
        });
      }

      if (personalResult.data) setPersonalInfo(personalResult.data);

      if (trustResult) {
        setTrustData(trustResult);
        if (trustResult.field_verifications) {
          setFieldVerifications(trustResult.field_verifications);
        }
      }
    } catch (error) {
      console.error('Failed to load profile:', error);
      FLIOAlertAPI.alert('오류', '프로필 데이터를 불러올 수 없습니다.');
    } finally {
      setIsLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    const init = async () => {
      const userId = await getCurrentUserId();
      if (userId) {
        setCurrentUserId(userId);
        loadAll();
      } else {
        setIsLoading(false);
        router.replace('/(auth)/login');
      }
    };
    init();
  }, []);

  const handleEditAnswer = (questionId: string) => {
    FLIOAlertAPI.alert('답변 수정/삭제', '이 답변을 어떻게 하시겠습니까?', [
      { text: '취소', style: 'cancel' },
      { text: '삭제', style: 'destructive', onPress: () => handleDeleteAnswer(questionId) },
      {
        text: '수정하기', onPress: () => router.push({
          pathname: '/(onboarding)/questions',
          params: { editMode: 'true', questionId, userId: currentUserId || 'unknown' },
        }),
      },
    ]);
  };

  const handleDeleteAnswer = async (questionId: string) => {
    try {
      setIsLoading(true);
      const userId = currentUserId || await getCurrentUserId();
      if (!userId) return;
      const result = await supabaseQuestionService.deleteAnswer(userId, questionId);
      if (result.success) {
        FLIOAlertAPI.alert('삭제 완료', result.message, [
          { text: '새로고침', onPress: () => loadAll() },
          { text: '확인' },
        ]);
      } else {
        FLIOAlertAPI.alert('오류', result.message);
      }
    } catch {
      FLIOAlertAPI.alert('오류', '답변 삭제 중 문제가 발생했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  const tierPoints = trustData ? Math.round((trustData.total_trust_score ?? 0) * 100) : 0;
  const nextTierPoints = tierPoints < 20 ? 20 : tierPoints < 40 ? 40 : tierPoints < 60 ? 60 : tierPoints < 80 ? 80 : 100;
  const pointsNeeded = nextTierPoints - tierPoints;

  if (isLoading && !userProfile) {
    return (
      <View style={styles.loadingContainer}>
        <LinearGradient colors={['#2E7D7A', '#4FD1C7', '#7EDDD9']} style={StyleSheet.absoluteFillObject} />
        <ActivityIndicator size="large" color="#FFFFFF" />
        <Text style={styles.loadingText}>프로필을 불러오는 중...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <StatusBar style="light" />
      <LinearGradient colors={['#2E7D7A', '#4FD1C7', '#7EDDD9']} style={StyleSheet.absoluteFillObject} />

      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerTextContainer}>
          <Text style={styles.headerTitle}>내 프로필</Text>
          <Text style={styles.headerSubtitle}>
            {userProfile ? `${userProfile.total_answers}개 답변 완료` : ''}
          </Text>
        </View>
        <TouchableOpacity style={styles.accountButton} onPress={() => router.push('/account')} activeOpacity={0.7}>
          <Ionicons name="person-circle-outline" size={26} color="#FFFFFF" />
        </TouchableOpacity>
      </View>

      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => loadAll(true)} tintColor="#FFFFFF" />}
      >
        {/* ── Trust Tier Card ── */}
        {trustData && (
          <View style={styles.tierCard}>
            <View style={styles.tierTop}>
              <TrustBadge tier={trustData.trust_tier ?? 'pebble'} size="large" />
              <View style={styles.tierInfo}>
                <Text style={styles.tierPoints}>{tierPoints}점</Text>
                <Text style={styles.tierSubtitle}>
                  {tierPoints < 100
                    ? `다음 등급까지 ${pointsNeeded}점`
                    : '최고 등급 달성!'}
                </Text>
              </View>
            </View>

            {/* Progress bar */}
            <View style={styles.progressBg}>
              <View style={[styles.progressFill, { width: `${tierPoints}%` }]} />
            </View>

            <TouchableOpacity style={styles.upgradeBtn} onPress={() => router.push('/document-verification')} activeOpacity={0.8}>
              <Ionicons name="arrow-up-circle" size={18} color="#FFFFFF" />
              <Text style={styles.upgradeBtnText}>서류 인증으로 등급 올리기</Text>
            </TouchableOpacity>
          </View>
        )}

        {/* ── Personal Info with Verification Badges ── */}
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>기본 정보</Text>

          {PERSONAL_FIELDS.map(({ key, label, unit }) => {
            const value = personalInfo[key];
            const isVerified = fieldVerifications[key] === true;
            const docInfo = FIELD_TO_DOC[key];

            return (
              <View key={key} style={styles.fieldRow}>
                <Text style={styles.fieldLabel}>{label}</Text>
                <View style={styles.fieldRight}>
                  {value != null ? (
                    <Text style={styles.fieldValue}>{String(value)}{unit ? ` ${unit}` : ''}</Text>
                  ) : (
                    <Text style={styles.fieldEmpty}>미입력</Text>
                  )}
                  {value != null && (
                    isVerified ? (
                      <View style={styles.verifiedBadge}>
                        <Ionicons name="checkmark-circle" size={12} color="#4FD1C7" />
                        <Text style={styles.verifiedText}>인증됨</Text>
                      </View>
                    ) : docInfo ? (
                      <TouchableOpacity
                        style={styles.unverifiedBadge}
                        onPress={() => router.push('/document-verification')}
                        activeOpacity={0.7}
                      >
                        <Ionicons name="shield-outline" size={12} color="rgba(255,255,255,0.5)" />
                        <Text style={styles.unverifiedText}>{docInfo.label}로 인증</Text>
                      </TouchableOpacity>
                    ) : null
                  )}
                </View>
              </View>
            );
          })}

          <TouchableOpacity
            style={styles.editProfileBtn}
            onPress={() => router.push('/(onboarding)/extended-profile')}
            activeOpacity={0.7}
          >
            <Ionicons name="pencil" size={15} color="#4FD1C7" />
            <Text style={styles.editProfileText}>정보 수정하기</Text>
          </TouchableOpacity>
        </View>

        {/* ── Q&A Answers ── */}
        <View style={styles.card}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>내 답변 ({userProfile?.total_answers ?? 0})</Text>
            {(userProfile?.profile_completion.completion_percentage ?? 0) < 100 && (
              <TouchableOpacity style={styles.addAnswerButton} onPress={() => router.push('/(onboarding)/questions')} activeOpacity={0.7}>
                <Ionicons name="add" size={16} color="#4FD1C7" />
                <Text style={styles.addAnswerText}>답변하기</Text>
              </TouchableOpacity>
            )}
          </View>

          {!userProfile || userProfile.answers.length === 0 ? (
            <View style={styles.emptyAnswers}>
              <Ionicons name="help-circle-outline" size={48} color="rgba(255,255,255,0.4)" />
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
                <Text style={styles.answerText}>{answer.answer_value}</Text>
                <View style={styles.answerFooter}>
                  <Text style={styles.categoryText}>{answer.category || '기타'}</Text>
                  <View style={styles.editButton}>
                    <Ionicons name="pencil" size={14} color="#4FD1C7" />
                    <Text style={styles.editButtonText}>수정</Text>
                  </View>
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
  container: { flex: 1, backgroundColor: '#2E7D7A' },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#2E7D7A' },
  loadingText: { marginTop: 12, fontSize: 16, color: '#FFFFFF' },
  header: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingTop: 60, paddingHorizontal: 24, paddingBottom: 20,
  },
  headerTextContainer: { flex: 1 },
  headerTitle: { fontSize: 24, fontWeight: '700', color: '#FFFFFF', marginBottom: 4 },
  headerSubtitle: { fontSize: 14, color: 'rgba(255,255,255,0.8)' },
  accountButton: {
    width: 40, height: 40, borderRadius: 20,
    backgroundColor: 'rgba(255,255,255,0.15)', alignItems: 'center', justifyContent: 'center',
  },
  scrollView: { flex: 1 },
  scrollContent: { paddingHorizontal: 20, paddingBottom: 120, gap: 16 },

  // Tier card
  tierCard: {
    backgroundColor: 'rgba(255,255,255,0.1)', borderRadius: 16, padding: 20,
    borderWidth: 1, borderColor: 'rgba(79,209,199,0.3)',
  },
  tierTop: { flexDirection: 'row', alignItems: 'center', marginBottom: 16, gap: 16 },
  tierInfo: { flex: 1 },
  tierPoints: { fontSize: 28, fontWeight: '800', color: '#4FD1C7' },
  tierSubtitle: { fontSize: 13, color: 'rgba(255,255,255,0.7)', marginTop: 2 },
  progressBg: { height: 6, backgroundColor: 'rgba(255,255,255,0.15)', borderRadius: 3, marginBottom: 16 },
  progressFill: { height: 6, backgroundColor: '#4FD1C7', borderRadius: 3 },
  upgradeBtn: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    backgroundColor: '#4FD1C7', borderRadius: 12, paddingVertical: 13, gap: 8,
  },
  upgradeBtnText: { fontSize: 15, fontWeight: '600', color: '#FFFFFF' },

  // Generic card
  card: {
    backgroundColor: 'rgba(255,255,255,0.08)', borderRadius: 16, padding: 20,
    borderWidth: 1, borderColor: 'rgba(255,255,255,0.1)',
  },
  sectionTitle: { fontSize: 16, fontWeight: '700', color: '#FFFFFF', marginBottom: 16 },
  sectionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },

  // Personal info fields
  fieldRow: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: 'rgba(255,255,255,0.06)',
  },
  fieldLabel: { fontSize: 14, color: 'rgba(255,255,255,0.6)', width: 90 },
  fieldRight: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'flex-end', gap: 8, flexWrap: 'wrap' },
  fieldValue: { fontSize: 14, fontWeight: '500', color: '#FFFFFF' },
  fieldEmpty: { fontSize: 13, color: 'rgba(255,255,255,0.3)', fontStyle: 'italic' },
  verifiedBadge: {
    flexDirection: 'row', alignItems: 'center', gap: 3,
    backgroundColor: 'rgba(79,209,199,0.15)', borderRadius: 8, paddingHorizontal: 6, paddingVertical: 2,
  },
  verifiedText: { fontSize: 10, fontWeight: '600', color: '#4FD1C7' },
  unverifiedBadge: {
    flexDirection: 'row', alignItems: 'center', gap: 3,
    backgroundColor: 'rgba(255,255,255,0.05)', borderRadius: 8, paddingHorizontal: 6, paddingVertical: 2,
  },
  unverifiedText: { fontSize: 10, color: 'rgba(255,255,255,0.45)' },
  editProfileBtn: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    marginTop: 16, gap: 6,
  },
  editProfileText: { fontSize: 14, fontWeight: '600', color: '#4FD1C7' },

  // Answers
  addAnswerButton: {
    flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 16, paddingHorizontal: 12, paddingVertical: 6, gap: 4,
  },
  addAnswerText: { fontSize: 12, fontWeight: '600', color: '#4FD1C7' },
  answerCard: { backgroundColor: 'rgba(255,255,255,0.06)', borderRadius: 12, padding: 14, marginBottom: 10 },
  answerHeader: { flexDirection: 'row', alignItems: 'flex-start', marginBottom: 10, gap: 8 },
  questionNumberBadge: {
    backgroundColor: '#4FD1C7', borderRadius: 10, paddingHorizontal: 8, paddingVertical: 3,
    minWidth: 34, alignItems: 'center',
  },
  questionNumberText: { fontSize: 11, fontWeight: '700', color: '#1A5F5A' },
  questionText: { flex: 1, fontSize: 14, fontWeight: '600', color: '#FFFFFF' },
  answerText: { fontSize: 13, color: 'rgba(255,255,255,0.85)', lineHeight: 20, marginBottom: 10 },
  answerFooter: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  categoryText: { fontSize: 12, color: 'rgba(255,255,255,0.5)', fontStyle: 'italic' },
  editButton: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  editButtonText: { fontSize: 12, fontWeight: '600', color: '#4FD1C7' },
  emptyAnswers: { alignItems: 'center', paddingVertical: 36 },
  emptyAnswersTitle: { fontSize: 16, fontWeight: '600', color: '#FFFFFF', marginTop: 12, marginBottom: 6 },
  emptyAnswersSubtitle: { fontSize: 14, color: 'rgba(255,255,255,0.6)', textAlign: 'center' },
});
