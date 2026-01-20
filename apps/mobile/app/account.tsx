import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  SafeAreaView,
  Modal,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';

import { getCurrentUserId, supabase } from '../services/supabase/client';
import { FLIOAlertAPI } from '../components/FLIOAlert';
import VerificationCenter from '../components/VerificationCenter';
import TrustBadge, { getTierFromScore } from '../components/TrustBadge';

/**
 * User Account Screen
 * User profile and account settings with logout functionality
 */
export default function AccountScreen() {
  const [currentUserId, setCurrentUserId] = useState<string | null>(null);
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const [showVerificationCenter, setShowVerificationCenter] = useState(false);
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

  const handleVerifyDocument = (documentType: string) => {
    console.log('📄 Document verification clicked:', documentType);
    // Close the verification center modal
    setShowVerificationCenter(false);
    // Navigate to standalone document verification screen
    setTimeout(() => {
      router.push('/document-verification');
    }, 300);
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

  const menuItems = [
    {
      icon: 'person-circle-outline',
      title: '프로필 보기',
      subtitle: '내 답변 확인 및 수정',
      onPress: () => router.push('/(tabs)/profile'),
    },
    {
      icon: 'diamond-outline',
      title: '등급 & 업그레이드',
      subtitle: '요금제 확인 및 등급 업그레이드',
      onPress: () => router.push('/tier'),
      highlight: true,
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
        <TouchableOpacity
          style={styles.verificationCard}
          onPress={() => setShowVerificationCenter(true)}
          activeOpacity={0.8}
        >
          <View style={styles.verificationHeader}>
            <View style={styles.verificationTitleRow}>
              <Text style={styles.verificationTitle}>신뢰도 인증</Text>
              <TrustBadge tier={currentTier} size="small" />
            </View>
            <TouchableOpacity
              style={styles.verificationInfoButton}
              onPress={() => setShowVerificationCenter(true)}
            >
              <Ionicons name="information-circle-outline" size={20} color="#4FD1C7" />
            </TouchableOpacity>
          </View>

          <View style={styles.trustScoreRow}>
            <Text style={styles.trustScoreLabel}>현재 신뢰도</Text>
            <Text style={styles.trustScoreValue}>{trustScore}%</Text>
          </View>

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
                {verifiedDocuments.length}개 인증완료
              </Text>
            </View>
            <Ionicons name="chevron-forward" size={16} color="rgba(255,255,255,0.5)" />
          </View>

          {trustScore < 80 && (
            <View style={styles.upgradeHint}>
              <Ionicons name="arrow-up-circle" size={16} color="#00FFC8" />
              <Text style={styles.upgradeHintText}>
                문서 인증으로 신뢰도를 높이세요
              </Text>
            </View>
          )}

          <View style={styles.buttonRow}>
            <TouchableOpacity
              style={styles.verifyButton}
              onPress={(e) => {
                e.stopPropagation();
                router.push('/document-verification');
              }}
              activeOpacity={0.8}
            >
              <Ionicons name="shield-checkmark-outline" size={18} color="#FFFFFF" />
              <Text style={styles.verifyButtonText}>인증하기</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.tierButton}
              onPress={(e) => {
                e.stopPropagation();
                router.push('/tier');
              }}
              activeOpacity={0.8}
            >
              <Ionicons name="diamond-outline" size={18} color="#4FD1C7" />
              <Text style={styles.tierButtonText}>등급 보기</Text>
            </TouchableOpacity>
          </View>
        </TouchableOpacity>

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

      {/* Verification Center Modal */}
      <Modal
        visible={showVerificationCenter}
        animationType="slide"
        presentationStyle="fullScreen"
        onRequestClose={() => setShowVerificationCenter(false)}
      >
        <VerificationCenter
          currentTier={currentTier}
          trustScore={trustScore}
          verifiedDocuments={verifiedDocuments}
          onVerifyDocument={handleVerifyDocument}
          onClose={() => setShowVerificationCenter(false)}
        />
      </Modal>
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
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  verificationTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  verificationInfoButton: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: 'rgba(79,209,199,0.2)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  trustScoreRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  trustScoreLabel: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.8)',
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
  upgradeHint: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255,255,255,0.1)',
  },
  upgradeHintText: {
    fontSize: 13,
    color: '#00FFC8',
    fontWeight: '600',
  },
  buttonRow: {
    flexDirection: 'row',
    gap: 8,
    marginTop: 12,
  },
  verifyButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#4FD1C7',
    borderRadius: 12,
    paddingVertical: 12,
    gap: 6,
  },
  verifyButtonText: {
    fontSize: 14,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  tierButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(79,209,199,0.3)',
    borderRadius: 12,
    paddingVertical: 12,
    gap: 6,
    borderWidth: 1,
    borderColor: 'rgba(79,209,199,0.4)',
  },
  tierButtonText: {
    fontSize: 14,
    fontWeight: '700',
    color: '#4FD1C7',
  },
});