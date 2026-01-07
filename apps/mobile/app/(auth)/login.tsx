import { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from 'react-native';
import { router } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { supabase } from '../../services/supabase/client';
import { FLIOAlertAPI } from '../../components/FLIOAlert';
import { supabaseQuestionService } from '../../services/supabaseQuestionService';

export default function LoginScreen() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async () => {
    if (!email || !password) {
      FLIOAlertAPI.alert('입력 오류', '이메일과 비밀번호를 입력해주세요.');
      return;
    }

    setIsLoading(true);
    try {
      // Login with email and password
      const { data: authData, error: authError } = await supabase.auth.signInWithPassword({
        email: email.trim(),
        password: password,
      });

      if (authError) {
        console.error('Login error:', authError);
        
        // Handle email not confirmed error specifically
        if (authError.message?.includes('Email not confirmed') || authError.message?.includes('email_not_confirmed')) {
          FLIOAlertAPI.alert(
            '이메일 확인 필요',
            '계정이 생성되었지만 이메일 확인이 필요합니다. Supabase 설정에서 이메일 확인을 비활성화하거나, 관리자에게 문의하세요.',
            [
              {
                text: '확인',
                onPress: () => {
                  // Optionally redirect to signup or show instructions
                }
              }
            ]
          );
        } else {
          FLIOAlertAPI.alert('로그인 실패', authError.message || '이메일 또는 비밀번호가 올바르지 않습니다.');
        }
        setIsLoading(false);
        return;
      }

      if (authData.user) {
        console.log('✅ Login successful:', authData.user.id);
        
        // Check profile completion status
        try {
          const userProfile = await supabaseQuestionService.getUserProfile(authData.user.id);
          const hasAnsweredQuestions = (userProfile?.total_answers || 0) > 0;
          const canStartMatching = userProfile?.profile_completion.can_start_matching || false;
          
          console.log(`📊 User profile status: ${userProfile?.total_answers || 0} answers, can match: ${canStartMatching}`);
          
          if (!hasAnsweredQuestions) {
            // No questions answered - redirect to questions
            console.log('🔄 Redirecting to questions - no answers found');
            FLIOAlertAPI.alert(
              '프로필 완성하기', 
              '매칭을 시작하기 위해 질문에 답변해주세요.',
              [
                { 
                  text: '질문 답변하기', 
                  onPress: () => router.replace('/(onboarding)/questions')
                }
              ]
            );
            return;
          } else if (!canStartMatching) {
            // Some questions answered but not enough for matching
            console.log('🔄 Redirecting to questions - insufficient answers for matching');
            FLIOAlertAPI.alert(
              '프로필 완성하기', 
              `더 나은 매칭을 위해 몇 가지 질문에 더 답변해주세요. (현재: ${userProfile?.total_answers || 0}개 답변)`,
              [
                { 
                  text: '계속 답변하기', 
                  onPress: () => router.replace('/(onboarding)/questions')
                },
                { 
                  text: '나중에', 
                  style: 'cancel',
                  onPress: () => router.replace('/(tabs)/matches')
                }
              ]
            );
            return;
          } else {
            // Profile complete - go to matches
            console.log('✅ Profile complete - redirecting to matches');
            router.replace('/(tabs)/matches');
          }
        } catch (profileError) {
          console.error('❌ Failed to check profile status:', profileError);
          // If profile check fails, allow user to proceed but show warning
          FLIOAlertAPI.alert(
            '프로필 상태 확인 실패',
            '프로필 상태를 확인할 수 없습니다. 매칭 화면으로 이동합니다.',
            [
              {
                text: '확인',
                onPress: () => router.replace('/(tabs)/matches')
              }
            ]
          );
        }
      }
    } catch (error: any) {
      console.error('Login error:', error);
      FLIOAlertAPI.alert('로그인 오류', error.message || '로그인 중 문제가 발생했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSocialLogin = (provider: 'apple' | 'google' | 'kakao') => {
    // TODO: Implement social login
    console.log(`Login with ${provider}`);
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <LinearGradient
        colors={['#2E7D7A', '#4FD1C7', '#7EDDD9', '#B0E7E4']}
        locations={[0, 0.4, 0.7, 1]}
        style={styles.gradient}
      />

      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
      >
        {/* Back Button */}
        <TouchableOpacity
          style={styles.backButton}
          onPress={() => router.back()}
        >
          <Ionicons name="arrow-back" size={24} color="#FFFFFF" />
        </TouchableOpacity>

        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.logo}>FLIO</Text>
          <Text style={styles.title}>다시 만나서 반가워요!</Text>
        </View>

        {/* Form */}
        <View style={styles.form}>
          <View style={styles.inputContainer}>
            <Ionicons name="mail-outline" size={20} color="rgba(255,255,255,0.5)" />
            <TextInput
              style={styles.input}
              placeholder="이메일 주소"
              placeholderTextColor="rgba(255,255,255,0.4)"
              value={email}
              onChangeText={setEmail}
              keyboardType="email-address"
              autoCapitalize="none"
              autoCorrect={false}
            />
          </View>

          <View style={styles.inputContainer}>
            <Ionicons name="lock-closed-outline" size={20} color="rgba(255,255,255,0.5)" />
            <TextInput
              style={styles.input}
              placeholder="비밀번호"
              placeholderTextColor="rgba(255,255,255,0.4)"
              value={password}
              onChangeText={setPassword}
              secureTextEntry={!showPassword}
            />
            <TouchableOpacity onPress={() => setShowPassword(!showPassword)}>
              <Ionicons
                name={showPassword ? 'eye-off-outline' : 'eye-outline'}
                size={20}
                color="rgba(255,255,255,0.5)"
              />
            </TouchableOpacity>
          </View>

          <TouchableOpacity style={styles.forgotButton}>
            <Text style={styles.forgotText}>비밀번호를 잊으셨나요?</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.primaryButton}
            onPress={handleLogin}
            disabled={isLoading}
            activeOpacity={0.8}
          >
            <LinearGradient
              colors={['#00FFC8', '#00D4AA']}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={styles.gradientButton}
            >
              <Text style={styles.primaryButtonText}>
                {isLoading ? '로그인 중...' : '로그인'}
              </Text>
            </LinearGradient>
          </TouchableOpacity>
        </View>

        {/* Divider */}
        <View style={styles.divider}>
          <View style={styles.dividerLine} />
          <Text style={styles.dividerText}>또는</Text>
          <View style={styles.dividerLine} />
        </View>

        {/* Social Login */}
        <View style={styles.socialButtons}>
          <TouchableOpacity
            style={[styles.socialButton, styles.appleButton]}
            onPress={() => handleSocialLogin('apple')}
          >
            <Ionicons name="logo-apple" size={24} color="#FFFFFF" />
            <Text style={styles.socialButtonText}>Apple로 계속하기</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.socialButton, styles.googleButton]}
            onPress={() => handleSocialLogin('google')}
          >
            <Ionicons name="logo-google" size={22} color="#FFFFFF" />
            <Text style={styles.socialButtonText}>Google로 계속하기</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.socialButton, styles.kakaoButton]}
            onPress={() => handleSocialLogin('kakao')}
          >
            <Text style={styles.kakaoIcon}>💬</Text>
            <Text style={[styles.socialButtonText, { color: '#FFFFFF' }]}>
              카카오로 계속하기
            </Text>
          </TouchableOpacity>
        </View>

        {/* Sign Up Link */}
        <View style={styles.signUpSection}>
          <Text style={styles.signUpText}>계정이 없으신가요? </Text>
          <TouchableOpacity onPress={() => router.push('/(onboarding)/phone-verification')}>
            <Text style={styles.signUpLink}>가입하기</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#2E7D7A',
  },
  gradient: {
    ...StyleSheet.absoluteFillObject,
  },
  scrollContent: {
    flexGrow: 1,
    paddingHorizontal: 24,
    paddingTop: 60,
    paddingBottom: 40,
  },
  backButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: 'transparent',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 24,
    borderWidth: 2,
    borderColor: 'rgba(255, 255, 255, 0.8)',
  },
  header: {
    marginBottom: 40,
  },
  logo: {
    fontSize: 32,
    fontWeight: '800',
    color: '#FFFFFF',
    letterSpacing: 4,
    marginBottom: 8,
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  form: {
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
  forgotButton: {
    alignSelf: 'flex-end',
  },
  forgotText: {
    fontSize: 14,
    color: '#FFFFFF',
  },
  primaryButton: {
    marginTop: 8,
    width: '100%',
    backgroundColor: 'transparent',
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
    letterSpacing: 0.5,
  },
  divider: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: 32,
  },
  dividerLine: {
    flex: 1,
    height: 1,
    backgroundColor: 'rgba(255,255,255,0.1)',
  },
  dividerText: {
    paddingHorizontal: 16,
    fontSize: 14,
    color: 'rgba(255,255,255,0.8)',
  },
  socialButtons: {
    gap: 12,
  },
  socialButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    height: 52,
    borderRadius: 26,
    gap: 12,
  },
  appleButton: {
    backgroundColor: '#000000',
    borderWidth: 2,
    borderColor: 'rgba(255,255,255,0.8)',
  },
  googleButton: {
    backgroundColor: 'transparent',
    borderWidth: 2,
    borderColor: 'rgba(255,255,255,0.8)',
  },
  kakaoButton: {
    backgroundColor: '#FEE500',
  },
  socialButtonText: {
    fontSize: 15,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  kakaoIcon: {
    fontSize: 20,
  },
  signUpSection: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginTop: 32,
  },
  signUpText: {
    fontSize: 14,
    color: '#FFFFFF',
  },
  signUpLink: {
    fontSize: 14,
    fontWeight: '600',
    color: '#FFFFFF',
  },
});
