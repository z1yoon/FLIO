import { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  TextInput,
  Dimensions,
  Animated,
  KeyboardAvoidingView,
  Platform,
  Alert,
} from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { StatusBar } from 'expo-status-bar';

const { width } = Dimensions.get('window');

/**
 * Password Setup Screen
 * User creates password for their phone number account
 */
export default function PasswordSetupScreen() {
  const params = useLocalSearchParams();
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // User data from phone verification
  const userName = params.name as string;
  const userPhone = params.phone as string;

  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(30)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 600,
        useNativeDriver: true,
      }),
      Animated.timing(slideAnim, {
        toValue: 0,
        duration: 600,
        useNativeDriver: true,
      }),
    ]).start();
  }, []);

  const validatePassword = () => {
    if (password.length < 6) {
      Alert.alert('비밀번호 오류', '비밀번호는 최소 6자리 이상이어야 합니다.');
      return false;
    }
    if (password !== confirmPassword) {
      Alert.alert('비밀번호 오류', '비밀번호가 일치하지 않습니다.');
      return false;
    }
    return true;
  };

  const handleCreateAccount = async () => {
    if (!validatePassword()) return;

    setIsLoading(true);
    try {
      // TODO: Create account with phone number + password
      console.log('Creating account:', { phone: userPhone, password });
      
      // Simulate account creation
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Navigate to face verification with all user data
      const faceVerificationParams = new URLSearchParams({
        userId: params.userId as string,
        name: userName,
        age: params.age as string,
        gender: params.gender as string,
        birthDate: params.birthDate as string,
        phone: userPhone,
        ci: params.ci as string,
        di: params.di as string
      });
      
      router.push(`/(onboarding)/face-verification?${faceVerificationParams.toString()}`);
      
    } catch (error) {
      console.error('Account creation error:', error);
      Alert.alert('계정 생성 오류', '계정 생성 중 문제가 발생했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoBack = () => {
    router.back();
  };

  return (
    <View style={styles.container}>
      <StatusBar style="light" />
      
      {/* FLIO Ocean Gradient Background */}
      <LinearGradient
        colors={['#2E7D7A', '#4FD1C7', '#7EDDD9', '#B0E7E4']}
        locations={[0, 0.4, 0.7, 1]}
        style={styles.backgroundGradient}
      />

      {/* Back Button */}
      <TouchableOpacity
        style={styles.backButton}
        onPress={handleGoBack}
        activeOpacity={0.7}
      >
        <Ionicons name="chevron-back" size={24} color="#FFFFFF" />
      </TouchableOpacity>

      <KeyboardAvoidingView
        style={styles.keyboardView}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <Animated.View
          style={[
            styles.content,
            {
              opacity: fadeAnim,
              transform: [{ translateY: slideAnim }],
            },
          ]}
        >
          {/* Header */}
          <View style={styles.header}>
            <Text style={styles.title}>비밀번호 설정</Text>
            <Text style={styles.subtitle}>
              {userName}님의 계정 비밀번호를 설정해주세요
            </Text>
            <Text style={styles.phoneText}>전화번호: {userPhone}</Text>
          </View>

          {/* Password Form */}
          <View style={styles.form}>
            <View style={styles.inputContainer}>
              <Ionicons name="lock-closed-outline" size={20} color="rgba(255, 255, 255, 0.7)" />
              <TextInput
                style={styles.input}
                placeholder="비밀번호 (최소 6자리)"
                placeholderTextColor="rgba(255, 255, 255, 0.5)"
                value={password}
                onChangeText={setPassword}
                secureTextEntry={!showPassword}
                autoCapitalize="none"
              />
              <TouchableOpacity onPress={() => setShowPassword(!showPassword)}>
                <Ionicons
                  name={showPassword ? 'eye-off-outline' : 'eye-outline'}
                  size={20}
                  color="rgba(255, 255, 255, 0.7)"
                />
              </TouchableOpacity>
            </View>

            <View style={styles.inputContainer}>
              <Ionicons name="lock-closed-outline" size={20} color="rgba(255, 255, 255, 0.7)" />
              <TextInput
                style={styles.input}
                placeholder="비밀번호 확인"
                placeholderTextColor="rgba(255, 255, 255, 0.5)"
                value={confirmPassword}
                onChangeText={setConfirmPassword}
                secureTextEntry={!showConfirmPassword}
                autoCapitalize="none"
              />
              <TouchableOpacity onPress={() => setShowConfirmPassword(!showConfirmPassword)}>
                <Ionicons
                  name={showConfirmPassword ? 'eye-off-outline' : 'eye-outline'}
                  size={20}
                  color="rgba(255, 255, 255, 0.7)"
                />
              </TouchableOpacity>
            </View>
          </View>

          {/* Create Account Button */}
          <TouchableOpacity
            style={[styles.primaryButton, (!password || !confirmPassword || isLoading) && styles.primaryButtonDisabled]}
            onPress={handleCreateAccount}
            disabled={!password || !confirmPassword || isLoading}
            activeOpacity={0.8}
          >
            <LinearGradient
              colors={['#00FFC8', '#00D4AA']}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={styles.gradientButton}
            >
              <Text style={styles.primaryButtonText}>
                {isLoading ? '계정 생성 중...' : '계정 생성하기'}
              </Text>
            </LinearGradient>
          </TouchableOpacity>

          {/* Security Info */}
          <View style={styles.securityInfo}>
            <Ionicons name="shield-checkmark" size={16} color="rgba(255, 255, 255, 0.8)" />
            <Text style={styles.securityText}>
              비밀번호는 안전하게 암호화되어 저장됩니다
            </Text>
          </View>
        </Animated.View>
      </KeyboardAvoidingView>
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
  backButton: {
    position: 'absolute',
    top: 60,
    left: 20,
    zIndex: 10,
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: 'transparent',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: 'rgba(255, 255, 255, 0.8)',
  },
  keyboardView: {
    flex: 1,
  },
  content: {
    flex: 1,
    paddingHorizontal: 24,
    paddingTop: 120,
    paddingBottom: 40,
    justifyContent: 'center',
  },
  header: {
    alignItems: 'center',
    marginBottom: 48,
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
    color: '#FFFFFF',
    marginBottom: 12,
    textAlign: 'center',
  },
  subtitle: {
    fontSize: 16,
    color: 'rgba(255, 255, 255, 0.8)',
    textAlign: 'center',
    lineHeight: 24,
    marginBottom: 8,
  },
  phoneText: {
    fontSize: 14,
    color: '#4FD1C7',
    fontWeight: '600',
  },
  form: {
    marginBottom: 32,
    gap: 16,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'transparent',
    borderRadius: 16,
    paddingHorizontal: 16,
    height: 56,
    gap: 12,
    borderWidth: 2,
    borderColor: 'rgba(255, 255, 255, 0.6)',
  },
  input: {
    flex: 1,
    fontSize: 16,
    color: '#FFFFFF',
  },
  primaryButton: {
    marginBottom: 24,
    width: '100%',
  },
  primaryButtonDisabled: {
    opacity: 0.6,
  },
  gradientButton: {
    paddingVertical: 18,
    borderRadius: 30,
    alignItems: 'center',
  },
  primaryButtonText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  securityInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  securityText: {
    fontSize: 12,
    color: 'rgba(255, 255, 255, 0.7)',
  },
});