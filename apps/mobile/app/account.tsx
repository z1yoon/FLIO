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

/**
 * User Account Screen
 * User profile and account settings with logout functionality
 */
export default function AccountScreen() {
  const [currentUserId, setCurrentUserId] = useState<string | null>(null);
  const [userEmail, setUserEmail] = useState<string | null>(null);

  useEffect(() => {
    const fetchUserInfo = async () => {
      try {
        const userId = await getCurrentUserId();
        setCurrentUserId(userId);
        
        const { data: { user } } = await supabase.auth.getUser();
        if (user?.email) {
          setUserEmail(user.email);
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

        {/* Menu Items */}
        <View style={styles.menuSection}>
          {menuItems.map((item, index) => (
            <TouchableOpacity
              key={index}
              style={styles.menuItem}
              onPress={item.onPress}
              activeOpacity={0.7}
            >
              <View style={styles.menuIcon}>
                <Ionicons name={item.icon as any} size={24} color="#4FD1C7" />
              </View>
              <View style={styles.menuContent}>
                <Text style={styles.menuTitle}>{item.title}</Text>
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
});