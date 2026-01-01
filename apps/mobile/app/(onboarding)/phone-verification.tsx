/**
 * FLIO Phone Verification Screen
 * Korean dating app style phone verification with SMS
 */

import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Animated,
  Image
} from 'react-native';
import { router } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { StatusBar } from 'expo-status-bar';

interface KoreanIdentityData {
  name: string;        // 실명
  birth_date: string;  // 생년월일 (19900315)
  gender: 'M' | 'F';   // 성별
  age: number;         // 계산된 나이
  phone: string;       // 휴대폰번호
  ci: string;          // Connecting Information
  di: string;          // Duplication Information
}

interface PhoneVerificationService {
  sendCode(phoneNumber: string): Promise<{
    verification_id: string;
    phone_number_masked: string;
    expires_in_minutes: number;
    message: string;
    resend_available_in: number;
  }>;
  verifyCode(phoneNumber: string, code: string): Promise<{
    verified: boolean;
    user_id: string;
    identity_data: KoreanIdentityData;
    next_step: string;
    message: string;
  }>;
}

const phoneVerificationService: PhoneVerificationService = {
  async sendCode(phoneNumber: string) {
    // Temporary mock service for development until backend is updated
    console.log('📱 MOCK: Sending code to', phoneNumber);
    
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    return {
      verification_id: `mock_${Date.now()}`,
      phone_number_masked: `${phoneNumber.slice(0, 3)}****${phoneNumber.slice(-4)}`,
      expires_in_minutes: 10,
      message: '인증번호를 전송했습니다. 10분 이내에 입력해주세요.',
      resend_available_in: 60
    };
  },
  
  async verifyCode(phoneNumber: string, code: string) {
    // Korean NICE PASS style identity verification simulation
    console.log('🔍 KOREAN ID VERIFICATION:', code, 'for', phoneNumber);
    
    // Simulate NICE PASS API delay
    await new Promise(resolve => setTimeout(resolve, 800));
    
    // Accept any 6-digit code for development
    if (code.length === 6) {
      // Generate realistic Korean identity data
      const names = ['김민수', '이지연', '박성호', '최유나', '정성민', '한소영', '조현우', '강혜진'];
      const name = names[Math.floor(Math.random() * names.length)];
      
      // Generate realistic birth date (ages 25-35 for serious marriage seekers)
      const currentYear = new Date().getFullYear();
      const birthYear = currentYear - (25 + Math.floor(Math.random() * 11)); // 25-35 years old
      const birthMonth = String(Math.floor(Math.random() * 12) + 1).padStart(2, '0');
      const birthDay = String(Math.floor(Math.random() * 28) + 1).padStart(2, '0');
      const birthDate = `${birthYear}${birthMonth}${birthDay}`;
      
      // Calculate age
      const today = new Date();
      const birth = new Date(parseInt(birthDate.slice(0, 4)), parseInt(birthDate.slice(4, 6)) - 1, parseInt(birthDate.slice(6, 8)));
      const age = today.getFullYear() - birth.getFullYear() - 
        (today.getMonth() < birth.getMonth() || (today.getMonth() === birth.getMonth() && today.getDate() < birth.getDate()) ? 1 : 0);
      
      const gender = Math.random() > 0.5 ? 'M' : 'F';
      
      const userId = `korean_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      const ci = `CI${Date.now()}${Math.random().toString(36).substr(2, 16)}`;
      const di = `DI${Date.now()}${Math.random().toString(36).substr(2, 16)}`;
      
      return {
        verified: true,
        user_id: userId,
        identity_data: {
          name,
          birth_date: birthDate,
          gender,
          age,
          phone: phoneNumber,
          ci,
          di
        },
        next_step: 'avatar_intro',
        message: `본인인증이 완료되었습니다!\n${name}님 (${age}세) 환영합니다.`
      };
    } else {
      throw new Error('인증번호가 일치하지 않습니다.');
    }
  }
};

export default function PhoneVerificationScreen() {
  const [step, setStep] = useState<'phone' | 'verify'>('phone');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [verificationCode, setVerificationCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [userId, setUserId] = useState<string | null>(null);
  
  const codeInputRefs = useRef<TextInput[]>([]);
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(50)).current;
  
  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 800,
        useNativeDriver: true,
      }),
      Animated.timing(slideAnim, {
        toValue: 0,
        duration: 600,
        useNativeDriver: true,
      })
    ]).start();
  }, [step]);

  useEffect(() => {
    if (countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [countdown]);

  const formatPhoneNumber = (value: string) => {
    const cleaned = value.replace(/\D/g, '');
    if (cleaned.length <= 3) return cleaned;
    if (cleaned.length <= 7) return `${cleaned.slice(0, 3)}-${cleaned.slice(3)}`;
    return `${cleaned.slice(0, 3)}-${cleaned.slice(3, 7)}-${cleaned.slice(7, 11)}`;
  };

  const isValidPhoneNumber = (phone: string) => {
    const cleaned = phone.replace(/\D/g, '');
    return /^(010|011|016|017|018|019)\d{8}$/.test(cleaned);
  };

  const handleSendCode = async () => {
    if (!isValidPhoneNumber(phoneNumber)) {
      Alert.alert('알림', '올바른 휴대폰 번호를 입력해주세요.\n(010-XXXX-XXXX 형식)');
      return;
    }

    setLoading(true);
    try {
      const cleanPhone = phoneNumber.replace(/\D/g, '');
      const result = await phoneVerificationService.sendCode(cleanPhone);
      
      Alert.alert('인증번호 전송', '인증번호를 전송했습니다.');
      setStep('verify');
      setCountdown(600); // 10 minutes
      setVerificationCode('');
      
      // Reset animation for verify step
      fadeAnim.setValue(0);
      slideAnim.setValue(50);
      Animated.parallel([
        Animated.timing(fadeAnim, {
          toValue: 1,
          duration: 800,
          useNativeDriver: true,
        }),
        Animated.timing(slideAnim, {
          toValue: 0,
          duration: 600,
          useNativeDriver: true,
        })
      ]).start();
      
    } catch (error: any) {
      Alert.alert('오류', error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyCode = async () => {
    if (verificationCode.length !== 6) {
      Alert.alert('알림', '인증번호 6자리를 모두 입력해주세요.');
      return;
    }

    setLoading(true);
    try {
      const cleanPhone = phoneNumber.replace(/\D/g, '');
      const result = await phoneVerificationService.verifyCode(cleanPhone, verificationCode);
      
      if (result.verified) {
        setUserId(result.user_id);
        const identityData = result.identity_data;
        
        Alert.alert(
          '본인인증 완료', 
          `${identityData.name}님 (${identityData.age}세) 환영합니다!`, 
          [
            {
              text: '확인',
              onPress: () => {
                // Pass all identity data to next screen
                const params = new URLSearchParams({
                  userId: result.user_id,
                  name: identityData.name,
                  age: identityData.age.toString(),
                  gender: identityData.gender,
                  birthDate: identityData.birth_date,
                  phone: identityData.phone,
                  ci: identityData.ci,
                  di: identityData.di
                });
                router.push(`/(onboarding)/avatar-intro?${params.toString()}`);
              }
            }
          ]
        );
      }
      
    } catch (error: any) {
      Alert.alert('인증 실패', error.message);
      setVerificationCode('');
      // Clear all inputs
      codeInputRefs.current.forEach(ref => ref?.clear());
    } finally {
      setLoading(false);
    }
  };

  const handleCodeInput = (value: string, index: number) => {
    // Only allow digits
    const digit = value.replace(/[^0-9]/g, '');
    
    const newCode = verificationCode.split('');
    newCode[index] = digit;
    const updatedCode = newCode.join('').slice(0, 6);
    setVerificationCode(updatedCode);

    // Auto-focus next input
    if (digit && index < 5) {
      codeInputRefs.current[index + 1]?.focus();
    }

    // Auto-verify when all 6 digits entered
    if (updatedCode.length === 6 && !updatedCode.includes('')) {
      setTimeout(() => handleVerifyCode(), 300);
    }
  };

  const handleResendCode = async () => {
    if (countdown > 0) return;
    
    setLoading(true);
    try {
      const cleanPhone = phoneNumber.replace(/\D/g, '');
      await phoneVerificationService.sendCode(cleanPhone);
      Alert.alert('재전송 완료', '인증번호를 다시 전송했습니다.');
      setCountdown(600);
    } catch (error: any) {
      Alert.alert('오류', error.message);
    } finally {
      setLoading(false);
    }
  };

  const formatCountdown = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
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
        onPress={() => router.back()}
        activeOpacity={0.7}
      >
        <Ionicons name="chevron-back" size={24} color="#FFFFFF" />
      </TouchableOpacity>

      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.keyboardView}
      >
        <View style={styles.centeredContainer}>

          <Animated.View 
            style={[
              styles.content,
              {
                opacity: fadeAnim,
                transform: [{ translateY: slideAnim }]
              }
            ]}
          >
            {step === 'phone' ? (
              <>
                <Text style={styles.title}>휴대폰 번호 인증</Text>
                <Text style={styles.subtitle}>
                  안전한 만남을 위해{'\n'}휴대폰 번호를 인증해주세요
                </Text>
                
                <View style={styles.inputContainer}>
                  <Text style={styles.inputLabel}>휴대폰 번호</Text>
                  <TextInput
                    style={styles.phoneInput}
                    value={phoneNumber}
                    onChangeText={(text) => setPhoneNumber(formatPhoneNumber(text))}
                    placeholder="010-0000-0000"
                    placeholderTextColor="#99B3CC"
                    keyboardType="phone-pad"
                    maxLength={13}
                    autoFocus
                  />
                </View>

                <TouchableOpacity
                  style={[
                    styles.button,
                    (!isValidPhoneNumber(phoneNumber) || loading) && styles.buttonDisabled
                  ]}
                  onPress={handleSendCode}
                  disabled={!isValidPhoneNumber(phoneNumber) || loading}
                >
                  <Text style={styles.buttonText}>
                    {loading ? '전송 중...' : '인증번호 받기'}
                  </Text>
                </TouchableOpacity>
              </>
            ) : (
              <>
                <Text style={styles.title}>인증번호 입력</Text>
                <Text style={styles.subtitle}>
                  {phoneNumber}으로{'\n'}전송된 6자리 인증번호를 입력해주세요
                </Text>
                
                {/* Development hint */}
                <View style={styles.devHint}>
                  <Text style={styles.devHintText}>
                    🧪 개발 모드: 아무 6자리 숫자나 입력
                  </Text>
                </View>
                
                <View style={styles.codeContainer}>
                  {Array.from({ length: 6 }, (_, index) => (
                    <TextInput
                      key={index}
                      ref={(ref) => (codeInputRefs.current[index] = ref!)}
                      style={styles.codeInput}
                      value={verificationCode[index] || ''}
                      onChangeText={(value) => handleCodeInput(value, index)}
                      keyboardType="number-pad"
                      maxLength={1}
                      textAlign="center"
                    />
                  ))}
                </View>

                {countdown > 0 && (
                  <Text style={styles.countdown}>
                    {formatCountdown(countdown)} 남음
                  </Text>
                )}

                <View style={styles.buttonGroup}>
                  <TouchableOpacity
                    style={[styles.resendButton, countdown > 0 && styles.buttonDisabled]}
                    onPress={handleResendCode}
                    disabled={countdown > 0 || loading}
                  >
                    <Text style={styles.resendButtonText}>
                      {countdown > 0 ? '재전송 대기' : '인증번호 재전송'}
                    </Text>
                  </TouchableOpacity>

                  <TouchableOpacity
                    style={[
                      styles.button,
                      (verificationCode.length !== 6 || loading) && styles.buttonDisabled
                    ]}
                    onPress={handleVerifyCode}
                    disabled={verificationCode.length !== 6 || loading}
                  >
                    <Text style={styles.buttonText}>
                      {loading ? '인증 중...' : '인증 완료'}
                    </Text>
                  </TouchableOpacity>
                </View>
              </>
            )}
          </Animated.View>
        </View>
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
    backgroundColor: 'rgba(255, 255, 255, 0.15)',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.2)',
  },
  keyboardView: {
    flex: 1,
  },
  centeredContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 24,
    paddingTop: 40,
    paddingBottom: 40,
  },
  content: {
    alignItems: 'center',
    width: '100%',
    maxWidth: 400,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#FFFFFF',
    textAlign: 'center',
    marginBottom: 12,
    textShadowColor: 'rgba(0, 0, 0, 0.4)',
    textShadowOffset: { width: 0, height: 2 },
    textShadowRadius: 4,
  },
  subtitle: {
    fontSize: 16,
    color: '#FFFFFF',
    textAlign: 'center',
    lineHeight: 24,
    marginBottom: 32,
    fontWeight: '600',
    textShadowColor: 'rgba(0, 0, 0, 0.4)',
    textShadowOffset: { width: 0, height: 2 },
    textShadowRadius: 4,
  },
  inputContainer: {
    width: '100%',
    marginBottom: 24,
  },
  inputLabel: {
    fontSize: 16,
    color: '#FFFFFF',
    marginBottom: 8,
    fontWeight: '600',
    textShadowColor: 'rgba(0, 0, 0, 0.4)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 2,
  },
  phoneInput: {
    backgroundColor: 'rgba(255, 255, 255, 0.15)',
    borderRadius: 25,
    padding: 18,
    fontSize: 18,
    color: '#FFFFFF',
    borderWidth: 2,
    borderColor: 'rgba(79, 209, 199, 0.6)',
    textAlign: 'center',
    letterSpacing: 2,
    fontWeight: '600',
  },
  codeContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    width: '100%',
    marginBottom: 24,
    paddingHorizontal: 20,
  },
  codeInput: {
    width: 45,
    height: 55,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    borderRadius: 8,
    fontSize: 20,
    fontWeight: 'bold',
    color: '#FFFFFF',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.2)',
  },
  countdown: {
    fontSize: 16,
    color: '#FFFFFF',
    fontWeight: '600',
    marginBottom: 24,
  },
  button: {
    backgroundColor: 'rgba(79, 209, 199, 0.9)',
    borderRadius: 25,
    paddingVertical: 18,
    paddingHorizontal: 32,
    width: '100%',
    alignItems: 'center',
    marginBottom: 16,
    shadowColor: 'rgba(0, 0, 0, 0.2)',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  buttonDisabled: {
    backgroundColor: 'rgba(255, 255, 255, 0.3)',
  },
  buttonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: 'bold',
    textShadowColor: 'rgba(47, 125, 122, 0.8)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 2,
  },
  buttonGroup: {
    width: '100%',
    gap: 12,
  },
  resendButton: {
    backgroundColor: 'transparent',
    borderWidth: 2,
    borderColor: 'rgba(79, 209, 199, 0.6)',
    borderRadius: 25,
    paddingVertical: 14,
    paddingHorizontal: 32,
    width: '100%',
    alignItems: 'center',
  },
  resendButtonText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '600',
  },
  devHint: {
    backgroundColor: 'rgba(79, 209, 199, 0.15)',
    borderRadius: 15,
    padding: 12,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: 'rgba(79, 209, 199, 0.4)',
  },
  devHintText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '600',
    textAlign: 'center',
  },
});