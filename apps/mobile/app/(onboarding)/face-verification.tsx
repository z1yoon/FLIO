import { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Dimensions,
  Animated,
} from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { FLIOAlertAPI, FLIOAlertButton } from '../../components/FLIOAlert';

const { width, height } = Dimensions.get('window');

type VerificationStep = 'intro' | 'photo_upload' | 'live_capture' | 'processing' | 'result';

/**
 * Face Verification Screen
 * 
 * Implements the 85% face match verification:
 * 1. User uploads profile photo
 * 2. User takes live selfie (with liveness detection)
 * 3. Backend compares embeddings
 * 4. Show verification result
 */
export default function FaceVerificationScreen() {
  const params = useLocalSearchParams();
  const [step, setStep] = useState<VerificationStep>('intro');
  const [profilePhoto, setProfilePhoto] = useState<string | null>(null);
  const [livePhoto, setLivePhoto] = useState<string | null>(null);
  const [verificationResult, setVerificationResult] = useState<{
    verified: boolean;
    similarity: number;
  } | null>(null);
  
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const pulseAnim = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, {
      toValue: 1,
      duration: 500,
      useNativeDriver: true,
    }).start();

    Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, {
          toValue: 1.05,
          duration: 1500,
          useNativeDriver: true,
        }),
        Animated.timing(pulseAnim, {
          toValue: 1,
          duration: 1500,
          useNativeDriver: true,
        }),
      ])
    ).start();
  }, []);

  const handleUploadPhoto = () => {
    // TODO: Implement actual photo picker
    FLIOAlertAPI.alert(
      '사진 업로드',
      '프로필에 사용할 사진을 선택해주세요',
      [
        { text: '갤러리에서 선택', onPress: () => simulatePhotoUpload() },
        { text: '카메라로 촬영', onPress: () => simulatePhotoUpload() },
        { text: '취소', style: 'cancel' },
      ]
    );
  };

  const simulatePhotoUpload = () => {
    // Simulate photo upload
    setProfilePhoto('uploaded');
    setStep('live_capture');
  };

  const handleLiveCapture = () => {
    // TODO: Implement actual camera capture with liveness detection
    FLIOAlertAPI.alert(
      '실시간 촬영',
      '얼굴이 화면에 잘 보이게 해주세요\n잠시 후 자동으로 촬영됩니다',
      [
        { text: '촬영하기', onPress: () => simulateLiveCapture() },
        { text: '취소', style: 'cancel' },
      ]
    );
  };

  const simulateLiveCapture = () => {
    setLivePhoto('captured');
    setStep('processing');
    
    // Simulate verification processing
    setTimeout(() => {
      // Simulate 92% match (successful verification)
      setVerificationResult({
        verified: true,
        similarity: 92.3,
      });
      setStep('result');
    }, 2500);
  };

  const handleComplete = () => {
    // Navigate to avatar intro with user data from previous screens
    const avatarParams = new URLSearchParams({
      userId: params.userId as string,
      name: params.name as string,
      age: params.age as string,
      gender: params.gender as string,
      birthDate: params.birthDate as string,
      phone: params.phone as string,
      ci: params.ci as string,
      di: params.di as string
    });
    router.push(`/(onboarding)/avatar-intro?${avatarParams.toString()}`);
  };

  const handleRetry = () => {
    setStep('photo_upload');
    setProfilePhoto(null);
    setLivePhoto(null);
    setVerificationResult(null);
  };

  const handleGoBack = () => {
    router.back();
  };

  const renderContent = () => {
    switch (step) {
      case 'intro':
        return (
          <Animated.View style={[styles.content, { opacity: fadeAnim }]}>
            <View style={styles.iconContainer}>
              <Ionicons name="shield-checkmark" size={64} color="#00FFC8" />
            </View>
            <Text style={styles.title}>얼굴 인증</Text>
            <Text style={styles.description}>
              FLIO는 안전한 만남을 위해{'\n'}
              얼굴 인증을 진행합니다.{'\n\n'}
              프로필 사진과 실시간 셀피를{'\n'}
              비교하여 85% 이상 일치해야{'\n'}
              인증이 완료됩니다.
            </Text>
            
            <View style={styles.featureList}>
              <View style={styles.featureItem}>
                <Ionicons name="checkmark-circle" size={24} color="#00FFC8" />
                <Text style={styles.featureText}>사기 프로필 방지</Text>
              </View>
              <View style={styles.featureItem}>
                <Ionicons name="checkmark-circle" size={24} color="#00FFC8" />
                <Text style={styles.featureText}>실제 본인 확인</Text>
              </View>
              <View style={styles.featureItem}>
                <Ionicons name="checkmark-circle" size={24} color="#00FFC8" />
                <Text style={styles.featureText}>신뢰도 배지 획득</Text>
              </View>
            </View>

            <TouchableOpacity
              style={styles.primaryButton}
              onPress={() => setStep('photo_upload')}
              activeOpacity={0.8}
            >
              <LinearGradient
                colors={['#00FFC8', '#00D4AA']}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 0 }}
                style={styles.gradientButton}
              >
                <Text style={styles.primaryButtonText}>인증 시작하기</Text>
              </LinearGradient>
            </TouchableOpacity>

          </Animated.View>
        );

      case 'photo_upload':
        return (
          <Animated.View style={[styles.content, { opacity: fadeAnim }]}>
            <Text style={styles.stepTitle}>1단계: 프로필 사진</Text>
            <Text style={styles.stepDescription}>
              프로필에 사용할 사진을 업로드해주세요
            </Text>

            <TouchableOpacity
              style={styles.uploadBox}
              onPress={handleUploadPhoto}
              activeOpacity={0.7}
            >
              {profilePhoto ? (
                <View style={styles.uploadedIndicator}>
                  <Ionicons name="checkmark-circle" size={48} color="#00FFC8" />
                  <Text style={styles.uploadedText}>사진 업로드됨</Text>
                </View>
              ) : (
                <>
                  <Ionicons name="cloud-upload-outline" size={48} color="rgba(255,255,255,0.5)" />
                  <Text style={styles.uploadText}>사진 업로드</Text>
                </>
              )}
            </TouchableOpacity>

            <View style={styles.tipsContainer}>
              <Text style={styles.tipsTitle}>좋은 프로필 사진 팁</Text>
              <Text style={styles.tipItem}>• 얼굴이 잘 보이는 정면 사진</Text>
              <Text style={styles.tipItem}>• 밝은 조명에서 촬영</Text>
              <Text style={styles.tipItem}>• 선글라스나 마스크 없이</Text>
            </View>
          </Animated.View>
        );

      case 'live_capture':
        return (
          <Animated.View style={[styles.content, { opacity: fadeAnim }]}>
            <Text style={styles.stepTitle}>2단계: 실시간 셀피</Text>
            <Text style={styles.stepDescription}>
              프로필 사진과 비교할{'\n'}
              실시간 셀피를 촬영해주세요
            </Text>

            <View style={styles.cameraPreview}>
              <View style={styles.faceGuide}>
                <View style={styles.faceCircle} />
              </View>
              <Text style={styles.cameraHint}>얼굴을 원 안에 맞춰주세요</Text>
            </View>

            <TouchableOpacity
              style={styles.captureButton}
              onPress={handleLiveCapture}
              activeOpacity={0.8}
            >
              <View style={styles.captureButtonInner}>
                <Ionicons name="camera" size={32} color="#000000" />
              </View>
            </TouchableOpacity>

            <Text style={styles.livenessHint}>
              * 눈을 깜빡여주세요 (자동 감지)
            </Text>
          </Animated.View>
        );

      case 'processing':
        return (
          <Animated.View style={[styles.content, { opacity: fadeAnim }]}>
            <Animated.View
              style={[styles.processingIcon, { transform: [{ scale: pulseAnim }] }]}
            >
              <Ionicons name="scan" size={64} color="#00FFC8" />
            </Animated.View>
            <Text style={styles.processingTitle}>얼굴 인증 중...</Text>
            <Text style={styles.processingDescription}>
              AI가 두 사진을 비교하고 있습니다{'\n'}
              잠시만 기다려주세요
            </Text>

            <View style={styles.processingSteps}>
              <View style={styles.processingStep}>
                <Ionicons name="checkmark-circle" size={20} color="#00FFC8" />
                <Text style={styles.processingStepText}>얼굴 감지 완료</Text>
              </View>
              <View style={styles.processingStep}>
                <Ionicons name="checkmark-circle" size={20} color="#00FFC8" />
                <Text style={styles.processingStepText}>생체 인증 완료</Text>
              </View>
              <View style={[styles.processingStep, styles.processingStepActive]}>
                <View style={styles.loadingDot} />
                <Text style={styles.processingStepText}>유사도 계산 중...</Text>
              </View>
            </View>
          </Animated.View>
        );

      case 'result':
        return (
          <Animated.View style={[styles.content, { opacity: fadeAnim }]}>
            {verificationResult?.verified ? (
              <>
                <View style={styles.successIcon}>
                  <Ionicons name="checkmark-circle" size={80} color="#00FFC8" />
                </View>
                <Text style={styles.successTitle}>인증 완료! 🎉</Text>
                <Text style={styles.resultScore}>
                  유사도: {verificationResult.similarity.toFixed(1)}%
                </Text>
                <Text style={styles.successDescription}>
                  프로필 사진과 실시간 셀피가{'\n'}
                  85% 이상 일치합니다.{'\n\n'}
                  이제 신뢰 배지가 표시됩니다!
                </Text>

                <View style={styles.badgePreview}>
                  <Ionicons name="shield-checkmark" size={24} color="#00FFC8" />
                  <Text style={styles.badgeText}>얼굴 인증됨</Text>
                </View>

                <TouchableOpacity
                  style={styles.primaryButton}
                  onPress={handleComplete}
                  activeOpacity={0.8}
                >
                  <LinearGradient
                    colors={['#00FFC8', '#00D4AA']}
                    start={{ x: 0, y: 0 }}
                    end={{ x: 1, y: 0 }}
                    style={styles.gradientButton}
                  >
                    <Text style={styles.primaryButtonText}>완료</Text>
                  </LinearGradient>
                </TouchableOpacity>
              </>
            ) : (
              <>
                <View style={styles.failIcon}>
                  <Ionicons name="close-circle" size={80} color="#FF6B6B" />
                </View>
                <Text style={styles.failTitle}>인증 실패</Text>
                <Text style={styles.resultScore}>
                  유사도: {verificationResult?.similarity.toFixed(1)}%
                </Text>
                <Text style={styles.failDescription}>
                  프로필 사진과 실시간 셀피의{'\n'}
                  유사도가 85% 미만입니다.{'\n\n'}
                  다른 사진으로 다시 시도해주세요.
                </Text>

                <TouchableOpacity
                  style={styles.retryButton}
                  onPress={handleRetry}
                  activeOpacity={0.8}
                >
                  <Text style={styles.retryButtonText}>다시 시도</Text>
                </TouchableOpacity>
              </>
            )}
          </Animated.View>
        );
    }
  };

  return (
    <View style={styles.container}>
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
        <Ionicons name="chevron-back" size={24} color="#00FFC8" />
      </TouchableOpacity>

      {/* Progress indicator */}
      <View style={styles.stepIndicator}>
        {['intro', 'photo_upload', 'live_capture', 'processing', 'result'].map((s, i) => (
          <View
            key={s}
            style={[
              styles.stepDot,
              ['intro', 'photo_upload', 'live_capture', 'processing', 'result'].indexOf(step) >= i &&
                styles.stepDotActive,
            ]}
          />
        ))}
      </View>

      {renderContent()}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#2E7D7A',
    paddingTop: 60,
  },
  backgroundGradient: {
    ...StyleSheet.absoluteFillObject,
  },
  stepIndicator: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 8,
    marginBottom: 24,
  },
  stepDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: 'rgba(255, 255, 255, 0.8)',
  },
  stepDotActive: {
    backgroundColor: '#00FFC8',
  },
  content: {
    flex: 1,
    paddingHorizontal: 24,
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconContainer: {
    marginBottom: 24,
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
    color: '#FFFFFF',
    marginBottom: 16,
  },
  description: {
    fontSize: 16,
    color: 'rgba(255, 255, 255, 0.7)',
    textAlign: 'center',
    lineHeight: 26,
  },
  featureList: {
    marginTop: 32,
    gap: 16,
  },
  featureItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  featureText: {
    fontSize: 16,
    color: '#FFFFFF',
  },
  primaryButton: {
    marginTop: 40,
    width: '100%',
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
  stepTitle: {
    fontSize: 24,
    fontWeight: '700',
    color: '#FFFFFF',
    marginBottom: 8,
  },
  stepDescription: {
    fontSize: 16,
    color: 'rgba(255, 255, 255, 0.7)',
    textAlign: 'center',
    marginBottom: 32,
  },
  uploadBox: {
    width: width - 80,
    height: width - 80,
    backgroundColor: 'transparent',
    borderRadius: 20,
    borderWidth: 2,
    borderColor: 'rgba(255, 255, 255, 0.8)',
    borderStyle: 'dashed',
    alignItems: 'center',
    justifyContent: 'center',
  },
  uploadText: {
    fontSize: 16,
    color: 'rgba(255, 255, 255, 0.5)',
    marginTop: 12,
  },
  uploadedIndicator: {
    alignItems: 'center',
  },
  uploadedText: {
    fontSize: 16,
    color: '#00FFC8',
    marginTop: 12,
  },
  tipsContainer: {
    marginTop: 32,
    alignSelf: 'flex-start',
  },
  tipsTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#00FFC8',
    marginBottom: 12,
  },
  tipItem: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.6)',
    marginBottom: 8,
  },
  cameraPreview: {
    width: width - 80,
    height: width - 80,
    backgroundColor: 'transparent',
    borderRadius: 20,
    borderWidth: 2,
    borderColor: 'rgba(255, 255, 255, 0.8)',
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
  },
  faceGuide: {
    width: '70%',
    height: '70%',
    alignItems: 'center',
    justifyContent: 'center',
  },
  faceCircle: {
    width: '100%',
    height: '100%',
    borderRadius: 1000,
    borderWidth: 3,
    borderColor: '#00FFC8',
    borderStyle: 'dashed',
  },
  cameraHint: {
    position: 'absolute',
    bottom: 20,
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.7)',
  },
  captureButton: {
    marginTop: 32,
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: '#00FFC8',
    alignItems: 'center',
    justifyContent: 'center',
  },
  captureButtonInner: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: '#FFFFFF',
    alignItems: 'center',
    justifyContent: 'center',
  },
  livenessHint: {
    marginTop: 16,
    fontSize: 12,
    color: 'rgba(255, 255, 255, 0.5)',
  },
  processingIcon: {
    marginBottom: 24,
  },
  processingTitle: {
    fontSize: 24,
    fontWeight: '700',
    color: '#FFFFFF',
    marginBottom: 8,
  },
  processingDescription: {
    fontSize: 16,
    color: 'rgba(255, 255, 255, 0.7)',
    textAlign: 'center',
    marginBottom: 32,
  },
  processingSteps: {
    gap: 16,
  },
  processingStep: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  processingStepActive: {
    opacity: 0.7,
  },
  processingStepText: {
    fontSize: 16,
    color: 'rgba(255, 255, 255, 0.8)',
  },
  loadingDot: {
    width: 20,
    height: 20,
    borderRadius: 10,
    backgroundColor: '#00FFC8',
    opacity: 0.6,
  },
  successIcon: {
    marginBottom: 16,
  },
  successTitle: {
    fontSize: 28,
    fontWeight: '700',
    color: '#00FFC8',
    marginBottom: 8,
  },
  resultScore: {
    fontSize: 20,
    fontWeight: '600',
    color: '#FFFFFF',
    marginBottom: 16,
  },
  successDescription: {
    fontSize: 16,
    color: 'rgba(255, 255, 255, 0.7)',
    textAlign: 'center',
    lineHeight: 26,
  },
  badgePreview: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginTop: 24,
    paddingVertical: 12,
    paddingHorizontal: 20,
    backgroundColor: 'transparent',
    borderRadius: 20,
    borderWidth: 2,
    borderColor: '#00FFC8',
  },
  badgeText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#00FFC8',
  },
  failIcon: {
    marginBottom: 16,
  },
  failTitle: {
    fontSize: 28,
    fontWeight: '700',
    color: '#FF6B6B',
    marginBottom: 8,
  },
  failDescription: {
    fontSize: 16,
    color: 'rgba(255, 255, 255, 0.7)',
    textAlign: 'center',
    lineHeight: 26,
  },
  retryButton: {
    marginTop: 32,
    paddingVertical: 16,
    paddingHorizontal: 48,
    borderRadius: 30,
    backgroundColor: 'transparent',
    borderWidth: 2,
    borderColor: 'rgba(255, 255, 255, 0.8)',
  },
  retryButtonText: {
    fontSize: 16,
    color: '#FFFFFF',
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
});
