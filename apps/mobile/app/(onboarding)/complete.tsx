import { useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Dimensions,
  Animated,
  ScrollView,
  SafeAreaView,
} from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';

const { width } = Dimensions.get('window');

/**
 * Onboarding Complete Screen
 * 
 * Congratulates user on completing their profile
 * Shows their verification badges and next steps
 */
export default function CompleteScreen() {
  const params = useLocalSearchParams();
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const scaleAnim = useRef(new Animated.Value(0.8)).current;
  const confettiAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 600,
        useNativeDriver: true,
      }),
      Animated.spring(scaleAnim, {
        toValue: 1,
        friction: 4,
        useNativeDriver: true,
      }),
    ]).start();

    // Confetti animation
    Animated.loop(
      Animated.sequence([
        Animated.timing(confettiAnim, {
          toValue: 1,
          duration: 1500,
          useNativeDriver: true,
        }),
        Animated.timing(confettiAnim, {
          toValue: 0,
          duration: 1500,
          useNativeDriver: true,
        }),
      ])
    ).start();
  }, []);

  const handleStart = () => {
    router.replace('/(tabs)/matches');
  };

  const handleVerify = () => {
    router.push('/document-verification');
  };


  return (
    <SafeAreaView style={styles.container}>
      {/* FLIO Ocean Gradient Background */}
      <LinearGradient
        colors={['#2E7D7A', '#4FD1C7', '#7EDDD9', '#B0E7E4']}
        locations={[0, 0.4, 0.7, 1]}
        style={styles.backgroundGradient}
      />
      

      <ScrollView 
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <Animated.View
          style={[
            styles.content,
            {
              opacity: fadeAnim,
              transform: [{ scale: scaleAnim }],
            },
          ]}
        >
        {/* Success Icon */}
        <View style={styles.iconContainer}>
          <LinearGradient
            colors={['#00FFC8', '#00D4AA', '#00B894']}
            style={styles.iconGradient}
          >
            <Ionicons name="checkmark" size={48} color="#FFFFFF" />
          </LinearGradient>
        </View>

        {/* Title */}
        <Text style={styles.title}>프로필 작성 완료! 🎉</Text>
        <Text style={styles.subtitle}>
          이제 당신의 인연을 찾을 준비가 됐어요
        </Text>

        {/* Badges Earned */}
        <View style={styles.badgesSection}>
          <Text style={styles.badgesTitle}>획득한 배지</Text>
          
          <View style={styles.badgeItem}>
            <View style={styles.badgeIcon}>
              <Ionicons name="shield-checkmark" size={24} color="#00FFC8" />
            </View>
            <View style={styles.badgeInfo}>
              <Text style={styles.badgeName}>얼굴 인증</Text>
              <Text style={styles.badgeDescription}>본인 확인 완료</Text>
            </View>
            <Ionicons name="checkmark-circle" size={24} color="#00FFC8" />
          </View>

          <View style={styles.badgeItem}>
            <View style={styles.badgeIcon}>
              <Ionicons name="person-circle" size={24} color="#00FFC8" />
            </View>
            <View style={styles.badgeInfo}>
              <Text style={styles.badgeName}>프로필 완성</Text>
              <Text style={styles.badgeDescription}>AI 질문 모두 답변 완료</Text>
            </View>
            <Ionicons name="checkmark-circle" size={24} color="#00FFC8" />
          </View>

          <View style={[styles.badgeItem, styles.badgeItemLocked]}>
            <View style={styles.badgeIcon}>
              <Ionicons name="school" size={24} color="rgba(255,255,255,0.3)" />
            </View>
            <View style={styles.badgeInfo}>
              <Text style={styles.badgeNameLocked}>학력 인증</Text>
              <Text style={styles.badgeDescriptionLocked}>설정에서 인증 가능</Text>
            </View>
            <Ionicons name="lock-closed" size={24} color="rgba(255,255,255,0.3)" />
          </View>

          <View style={[styles.badgeItem, styles.badgeItemLocked]}>
            <View style={styles.badgeIcon}>
              <Ionicons name="briefcase" size={24} color="rgba(255,255,255,0.3)" />
            </View>
            <View style={styles.badgeInfo}>
              <Text style={styles.badgeNameLocked}>직장 인증</Text>
              <Text style={styles.badgeDescriptionLocked}>설정에서 인증 가능</Text>
            </View>
            <Ionicons name="lock-closed" size={24} color="rgba(255,255,255,0.3)" />
          </View>
        </View>


        {/* CTA Buttons */}
        <TouchableOpacity
          style={styles.verifyButton}
          onPress={handleVerify}
          activeOpacity={0.8}
        >
          <LinearGradient
            colors={['#2E7D7A', '#1A5F5A']}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 0 }}
            style={styles.buttonGradient}
          >
            <Ionicons name="shield-checkmark-outline" size={20} color="#4FD1C7" />
            <View style={styles.verifyBtnText}>
              <Text style={styles.verifyButtonTitle}>서류 인증으로 등급 올리기</Text>
              <Text style={styles.verifyButtonSub}>신분증 1개만 해도 조약돌 → 조개 승급!</Text>
            </View>
            <Ionicons name="chevron-forward" size={18} color="rgba(255,255,255,0.5)" />
          </LinearGradient>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.startButton}
          onPress={handleStart}
          activeOpacity={0.8}
        >
          <LinearGradient
            colors={['#00FFC8', '#00D4AA']}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 0 }}
            style={styles.buttonGradient}
          >
            <Text style={styles.startButtonText}>일단 매칭 시작하기</Text>
            <Ionicons name="arrow-forward" size={20} color="#FFFFFF" />
          </LinearGradient>
        </TouchableOpacity>

        <Text style={styles.skipNote}>
          서류 인증은 나중에 프로필 탭에서도 할 수 있어요
        </Text>
        </Animated.View>
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
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
    paddingTop: 80,
    paddingBottom: 40,
  },
  content: {
    paddingHorizontal: 24,
    alignItems: 'center',
  },
  iconContainer: {
    marginBottom: 16,
  },
  iconGradient: {
    width: 80,
    height: 80,
    borderRadius: 40,
    alignItems: 'center',
    justifyContent: 'center',
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    color: '#FFFFFF',
    marginBottom: 6,
  },
  subtitle: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.7)',
    textAlign: 'center',
  },
  badgesSection: {
    width: '100%',
    marginTop: 20,
  },
  badgesTitle: {
    fontSize: 12,
    fontWeight: '600',
    color: '#00FFC8',
    marginBottom: 12,
  },
  badgeItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderRadius: 12,
    padding: 12,
    marginBottom: 8,
  },
  badgeItemLocked: {
    opacity: 0.6,
  },
  badgeIcon: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: 'rgba(0, 255, 200, 0.1)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  badgeInfo: {
    flex: 1,
    marginLeft: 12,
  },
  badgeName: {
    fontSize: 14,
    fontWeight: '600',
    color: '#FFFFFF',
    marginBottom: 2,
  },
  badgeDescription: {
    fontSize: 11,
    color: 'rgba(255, 255, 255, 0.5)',
  },
  badgeNameLocked: {
    fontSize: 14,
    fontWeight: '600',
    color: 'rgba(255, 255, 255, 0.5)',
    marginBottom: 2,
  },
  badgeDescriptionLocked: {
    fontSize: 11,
    color: 'rgba(255, 255, 255, 0.3)',
  },
  startButton: {
    width: '100%',
    marginTop: 10,
  },
  buttonGradient: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 16,
    borderRadius: 30,
    gap: 8,
  },
  verifyButton: {
    width: '100%',
    marginTop: 20,
    borderRadius: 30,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: 'rgba(79,209,199,0.4)',
  },
  verifyBtnText: {
    flex: 1,
    marginLeft: 4,
  },
  verifyButtonTitle: {
    fontSize: 15,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  verifyButtonSub: {
    fontSize: 11,
    color: 'rgba(255,255,255,0.6)',
    marginTop: 2,
  },
  startButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFFFFF',
    letterSpacing: 0.5,
  },
  skipNote: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.4)',
    textAlign: 'center',
    marginTop: 14,
  },
});
