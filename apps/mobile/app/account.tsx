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

/**
 * User Account Screen
 * User profile and account settings with logout functionality
 */
export default function AccountScreen() {
  const [currentUserId, setCurrentUserId] = useState<string | null>(null);
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const [userName, setUserName] = useState<string | null>(null);
  const [trustScore, setTrustScore] = useState(0);
  const [currentTier, setCurrentTier] = useState<'pebble' | 'shell' | 'pearl' | 'coral'>('pebble');
  const [verifiedDocuments, setVerifiedDocuments] = useState<string[]>([]);

  useEffect(() => {
    const fetchUserInfo = async () => {
      try {
        const userId = await getCurrentUserId();
        setCurrentUserId(userId);

        const { data: { user } } = await supabase.auth.getUser();
        if (user?.email) {
          setUserEmail(user.email);
        }

        // Fetch user profile for name
        if (userId) {
          const { data: profileData } = await supabase
            .from('profiles')
            .select('name')
            .eq('user_id', userId)
            .single();

          if (profileData?.name) {
            setUserName(profileData.name);
          }
        }

        // Fetch trust score
        if (userId) {
          const { data: trustData } = await supabase
            .from('user_trust_scores')
            .select('total_trust_score')
            .eq('user_id', userId)
            .single();

          if (trustData) {
            const score = Math.round(trustData.total_trust_score * 100);
            setTrustScore(score);
            const tier = getTierFromScore(trustData.total_trust_score);
            // Filter to only valid tiers
            if (['pebble', 'shell', 'pearl', 'coral'].includes(tier)) {
              setCurrentTier(tier as 'pebble' | 'shell' | 'pearl' | 'coral');
            }
          }

          // Fetch verified documents
          const { data: docsData } = await supabase
            .from('user_documents')
            .select('document_type')
            .eq('user_id', userId)
            .eq('verification_status', 'verified');

          if (docsData) {
            setVerifiedDocuments(docsData.map(d => d.document_type));
          }
        }
      } catch (error) {
        console.error('❌ Failed to fetch user info:', error);
      }
    };

    fetchUserInfo();
  }, []);

  const handleLogout = () => {
    FLIOAlertAPI.alert(
      '로그아웃',
      '정말 로그아웃 하시겠습니까?',
      [
        { text: '취소', style: 'cancel' },
        { 
          text: '로그아웃', 
          style: 'destructive',
          onPress: async () => {
            try {
              console.log('🚪 Logging out user...');
              await supabase.auth.signOut();
              console.log('✅ User logged out successfully');
              router.replace('/');
            } catch (error) {
              console.error('❌ Logout failed:', error);
              FLIOAlertAPI.alert('오류', '로그아웃 중 문제가 발생했습니다.');
            }
          }
        }
      ]
    );
  };

  const goBack = () => {
    router.back();
  };

  const getTierKoreanName = (tier: string) => {
    const names: Record<string, string> = {
      pebble: '조약돌',
      shell: '조개',
      pearl: '진주',
      coral: '산호'
    };
    return names[tier] || '조약돌';
  };

  const getTierBenefits = (tier: string): string[] => {
    const benefits: Record<string, string[]> = {
      pebble: [
        '하루 3명/일 매칭',
        '조약돌 회원만 매칭',
        '하루 3회 조회',
        '제한된 기능'
      ],
      shell: [
        '하루 5명/일 매칭',
        '조개급 이하 회원 매칭',
        '하루 5회 조회',
        '기본 기능 이용'
      ],
      pearl: [
        '하루 8명/일 매칭',
        '진주급 이하 회원 매칭',
        '하루 10회 조회',
        '고급 필터 사용'
      ],
      coral: [
        '무제한 매칭',
        '모든 회원 매칭',
        '무제한 조회',
        '프리미엄 기능 전체'
      ]
    };
    return benefits[tier] || benefits['pebble'];
  };

  const menuItems = [
    {
      icon: 'person-circle-outline',
      title: '프로필 보기',
      subtitle: '내 답변 확인 및 수정',
      onPress: () => router.push('/(tabs)/profile'),
    },
    {
      icon: 'settings-outline',
      title: '계정 설정',
      subtitle: '개인정보 및 알림 설정',
      onPress: () => {
        FLIOAlertAPI.alert('준비 중', '계정 설정 기능은 곧 추가될 예정입니다.');
      },
    },
    {
      icon: 'help-circle-outline',
      title: '고객 지원',
      subtitle: '문의하기 및 FAQ',
      onPress: () => {
        FLIOAlertAPI.alert('준비 중', '고객 지원 기능은 곧 추가될 예정입니다.');
      },
    },
    {
      icon: 'information-circle-outline',
      title: '앱 정보',
      subtitle: '버전 정보 및 이용약관',
      onPress: () => {
        FLIOAlertAPI.alert('FLIO 앱', '버전 1.0.0\n\nAI 기반 매칭 서비스');
      },
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
        <Text style={styles.headerTitle}>내 계정</Text>
        <View style={styles.headerSpacer} />
      </View>

      <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
        {/* User Info Card */}
        <View style={styles.userInfoCard}>
          <View style={styles.userAvatar}>
            <Ionicons name="person" size={40} color="#2E7D7A" />
          </View>
          <View style={styles.userDetails}>
            <Text style={styles.userEmail}>
              {userEmail || 'user@example.com'}
            </Text>
            <Text style={styles.userId}>
              ID: {currentUserId?.slice(0, 8) || 'unknown'}...
            </Text>
          </View>
        </View>

        {/* Verification Card */}
        <View style={styles.verificationCard}>
          <View style={styles.verificationHeader}>
            <View style={styles.verificationTitleRow}>
              <Text style={styles.verificationTitle}>
                {userName || userEmail?.split('@')[0] || '회원'}님의 등급
              </Text>
            </View>
            <TrustBadge tier={currentTier} size="medium" />
          </View>

          <TouchableOpacity
            style={styles.trustScoreRow}
            onPress={() => router.push('/trust-breakdown')}
            activeOpacity={0.7}
          >
            <Text style={styles.trustScoreLabel}>현재 신뢰도</Text>
            <View style={styles.trustScoreRight}>
              <Text style={styles.trustScoreValue}>{trustScore}%</Text>
              <Ionicons name="chevron-forward" size={18} color="rgba(255,255,255,0.5)" />
            </View>
          </TouchableOpacity>

          <View style={styles.progressBarContainer}>
            <View style={styles.progressBar}>
              <View
                style={[
                  styles.progressBarFill,
                  { width: `${trustScore}%` }
                ]}
              />
            </View>
          </View>

          <View style={styles.verificationStatsRow}>
            <View style={styles.verificationStat}>
              <Ionicons name="shield-checkmark" size={16} color="#4FD1C7" />
              <Text style={styles.verificationStatText}>
                문서인증 {verifiedDocuments.length}/4
              </Text>
            </View>
          </View>

          <TouchableOpacity
            style={styles.upgradePrompt}
            onPress={() => router.push('/document-verification')}
            activeOpacity={0.7}
          >
            <Ionicons name="arrow-up-circle" size={18} color="#00FFC8" />
            <Text style={styles.upgradePromptText}>
              문서 인증하여 신뢰도 올리기
            </Text>
          </TouchableOpacity>

          {/* Tier Benefits */}
          <View style={styles.tierBenefits}>
            <Text style={styles.tierBenefitsTitle}>현재 혜택</Text>
            {getTierBenefits(currentTier).map((benefit, index) => (
              <View key={index} style={styles.benefitItem}>
                <Ionicons name="checkmark-circle" size={14} color="#4FD1C7" />
                <Text style={styles.benefitText}>{benefit}</Text>
              </View>
            ))}
          </View>

          {currentTier !== 'coral' && (
            <View style={styles.upgradeCtaContainer}>
              <TouchableOpacity
                style={styles.upgradeCtaButton}
                onPress={() => router.push('/tier')}
                activeOpacity={0.8}
              >
                <LinearGradient
                  colors={['#00FFC8', '#00D4AA']}
                  start={{ x: 0, y: 0 }}
                  end={{ x: 1, y: 0 }}
                  style={styles.upgradeCtaGradient}
                >
                  <Ionicons name="diamond" size={16} color="#FFFFFF" />
                  <Text style={styles.upgradeCtaText}>등급 업그레이드</Text>
                </LinearGradient>
              </TouchableOpacity>
            </View>
          )}
        </View>

        {/* Menu Items */}
        <View style={styles.menuSection}>
          {menuItems.map((item, index) => (
            <TouchableOpacity
              key={index}
              style={[
                styles.menuItem,
                item.highlight && styles.menuItemHighlight,
              ]}
              onPress={item.onPress}
              activeOpacity={0.7}
            >
              <View style={[
                styles.menuIcon,
                item.highlight && styles.menuIconHighlight,
              ]}>
                <Ionicons
                  name={item.icon as any}
                  size={24}
                  color='#4FD1C7'
                />
              </View>
              <View style={styles.menuContent}>
                <Text style={[
                  styles.menuTitle,
                  item.highlight && styles.menuTitleHighlight,
                ]}>
                  {item.title}
                </Text>
                <Text style={styles.menuSubtitle}>{item.subtitle}</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color="rgba(255,255,255,0.5)" />
            </TouchableOpacity>
          ))}
        </View>

        {/* Logout Button */}
        <View style={styles.logoutSection}>
          <TouchableOpacity
            style={styles.logoutButton}
            onPress={handleLogout}
            activeOpacity={0.8}
          >
            <Ionicons name="log-out-outline" size={24} color="#FF6B6B" />
            <Text style={styles.logoutText}>로그아웃</Text>
          </TouchableOpacity>
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
  userInfoCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.15)',
    borderRadius: 16,
    padding: 20,
    marginBottom: 24,
    gap: 16,
  },
  userAvatar: {
    width: 70,
    height: 70,
    borderRadius: 35,
    backgroundColor: 'rgba(255,255,255,0.9)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  userDetails: {
    flex: 1,
  },
  userEmail: {
    fontSize: 18,
    fontWeight: '600',
    color: '#FFFFFF',
    marginBottom: 4,
  },
  userId: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.7)',
    fontFamily: 'monospace',
  },
  menuSection: {
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 16,
    marginBottom: 24,
    overflow: 'hidden',
  },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 16,
    gap: 16,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.1)',
  },
  menuIcon: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(255,255,255,0.1)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  menuContent: {
    flex: 1,
  },
  menuTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFFFFF',
    marginBottom: 2,
  },
  menuSubtitle: {
    fontSize: 13,
    color: 'rgba(255,255,255,0.7)',
  },
  menuItemHighlight: {
    backgroundColor: 'rgba(79,209,199,0.15)',
    borderWidth: 1,
    borderColor: 'rgba(79,209,199,0.3)',
  },
  menuIconHighlight: {
    backgroundColor: 'rgba(79,209,199,0.2)',
  },
  menuTitleHighlight: {
    color: '#FFFFFF',
  },
  logoutSection: {
    marginBottom: 40,
  },
  logoutButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(255,107,107,0.2)',
    borderRadius: 16,
    paddingVertical: 18,
    gap: 12,
    borderWidth: 1,
    borderColor: 'rgba(255,107,107,0.3)',
  },
  logoutText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#FF6B6B',
  },
  // Verification Card Styles
  verificationCard: {
    backgroundColor: 'rgba(79,209,199,0.2)',
    borderRadius: 16,
    padding: 20,
    marginBottom: 24,
    borderWidth: 1,
    borderColor: 'rgba(79,209,199,0.3)',
  },
  verificationHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  verificationTitleRow: {
    flex: 1,
  },
  verificationTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  trustScoreRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 16,
    marginBottom: 12,
    paddingVertical: 4,
  },
  trustScoreLabel: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.8)',
  },
  trustScoreRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  trustScoreValue: {
    fontSize: 24,
    fontWeight: '700',
    color: '#4FD1C7',
  },
  progressBarContainer: {
    marginBottom: 16,
  },
  progressBar: {
    height: 6,
    backgroundColor: 'rgba(255,255,255,0.2)',
    borderRadius: 3,
    overflow: 'hidden',
  },
  progressBarFill: {
    height: '100%',
    backgroundColor: '#4FD1C7',
    borderRadius: 3,
  },
  verificationStatsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  verificationStat: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  verificationStatText: {
    fontSize: 13,
    color: 'rgba(255,255,255,0.9)',
    fontWeight: '500',
  },
  upgradePrompt: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingVertical: 14,
    paddingHorizontal: 14,
    backgroundColor: 'rgba(0,255,200,0.15)',
    borderRadius: 10,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: 'rgba(0,255,200,0.3)',
  },
  upgradePromptText: {
    fontSize: 14,
    color: '#00FFC8',
    fontWeight: '700',
    flex: 1,
  },
  tierBenefits: {
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderRadius: 12,
    padding: 16,
    marginTop: 8,
    marginBottom: 12,
  },
  tierBenefitsTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: '#FFFFFF',
    marginBottom: 12,
  },
  benefitItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 8,
  },
  benefitText: {
    fontSize: 13,
    color: 'rgba(255,255,255,0.9)',
    flex: 1,
  },
  upgradeCtaContainer: {
    marginTop: 8,
  },
  upgradeCtaButton: {
    borderRadius: 12,
    overflow: 'hidden',
  },
  upgradeCtaGradient: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 14,
    gap: 8,
  },
  upgradeCtaText: {
    fontSize: 15,
    fontWeight: '700',
    color: '#FFFFFF',
  },
});