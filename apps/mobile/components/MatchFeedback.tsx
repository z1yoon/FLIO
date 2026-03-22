import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Modal,
  ScrollView,
  TextInput,
  ActivityIndicator,
  Platform,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { aiManagerService } from '../services/aiManagerService';

interface MatchFeedbackProps {
  visible: boolean;
  userId: string;
  matchUserId: string;
  matchName?: string;
  onClose: () => void;
  onSubmitted?: (needsDiagnosis: boolean) => void;
}

const TEAL = '#40e0d0';
const DARK_BG = '#0a0e1a';
const CARD_BG = '#111827';

const POSITIVE_TAGS = [
  '가치관 일치', '대화 편안함', '결혼 진지도 높음', '생활 패턴 유사',
  '가족관 비슷함', '갈등 해결 방식 맞음', '인생 목표 일치', '유머 감각',
];

const NEGATIVE_TAGS = [
  '가치관 차이', '종교 차이', '거리/지역', '나이 차이', '결혼 의지 불명확',
  '생활 패턴 달라', '재정관 차이', '가족 관계 다름',
];

const DIMENSIONS = [
  { key: 'values_alignment', label: '가치관 일치도', icon: 'heart-outline' },
  { key: 'lifestyle_match', label: '생활 패턴 일치', icon: 'calendar-outline' },
  { key: 'conversation_comfort', label: '대화 편안함', icon: 'chatbubble-outline' },
  { key: 'marriage_seriousness', label: '결혼 진지도', icon: 'diamond-outline' },
] as const;

function StarRating({ value, onChange, size = 28 }: { value: number; onChange: (v: number) => void; size?: number }) {
  return (
    <View style={{ flexDirection: 'row', gap: 4 }}>
      {[1, 2, 3, 4, 5].map(star => (
        <TouchableOpacity key={star} onPress={() => onChange(star)}>
          <Ionicons
            name={star <= value ? 'star' : 'star-outline'}
            size={size}
            color={star <= value ? '#fbbf24' : 'rgba(255,255,255,0.25)'}
          />
        </TouchableOpacity>
      ))}
    </View>
  );
}

export default function MatchFeedback({
  visible, userId, matchUserId, matchName, onClose, onSubmitted,
}: MatchFeedbackProps) {
  const [overallRating, setOverallRating] = useState(0);
  const [dimensionRatings, setDimensionRatings] = useState<Record<string, number>>({});
  const [selectedPositive, setSelectedPositive] = useState<string[]>([]);
  const [selectedNegative, setSelectedNegative] = useState<string[]>([]);
  const [freeText, setFreeText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [submitMessage, setSubmitMessage] = useState('');

  const toggleTag = (tag: string, list: string[], setList: (v: string[]) => void) => {
    setList(list.includes(tag) ? list.filter(t => t !== tag) : [...list, tag]);
  };

  const setDimension = (key: string, value: number) => {
    setDimensionRatings(prev => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async () => {
    if (overallRating === 0) return;
    setIsSubmitting(true);
    try {
      const result = await aiManagerService.submitMatchFeedback({
        user_id: userId,
        match_user_id: matchUserId,
        overall_rating: overallRating,
        dimension_ratings: dimensionRatings,
        positive_aspects: selectedPositive,
        dealbreaker_aspects: selectedNegative,
        free_text_feedback: freeText.trim() || undefined,
      });
      setSubmitted(true);
      setSubmitMessage(result.message);
      setTimeout(() => {
        onSubmitted?.(result.needs_diagnosis);
        handleClose();
      }, 1800);
    } catch (e) {
      setSubmitMessage('피드백 저장에 실패했습니다. 다시 시도해주세요.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setOverallRating(0);
    setDimensionRatings({});
    setSelectedPositive([]);
    setSelectedNegative([]);
    setFreeText('');
    setSubmitted(false);
    setSubmitMessage('');
    onClose();
  };

  return (
    <Modal visible={visible} animationType="slide" presentationStyle="pageSheet" onRequestClose={handleClose}>
      <View style={styles.container}>
        <LinearGradient colors={['#0f2027', '#1a2e2e']} style={styles.header}>
          <Text style={styles.headerTitle}>매칭 피드백</Text>
          <Text style={styles.headerSubtitle}>
            {matchName ? `${matchName}님` : '이 상대'}과의 매칭 경험을 알려주세요
          </Text>
          <TouchableOpacity onPress={handleClose} style={styles.closeBtn}>
            <Ionicons name="close" size={22} color="rgba(255,255,255,0.6)" />
          </TouchableOpacity>
        </LinearGradient>

        {submitted ? (
          <View style={styles.successContainer}>
            <Ionicons name="checkmark-circle" size={64} color={TEAL} />
            <Text style={styles.successTitle}>피드백 감사합니다!</Text>
            <Text style={styles.successMessage}>{submitMessage}</Text>
          </View>
        ) : (
          <ScrollView contentContainerStyle={styles.body} showsVerticalScrollIndicator={false}>
            {/* Overall rating */}
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>전체 만족도</Text>
              <Text style={styles.sectionHint}>이 매칭은 얼마나 마음에 드셨나요?</Text>
              <View style={styles.overallStars}>
                <StarRating value={overallRating} onChange={setOverallRating} size={36} />
              </View>
              {overallRating > 0 && (
                <Text style={styles.ratingLabel}>
                  {['', '별로예요', '조금 아쉬워요', '보통이에요', '좋았어요', '아주 마음에 들어요'][overallRating]}
                </Text>
              )}
            </View>

            {/* Dimension ratings */}
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>항목별 평가</Text>
              {DIMENSIONS.map(dim => (
                <View key={dim.key} style={styles.dimensionRow}>
                  <View style={styles.dimensionLabel}>
                    <Ionicons name={dim.icon as any} size={16} color={TEAL} />
                    <Text style={styles.dimensionText}>{dim.label}</Text>
                  </View>
                  <StarRating
                    value={dimensionRatings[dim.key] || 0}
                    onChange={v => setDimension(dim.key, v)}
                    size={20}
                  />
                </View>
              ))}
            </View>

            {/* Positive tags */}
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>좋았던 점</Text>
              <View style={styles.tagGrid}>
                {POSITIVE_TAGS.map(tag => (
                  <TouchableOpacity
                    key={tag}
                    style={[styles.tag, selectedPositive.includes(tag) && styles.tagSelectedPositive]}
                    onPress={() => toggleTag(tag, selectedPositive, setSelectedPositive)}
                  >
                    <Text style={[styles.tagText, selectedPositive.includes(tag) && styles.tagTextSelected]}>
                      {tag}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>
            </View>

            {/* Negative tags */}
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>아쉬웠던 점</Text>
              <View style={styles.tagGrid}>
                {NEGATIVE_TAGS.map(tag => (
                  <TouchableOpacity
                    key={tag}
                    style={[styles.tag, selectedNegative.includes(tag) && styles.tagSelectedNegative]}
                    onPress={() => toggleTag(tag, selectedNegative, setSelectedNegative)}
                  >
                    <Text style={[styles.tagText, selectedNegative.includes(tag) && styles.tagTextSelected]}>
                      {tag}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>
            </View>

            {/* Free text */}
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>추가 의견 (선택)</Text>
              <TextInput
                style={styles.freeTextInput}
                placeholder="매칭에 대해 더 알려주시면 다음 추천에 반영할게요..."
                placeholderTextColor="rgba(255,255,255,0.3)"
                value={freeText}
                onChangeText={setFreeText}
                multiline
                maxLength={300}
              />
              <Text style={styles.charCount}>{freeText.length}/300</Text>
            </View>

            {/* Notice */}
            <View style={styles.noticeBox}>
              <Ionicons name="information-circle-outline" size={16} color={TEAL} />
              <Text style={styles.noticeText}>
                피드백은 AI 매칭 알고리즘 개선에만 활용되며, 상대방에게는 전달되지 않습니다.
              </Text>
            </View>

            {/* Submit */}
            <TouchableOpacity
              style={[styles.submitButton, overallRating === 0 && styles.submitButtonDisabled]}
              onPress={handleSubmit}
              disabled={overallRating === 0 || isSubmitting}
            >
              {isSubmitting
                ? <ActivityIndicator color="#fff" />
                : <Text style={styles.submitText}>피드백 제출</Text>
              }
            </TouchableOpacity>

            <View style={{ height: 32 }} />
          </ScrollView>
        )}
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: DARK_BG,
  },
  header: {
    paddingHorizontal: 20,
    paddingTop: Platform.OS === 'ios' ? 52 : 16,
    paddingBottom: 20,
    position: 'relative',
  },
  headerTitle: {
    color: '#fff',
    fontSize: 20,
    fontWeight: '700',
  },
  headerSubtitle: {
    color: 'rgba(255,255,255,0.55)',
    fontSize: 13,
    marginTop: 4,
  },
  closeBtn: {
    position: 'absolute',
    right: 16,
    top: Platform.OS === 'ios' ? 52 : 16,
    padding: 8,
  },
  successContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 32,
    gap: 16,
  },
  successTitle: {
    color: '#fff',
    fontSize: 22,
    fontWeight: '700',
  },
  successMessage: {
    color: 'rgba(255,255,255,0.7)',
    fontSize: 15,
    textAlign: 'center',
    lineHeight: 22,
  },
  body: {
    paddingHorizontal: 20,
    paddingTop: 8,
  },
  section: {
    marginTop: 24,
  },
  sectionTitle: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 8,
  },
  sectionHint: {
    color: 'rgba(255,255,255,0.5)',
    fontSize: 13,
    marginBottom: 12,
  },
  overallStars: {
    alignItems: 'center',
    paddingVertical: 8,
  },
  ratingLabel: {
    color: TEAL,
    fontSize: 14,
    textAlign: 'center',
    marginTop: 8,
    fontWeight: '500',
  },
  dimensionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.06)',
  },
  dimensionLabel: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  dimensionText: {
    color: 'rgba(255,255,255,0.8)',
    fontSize: 14,
  },
  tagGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  tag: {
    borderRadius: 20,
    paddingHorizontal: 12,
    paddingVertical: 6,
    backgroundColor: 'rgba(255,255,255,0.06)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.12)',
  },
  tagSelectedPositive: {
    backgroundColor: `${TEAL}22`,
    borderColor: TEAL,
  },
  tagSelectedNegative: {
    backgroundColor: 'rgba(239,68,68,0.15)',
    borderColor: '#ef4444',
  },
  tagText: {
    color: 'rgba(255,255,255,0.6)',
    fontSize: 13,
  },
  tagTextSelected: {
    color: '#fff',
    fontWeight: '500',
  },
  freeTextInput: {
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
    color: '#fff',
    fontSize: 14,
    minHeight: 80,
    textAlignVertical: 'top',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
  },
  charCount: {
    color: 'rgba(255,255,255,0.3)',
    fontSize: 11,
    textAlign: 'right',
    marginTop: 4,
  },
  noticeBox: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    backgroundColor: `${TEAL}10`,
    borderRadius: 10,
    padding: 12,
    marginTop: 24,
    borderWidth: 1,
    borderColor: `${TEAL}30`,
  },
  noticeText: {
    color: 'rgba(255,255,255,0.55)',
    fontSize: 12,
    flex: 1,
    lineHeight: 18,
  },
  submitButton: {
    marginTop: 20,
    backgroundColor: TEAL,
    borderRadius: 14,
    paddingVertical: 16,
    alignItems: 'center',
  },
  submitButtonDisabled: {
    opacity: 0.35,
  },
  submitText: {
    color: '#0a0e1a',
    fontSize: 16,
    fontWeight: '700',
  },
});
