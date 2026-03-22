/**
 * UserProfileModal
 * Shows a matched user's public profile with verification badges.
 * Opened from the matches screen when tapping a match card.
 */
import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Modal,
  ActivityIndicator,
  SafeAreaView,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { supabase } from '../services/supabase/client';
import TrustBadge from './TrustBadge';

interface PublicProfile {
  real_name?: string;
  age?: number;
  height_cm?: number;
  weight_kg?: number;
  education_level?: string;
  university_name?: string;
  major?: string;
  employment_status?: string;
  company_name?: string;
  job_title?: string;
  annual_income_range?: string;
  marital_status?: string;
}

interface FieldVerifications {
  [field: string]: boolean;
}

interface Props {
  visible: boolean;
  userId: string;
  compatibilityScore: number;
  trustTier?: string;
  onClose: () => void;
}

const FIELD_LABELS: { key: keyof PublicProfile; label: string; unit?: string }[] = [
  { key: 'real_name',           label: '이름' },
  { key: 'age',                 label: '나이',    unit: '세' },
  { key: 'height_cm',           label: '키',      unit: 'cm' },
  { key: 'weight_kg',           label: '몸무게',  unit: 'kg' },
  { key: 'education_level',     label: '학력' },
  { key: 'university_name',     label: '학교' },
  { key: 'major',               label: '전공' },
  { key: 'employment_status',   label: '직업 상태' },
  { key: 'company_name',        label: '회사' },
  { key: 'job_title',           label: '직책' },
  { key: 'annual_income_range', label: '연봉' },
  { key: 'marital_status',      label: '혼인 상태' },
];

const FIELD_TO_DOC: Record<string, string> = {
  real_name:           '신분증',
  age:                 '신분증',
  height_cm:           '건강검진서',
  weight_kg:           '건강검진서',
  university_name:     '졸업증명서',
  education_level:     '졸업증명서',
  major:               '졸업증명서',
  company_name:        '재직증명서',
  job_title:           '재직증명서',
  employment_status:   '재직증명서',
  annual_income_range: '소득증명서',
};

export default function UserProfileModal({ visible, userId, compatibilityScore, trustTier, onClose }: Props) {
  const [profile, setProfile] = useState<PublicProfile | null>(null);
  const [fieldVerifications, setFieldVerifications] = useState<FieldVerifications>({});
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (visible && userId) {
      loadProfile();
    }
  }, [visible, userId]);

  const loadProfile = async () => {
    setIsLoading(true);
    try {
      const [profileResult, trustResult] = await Promise.all([
        supabase.from('profiles').select(
          'real_name, age, height_cm, weight_kg, education_level, university_name, major, ' +
          'employment_status, company_name, job_title, annual_income_range, marital_status'
        ).eq('user_id', userId).single(),
        supabase.from('user_trust_scores').select(
          'field_verifications'
        ).eq('user_id', userId).maybeSingle(),
      ]);

      if (profileResult.data) setProfile(profileResult.data);
      if (trustResult.data?.field_verifications) {
        setFieldVerifications(trustResult.data.field_verifications);
      }
    } catch (err) {
      console.error('Failed to load match profile:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const scoreColor = compatibilityScore >= 0.8
    ? '#4FD1C7'
    : compatibilityScore >= 0.6
    ? '#68D391'
    : '#F6AD55';

  return (
    <Modal visible={visible} animationType="slide" presentationStyle="pageSheet" onRequestClose={onClose}>
      <SafeAreaView style={styles.safeArea}>
        <LinearGradient colors={['#1A3A38', '#2E7D7A']} style={StyleSheet.absoluteFillObject} />

        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity onPress={onClose} style={styles.closeBtn}>
            <Ionicons name="chevron-down" size={24} color="#FFFFFF" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>상대방 프로필</Text>
          <View style={{ width: 40 }} />
        </View>

        {isLoading ? (
          <View style={styles.center}>
            <ActivityIndicator size="large" color="#4FD1C7" />
          </View>
        ) : (
          <ScrollView contentContainerStyle={styles.scroll}>
            {/* Compatibility score banner */}
            <View style={styles.scoreBanner}>
              <Text style={styles.scoreLabelText}>궁합 점수</Text>
              <Text style={[styles.scoreValue, { color: scoreColor }]}>
                {(compatibilityScore * 100).toFixed(0)}%
              </Text>
              {trustTier && <TrustBadge tier={trustTier} size="small" />}
            </View>

            {/* Profile fields */}
            <View style={styles.card}>
              <Text style={styles.sectionTitle}>기본 정보</Text>
              {FIELD_LABELS.map(({ key, label, unit }) => {
                const value = profile?.[key];
                if (value == null) return null;
                const isVerified = fieldVerifications[key] === true;
                return (
                  <View key={key} style={styles.fieldRow}>
                    <Text style={styles.fieldLabel}>{label}</Text>
                    <View style={styles.fieldRight}>
                      <Text style={styles.fieldValue}>
                        {String(value)}{unit ? ` ${unit}` : ''}
                      </Text>
                      <View style={[styles.verifyBadge, isVerified ? styles.verifiedBadge : styles.unverifiedBadge]}>
                        <Ionicons
                          name={isVerified ? 'checkmark-circle' : 'ellipse-outline'}
                          size={12}
                          color={isVerified ? '#4FD1C7' : 'rgba(255,255,255,0.4)'}
                        />
                        <Text style={[styles.verifyText, !isVerified && styles.unverifiedText]}>
                          {isVerified ? '인증됨' : '미인증'}
                        </Text>
                      </View>
                    </View>
                  </View>
                );
              })}
            </View>
          </ScrollView>
        )}
      </SafeAreaView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#1A3A38',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingVertical: 16,
  },
  closeBtn: {
    width: 40,
    height: 40,
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  scroll: {
    paddingHorizontal: 20,
    paddingBottom: 40,
  },
  scoreBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.08)',
    borderRadius: 16,
    padding: 20,
    marginBottom: 16,
    gap: 12,
  },
  scoreLabelText: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.7)',
    flex: 1,
  },
  scoreValue: {
    fontSize: 28,
    fontWeight: '800',
  },
  card: {
    backgroundColor: 'rgba(255,255,255,0.07)',
    borderRadius: 16,
    padding: 20,
    borderWidth: 1,
    borderColor: 'rgba(79,209,199,0.2)',
  },
  sectionTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: '#FFFFFF',
    marginBottom: 16,
  },
  fieldRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.06)',
  },
  fieldLabel: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.6)',
    width: 90,
  },
  fieldRight: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'flex-end',
    gap: 8,
  },
  fieldValue: {
    fontSize: 14,
    fontWeight: '500',
    color: '#FFFFFF',
  },
  verifyBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
    borderRadius: 8,
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  verifiedBadge: {
    backgroundColor: 'rgba(79,209,199,0.15)',
  },
  unverifiedBadge: {
    backgroundColor: 'rgba(255,255,255,0.05)',
  },
  verifyText: {
    fontSize: 10,
    fontWeight: '600',
    color: '#4FD1C7',
  },
  unverifiedText: {
    color: 'rgba(255,255,255,0.35)',
  },
});
