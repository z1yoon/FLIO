/**
 * 인증 센터 (Verification Center)
 *
 * One-screen overview of everything a user can verify.
 * Shows current tier, point progress, and each document card with:
 *  - what it verifies (profile fields)
 *  - where to get it
 *  - +20pts reward
 *  - current status
 *
 * Accessible from:
 *  - Onboarding complete screen ("인증으로 등급 올리기" button)
 *  - Profile tab ("서류 인증으로 등급 올리기" button)
 *  - Matches screen tier upgrade nudge
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  SafeAreaView,
  Alert,
  Linking,
} from 'react-native';
import { router } from 'expo-router';
import * as ImagePicker from 'expo-image-picker';
import { LinearGradient } from 'expo-linear-gradient';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import { supabase } from '../services/supabase/client';
import { getCurrentUserId } from '../services/supabase/client';
import TrustBadge from '../components/TrustBadge';

// ── Types ──────────────────────────────────────────────────────────────
type DocStatus = 'not_submitted' | 'pending' | 'processing' | 'verified' | 'flagged' | 'rejected';

interface DocInfo {
  type: string;
  label: string;
  labelDetail: string;
  issueFrom: string;
  issueUrl?: string;
  verifiesLabel: string;
  icon: string;
  points: number;
  status: DocStatus;
}

// ── Static document catalogue ─────────────────────────────────────────
const DOC_CATALOGUE: Omit<DocInfo, 'status'>[] = [
  {
    type: 'id_card',
    label: '신분증',
    labelDetail: '주민등록증 · 운전면허증 · 여권',
    issueFrom: '본인 소지 서류',
    verifiesLabel: '이름, 나이',
    icon: '🪪',
    points: 20,
  },
  {
    type: 'health_checkup',
    label: '건강검진서',
    labelDetail: '국민건강보험공단 건강검진 결과지',
    issueFrom: '국민건강보험공단 건강iN',
    issueUrl: 'https://hi.nhis.or.kr',
    verifiesLabel: '키, 몸무게',
    icon: '🏥',
    points: 20,
  },
  {
    type: 'diploma',
    label: '졸업증명서',
    labelDetail: '대학교 졸업 · 학위증명서',
    issueFrom: '정부24 또는 대학교 학생처',
    issueUrl: 'https://www.gov.kr',
    verifiesLabel: '학교, 학력',
    icon: '🎓',
    points: 20,
  },
  {
    type: 'employment_cert',
    label: '재직증명서',
    labelDetail: '회사 발급 재직증명서',
    issueFrom: '재직 중인 회사 HR팀',
    verifiesLabel: '회사, 직책',
    icon: '💼',
    points: 20,
  },
  {
    type: 'income_proof',
    label: '소득증명서',
    labelDetail: '소득금액증명원 (국세청)',
    issueFrom: '홈택스 또는 정부24 (무료)',
    issueUrl: 'https://www.hometax.go.kr',
    verifiesLabel: '연봉',
    icon: '💰',
    points: 20,
  },
  {
    type: 'criminal_check',
    label: '범죄이력조회서',
    labelDetail: '성범죄 경력 조회 확인서',
    issueFrom: '경찰청 범죄경력조회 또는 정부24 (무료)',
    issueUrl: 'https://www.gov.kr',
    verifiesLabel: '범죄 이력 없음 🛡️',
    icon: '🛡️',
    points: 20,
  },
];

const TIER_LABELS: Record<string, { label: string; color: string; nextLabel?: string }> = {
  pebble: { label: '조약돌', color: '#A0AEC0', nextLabel: '신분증 1개 인증 → 조개' },
  shell:  { label: '조개',   color: '#68D391', nextLabel: '서류 2개 인증 → 진주' },
  pearl:  { label: '진주',   color: '#76E4F7', nextLabel: '서류 3개 인증 → 산호' },
  coral:  { label: '산호',   color: '#F6AD55', nextLabel: '서류 4개 인증 → 다이아' },
  diamond:{ label: '다이아', color: '#4FD1C7' },
};

const STATUS_CONFIG: Record<DocStatus, { label: string; color: string; icon: string }> = {
  not_submitted: { label: '+20점',     color: 'rgba(79,209,199,0.2)', icon: 'add-circle-outline' },
  pending:       { label: '검토 대기', color: 'rgba(246,173,85,0.2)', icon: 'time-outline' },
  processing:    { label: '처리 중',   color: 'rgba(246,173,85,0.2)', icon: 'sync-outline' },
  verified:      { label: '인증됨',    color: 'rgba(72,187,120,0.2)', icon: 'checkmark-circle' },
  flagged:       { label: '확인 필요', color: 'rgba(245,101,101,0.2)', icon: 'alert-circle-outline' },
  rejected:      { label: '거부됨',    color: 'rgba(245,101,101,0.2)', icon: 'close-circle-outline' },
};

// ── Component ──────────────────────────────────────────────────────────
export default function VerificationCenterScreen() {
  const [docs, setDocs] = useState<DocInfo[]>(
    DOC_CATALOGUE.map(d => ({ ...d, status: 'not_submitted' }))
  );
  const [trustPoints, setTrustPoints] = useState(0);
  const [trustTier, setTrustTier] = useState('pebble');
  const [userId, setUserId] = useState<string | null>(null);
  const [uploading, setUploading] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    init();
  }, []);

  const init = async () => {
    try {
      const id = await getCurrentUserId();
      if (!id) { router.replace('/(auth)/login'); return; }
      setUserId(id);
      await Promise.all([loadDocStatuses(id), loadTrustScore(id)]);
    } catch (e) {
      console.error('VerificationCenter init error:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const loadDocStatuses = async (id: string) => {
    const { data } = await supabase
      .from('user_documents')
      .select('document_type, verification_status')
      .eq('user_id', id);

    if (data) {
      setDocs(prev => prev.map(doc => {
        const found = data.find(d => d.document_type === doc.type);
        return found ? { ...doc, status: found.verification_status as DocStatus } : doc;
      }));
    }
  };

  const loadTrustScore = async (id: string) => {
    const { data } = await supabase
      .from('user_trust_scores')
      .select('total_trust_score, trust_tier')
      .eq('user_id', id)
      .maybeSingle();

    if (data) {
      setTrustPoints(Math.round((data.total_trust_score ?? 0) * 100));
      setTrustTier(data.trust_tier ?? 'pebble');
    }
  };

  const handleUpload = (docType: string) => {
    Alert.alert('문서 업로드', '어떻게 업로드하시겠습니까?', [
      { text: '카메라로 촬영', onPress: () => pickImage(docType, 'camera') },
      { text: '갤러리에서 선택', onPress: () => pickImage(docType, 'gallery') },
      { text: '취소', style: 'cancel' },
    ]);
  };

  const pickImage = async (docType: string, source: 'camera' | 'gallery') => {
    if (!userId) return;

    const launch = source === 'camera'
      ? ImagePicker.launchCameraAsync
      : ImagePicker.launchImageLibraryAsync;

    const result = await launch({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.8,
      allowsEditing: true,
      aspect: [4, 3],
    });

    if (result.canceled || !result.assets?.[0]) return;

    setUploading(docType);
    try {
      const uri = result.assets[0].uri;
      const blob = await (await fetch(uri)).blob();
      const fileName = `${userId}/${docType}_${Date.now()}.jpg`;

      const { error: storageError } = await supabase.storage
        .from('flio-documents')
        .upload(fileName, blob, { contentType: 'image/jpeg', upsert: false });

      if (storageError) throw storageError;

      const { data: urlData } = supabase.storage
        .from('flio-documents')
        .getPublicUrl(fileName);

      const apiUrl = process.env.EXPO_PUBLIC_AI_BACKEND_URL || 'http://localhost:8000';
      await fetch(`${apiUrl}/api/v1/verification/document/upload`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          document_type: docType,
          file_url: urlData.publicUrl,
        }),
      });

      setDocs(prev => prev.map(d =>
        d.type === docType ? { ...d, status: 'processing' } : d
      ));

      Alert.alert('업로드 완료 ✅', '문서가 제출되었습니다. 보통 몇 분 내에 인증이 완료됩니다.');
    } catch (e) {
      console.error('Upload error:', e);
      Alert.alert('오류', '문서 업로드 중 문제가 발생했습니다.');
    } finally {
      setUploading(null);
    }
  };

  const verifiedCount = docs.filter(d => d.status === 'verified').length;
  const tierInfo = TIER_LABELS[trustTier] ?? TIER_LABELS.pebble;
  const nextTierInfo = TIER_LABELS[trustTier]?.nextLabel;

  if (isLoading) {
    return (
      <View style={styles.center}>
        <LinearGradient colors={['#1A3A38', '#2E7D7A']} style={StyleSheet.absoluteFillObject} />
        <ActivityIndicator size="large" color="#4FD1C7" />
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="light" />
      <LinearGradient colors={['#1A3A38', '#2E7D7A']} style={StyleSheet.absoluteFillObject} />

      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity style={styles.backBtn} onPress={() => router.back()}>
          <Ionicons name="chevron-back" size={24} color="#FFFFFF" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>인증 센터</Text>
        <View style={{ width: 40 }} />
      </View>

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>

        {/* ── 현재 등급 카드 ── */}
        <View style={styles.tierCard}>
          <View style={styles.tierRow}>
            <TrustBadge tier={trustTier} size="large" />
            <View style={styles.tierInfo}>
              <Text style={styles.tierPoints}>{trustPoints}점</Text>
              <Text style={styles.tierVerified}>{verifiedCount}개 서류 인증됨</Text>
            </View>
          </View>

          {/* progress bar */}
          <View style={styles.progressBg}>
            <View style={[styles.progressFill, { width: `${Math.min(trustPoints, 100)}%` }]} />
          </View>
          <View style={styles.progressLabels}>
            {[0, 20, 40, 60, 80, 100].map(pt => (
              <Text key={pt} style={[styles.progressLabel, trustPoints >= pt && styles.progressLabelActive]}>
                {pt}
              </Text>
            ))}
          </View>

          {nextTierInfo && (
            <View style={styles.nextTierRow}>
              <Ionicons name="arrow-up-circle-outline" size={14} color="#4FD1C7" />
              <Text style={styles.nextTierText}>{nextTierInfo}</Text>
            </View>
          )}
        </View>

        {/* ── 필수 인증 (가입 시 완료) ── */}
        <Text style={styles.sectionLabel}>가입 시 완료된 인증</Text>
        <View style={styles.doneGroup}>
          {[
            { icon: 'call', label: '전화번호 인증', sub: '본인 명의 휴대폰' },
            { icon: 'camera', label: '얼굴 인증 (라이브니스)', sub: '실제 본인 확인' },
          ].map(item => (
            <View key={item.label} style={styles.doneRow}>
              <View style={styles.doneIcon}>
                <Ionicons name={item.icon as any} size={16} color="#4FD1C7" />
              </View>
              <View style={styles.doneText}>
                <Text style={styles.doneName}>{item.label}</Text>
                <Text style={styles.doneSub}>{item.sub}</Text>
              </View>
              <Ionicons name="checkmark-circle" size={20} color="#48BB78" />
            </View>
          ))}
        </View>

        {/* ── 서류 인증 (선택, 등급 결정) ── */}
        <Text style={styles.sectionLabel}>서류 인증 — 5개 중 5개 = 다이아 등급</Text>
        <Text style={styles.sectionSub}>
          아무 5개나 인증하면 최고 등급 달성! 직업이 없으면 재직증명서 대신 범죄이력조회서로 대체 가능해요.
        </Text>

        {/* ── 서류 인증 (등급 결정, 5개 = 다이아) ── */}
        <Text style={styles.sectionLabel}>서류 인증 — 5개 전부 인증 = 다이아 등급</Text>
        <Text style={styles.sectionSub}>
          5개를 모두 인증해야 최고 등급(다이아)이 됩니다. 각 서류 1개당 +20점.
        </Text>

        {docs.filter(d => d.type !== 'criminal_check').map(doc => {
          const cfg = STATUS_CONFIG[doc.status];
          const isVerified = doc.status === 'verified';
          const isPending = doc.status === 'processing' || doc.status === 'pending';
          const isUploading = uploading === doc.type;

          return (
            <View key={doc.type} style={[styles.docCard, isVerified && styles.docCardVerified]}>
              {/* Top row */}
              <View style={styles.docTop}>
                <Text style={styles.docIcon}>{doc.icon}</Text>
                <View style={styles.docMeta}>
                  <Text style={styles.docLabel}>{doc.label}</Text>
                  <Text style={styles.docDetail}>{doc.labelDetail}</Text>
                </View>
                <View style={[styles.statusPill, { backgroundColor: cfg.color }]}>
                  <Ionicons name={cfg.icon as any} size={12} color={isVerified ? '#48BB78' : '#FFFFFF'} />
                  <Text style={[styles.statusText, isVerified && { color: '#48BB78' }]}>{cfg.label}</Text>
                </View>
              </View>

              {/* Verifies + issue from */}
              <View style={styles.docMeta2}>
                <View style={styles.metaRow}>
                  <Text style={styles.metaKey}>인증 정보</Text>
                  <Text style={styles.metaVal}>{doc.verifiesLabel}</Text>
                </View>
                <View style={styles.metaRow}>
                  <Text style={styles.metaKey}>발급처</Text>
                  <View style={styles.metaValRow}>
                    <Text style={styles.metaVal}>{doc.issueFrom}</Text>
                    {doc.issueUrl && (
                      <TouchableOpacity onPress={() => Linking.openURL(doc.issueUrl!)}>
                        <Text style={styles.linkText}> 바로가기 →</Text>
                      </TouchableOpacity>
                    )}
                  </View>
                </View>
              </View>

              {!isVerified && (
                <TouchableOpacity
                  style={[styles.uploadBtn, isPending && styles.uploadBtnDisabled]}
                  onPress={() => handleUpload(doc.type)}
                  disabled={isPending || isUploading}
                  activeOpacity={0.8}
                >
                  {isUploading ? (
                    <ActivityIndicator size="small" color="#FFF" />
                  ) : (
                    <>
                      <Ionicons name={isPending ? 'time' : 'cloud-upload-outline'} size={16} color="#FFF" />
                      <Text style={styles.uploadBtnText}>
                        {isPending ? '검토 중...' : doc.status === 'rejected' ? '다시 업로드' : '인증하기'}
                      </Text>
                    </>
                  )}
                </TouchableOpacity>
              )}
            </View>
          );
        })}

        {/* ── 안전 뱃지 (별도 섹션, 등급 점수 없음) ── */}
        {(() => {
          const criminalDoc = docs.find(d => d.type === 'criminal_check')!;
          const cfg = STATUS_CONFIG[criminalDoc.status];
          const isVerified = criminalDoc.status === 'verified';
          const isPending = criminalDoc.status === 'processing' || criminalDoc.status === 'pending';
          const isUploading = uploading === 'criminal_check';
          return (
            <View>
              <Text style={styles.sectionLabel}>안전 뱃지 — 등급 점수와 무관</Text>
              <Text style={styles.sectionSub}>
                인증 시 프로필에 🛡️ 안전 뱃지가 표시됩니다. 많은 분들이 범죄 이력 없는 상대를 선호해요.
              </Text>
              <View style={[styles.docCard, styles.safetyCard, isVerified && styles.docCardVerified]}>
                <View style={styles.docTop}>
                  <Text style={styles.docIcon}>{criminalDoc.icon}</Text>
                  <View style={styles.docMeta}>
                    <Text style={styles.docLabel}>{criminalDoc.label}</Text>
                    <Text style={styles.docDetail}>{criminalDoc.labelDetail}</Text>
                  </View>
                  <View style={[styles.statusPill, { backgroundColor: isVerified ? 'rgba(72,187,120,0.2)' : 'rgba(99,179,237,0.2)' }]}>
                    <Ionicons name={isVerified ? 'shield-checkmark' : 'shield-outline'} size={12} color={isVerified ? '#48BB78' : '#63B3ED'} />
                    <Text style={[styles.statusText, { color: isVerified ? '#48BB78' : '#63B3ED' }]}>
                      {isVerified ? '안전 인증됨' : '안전 뱃지'}
                    </Text>
                  </View>
                </View>
                <View style={styles.docMeta2}>
                  <View style={styles.metaRow}>
                    <Text style={styles.metaKey}>발급처</Text>
                    <View style={styles.metaValRow}>
                      <Text style={styles.metaVal}>{criminalDoc.issueFrom}</Text>
                      {criminalDoc.issueUrl && (
                        <TouchableOpacity onPress={() => Linking.openURL(criminalDoc.issueUrl!)}>
                          <Text style={styles.linkText}> 바로가기 →</Text>
                        </TouchableOpacity>
                      )}
                    </View>
                  </View>
                </View>
                {!isVerified && (
                  <TouchableOpacity
                    style={[styles.uploadBtn, styles.safetyBtn, isPending && styles.uploadBtnDisabled]}
                    onPress={() => handleUpload('criminal_check')}
                    disabled={isPending || isUploading}
                    activeOpacity={0.8}
                  >
                    {isUploading ? <ActivityIndicator size="small" color="#FFF" /> : (
                      <>
                        <Ionicons name={isPending ? 'time' : 'shield-outline'} size={16} color="#FFF" />
                        <Text style={styles.uploadBtnText}>
                          {isPending ? '검토 중...' : '안전 뱃지 받기'}
                        </Text>
                      </>
                    )}
                  </TouchableOpacity>
                )}
              </View>
            </View>
          );
        })()}

        {/* ── 보안 안내 ── */}
        <View style={styles.securityNote}>
          <Ionicons name="lock-closed" size={16} color="rgba(255,255,255,0.5)" />
          <Text style={styles.securityText}>
            업로드된 서류는 AES-256으로 암호화 저장되며, 인증 완료 후 즉시 파기됩니다.
            제3자에게 절대 제공되지 않습니다.
          </Text>
        </View>

        <View style={{ height: 40 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#1A3A38' },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  header: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingHorizontal: 20, paddingVertical: 14,
  },
  backBtn: {
    width: 40, height: 40, borderRadius: 20,
    backgroundColor: 'rgba(255,255,255,0.1)', alignItems: 'center', justifyContent: 'center',
  },
  headerTitle: { fontSize: 19, fontWeight: '700', color: '#FFFFFF' },
  scroll: { paddingHorizontal: 20, paddingBottom: 60 },

  // Tier card
  tierCard: {
    backgroundColor: 'rgba(255,255,255,0.07)', borderRadius: 18, padding: 20,
    borderWidth: 1, borderColor: 'rgba(79,209,199,0.25)', marginBottom: 28,
  },
  tierRow: { flexDirection: 'row', alignItems: 'center', gap: 16, marginBottom: 16 },
  tierInfo: { flex: 1 },
  tierPoints: { fontSize: 30, fontWeight: '800', color: '#4FD1C7' },
  tierVerified: { fontSize: 13, color: 'rgba(255,255,255,0.6)', marginTop: 2 },
  progressBg: { height: 6, backgroundColor: 'rgba(255,255,255,0.12)', borderRadius: 3 },
  progressFill: { height: 6, backgroundColor: '#4FD1C7', borderRadius: 3 },
  progressLabels: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 4 },
  progressLabel: { fontSize: 10, color: 'rgba(255,255,255,0.3)' },
  progressLabelActive: { color: '#4FD1C7', fontWeight: '600' },
  nextTierRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 12 },
  nextTierText: { fontSize: 13, color: '#4FD1C7' },

  // Section labels
  sectionLabel: { fontSize: 13, fontWeight: '700', color: 'rgba(255,255,255,0.5)', marginBottom: 10, letterSpacing: 0.5 },
  sectionSub: { fontSize: 12, color: 'rgba(255,255,255,0.45)', marginBottom: 14, lineHeight: 18 },

  // Done group (phone + face)
  doneGroup: {
    backgroundColor: 'rgba(72,187,120,0.08)', borderRadius: 14, padding: 14,
    borderWidth: 1, borderColor: 'rgba(72,187,120,0.2)', marginBottom: 24, gap: 12,
  },
  doneRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  doneIcon: {
    width: 32, height: 32, borderRadius: 16,
    backgroundColor: 'rgba(79,209,199,0.15)', alignItems: 'center', justifyContent: 'center',
  },
  doneText: { flex: 1 },
  doneName: { fontSize: 14, fontWeight: '600', color: '#FFFFFF' },
  doneSub: { fontSize: 11, color: 'rgba(255,255,255,0.5)', marginTop: 2 },

  // Document card
  docCard: {
    backgroundColor: 'rgba(255,255,255,0.06)', borderRadius: 16, padding: 16,
    marginBottom: 12, borderWidth: 1, borderColor: 'rgba(255,255,255,0.1)',
  },
  docCardVerified: {
    borderColor: 'rgba(72,187,120,0.35)', backgroundColor: 'rgba(72,187,120,0.06)',
  },
  docTop: { flexDirection: 'row', alignItems: 'flex-start', gap: 12, marginBottom: 12 },
  docIcon: { fontSize: 28, lineHeight: 34 },
  docMeta: { flex: 1 },
  docLabel: { fontSize: 15, fontWeight: '700', color: '#FFFFFF', marginBottom: 3 },
  docDetail: { fontSize: 12, color: 'rgba(255,255,255,0.5)' },
  statusPill: {
    flexDirection: 'row', alignItems: 'center', gap: 4,
    borderRadius: 10, paddingHorizontal: 8, paddingVertical: 4,
  },
  statusText: { fontSize: 11, fontWeight: '600', color: '#FFFFFF' },
  docMeta2: { gap: 6, marginBottom: 14 },
  metaRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  metaKey: { fontSize: 12, color: 'rgba(255,255,255,0.4)', width: 54 },
  metaVal: { fontSize: 12, color: 'rgba(255,255,255,0.75)', flex: 1 },
  metaValRow: { flexDirection: 'row', alignItems: 'center', flex: 1, flexWrap: 'wrap' },
  linkText: { fontSize: 12, color: '#4FD1C7', fontWeight: '600' },
  uploadBtn: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    backgroundColor: '#2E7D7A', borderRadius: 10, paddingVertical: 11, gap: 6,
    borderWidth: 1, borderColor: 'rgba(79,209,199,0.4)',
  },
  uploadBtnDisabled: { backgroundColor: 'rgba(255,255,255,0.08)', borderColor: 'rgba(255,255,255,0.1)' },
  uploadBtnText: { fontSize: 14, fontWeight: '600', color: '#FFFFFF' },

  safetyCard: {
    borderColor: 'rgba(99,179,237,0.3)',
    backgroundColor: 'rgba(99,179,237,0.05)',
  },
  safetyBtn: {
    backgroundColor: '#2B6CB0',
    borderColor: 'rgba(99,179,237,0.4)',
  },
  // Security note
  securityNote: {
    flexDirection: 'row', alignItems: 'flex-start', gap: 8,
    backgroundColor: 'rgba(255,255,255,0.04)', borderRadius: 12, padding: 14,
    marginTop: 8,
  },
  securityText: { flex: 1, fontSize: 11, color: 'rgba(255,255,255,0.4)', lineHeight: 17 },
});
