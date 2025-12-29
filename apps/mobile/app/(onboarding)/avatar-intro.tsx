import { useState, useRef, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Dimensions,
  Animated,
  Easing,
  ImageBackground,
  Image,
} from 'react-native';
import { router } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { StatusBar } from 'expo-status-bar';
import * as Speech from 'expo-speech';

const { width, height } = Dimensions.get('window');

/**
 * Avatar Introduction Screen - Ocean Theme
 * 
 * AI 매니저가 음성으로 사용자에게 안내하는 화면
 * 
 * Features:
 * - AI Avatar with speaking animation
 * - Text-to-Speech for voice guidance
 * - Ocean theme consistent with landing page
 * - Step-by-step process explanation
 */
export default function AvatarIntroScreen() {
  const [currentMessage, setCurrentMessage] = useState(0);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [hasUserInteracted, setHasUserInteracted] = useState(false);
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const speakingAnim = useRef(new Animated.Value(1)).current;
  const waveAnim = useRef(new Animated.Value(0)).current;

  const messages = [
    {
      text: '안녕하세요? 우리 함께 프로필을 만들어볼까요?',
      subtitle: '혹시 음성으로 진행하고 싶으시면 음성모드로 전환해 주세요',
    },
    {
      text: '아니면 다음을 눌러 프로필 작성을 진행해 보아요!',
      subtitle: '✨ 약 5분 정도 걸려요',
    },
  ];

  // Process steps to show
  const processSteps = [
    { icon: 'person-outline', text: '프로필작성', active: true },
    { icon: 'shield-checkmark-outline', text: '본인인증', active: false },
    { icon: 'heart-outline', text: '만남시작', active: false },
  ];

  // Speaking animation
  useEffect(() => {
    let animation: Animated.CompositeAnimation;
    
    if (isSpeaking) {
      animation = Animated.loop(
        Animated.sequence([
          Animated.timing(speakingAnim, {
            toValue: 1.15,
            duration: 200,
            easing: Easing.inOut(Easing.ease),
            useNativeDriver: true,
          }),
          Animated.timing(speakingAnim, {
            toValue: 0.95,
            duration: 200,
            easing: Easing.inOut(Easing.ease),
            useNativeDriver: true,
          }),
        ])
      );
      animation.start();
    } else {
      speakingAnim.setValue(1);
    }

    return () => animation?.stop();
  }, [isSpeaking]);

  useEffect(() => {
    // Fade in animation
    Animated.timing(fadeAnim, {
      toValue: 1,
      duration: 800,
      useNativeDriver: true,
    }).start();

    // Pulsing effect
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, {
          toValue: 1.08,
          duration: 2500,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
        Animated.timing(pulseAnim, {
          toValue: 1,
          duration: 2500,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
      ])
    ).start();

    // Wave animation
    Animated.loop(
      Animated.timing(waveAnim, {
        toValue: 1,
        duration: 3000,
        easing: Easing.linear,
        useNativeDriver: true,
      })
    ).start();
  }, []);

  // Text-to-Speech function
  const speakMessage = useCallback((text: string) => {
    setIsSpeaking(true);
    
    Speech.speak(text, {
      language: 'ko-KR',
      pitch: 1.1,
      rate: 0.9,
      onDone: () => setIsSpeaking(false),
      onError: () => setIsSpeaking(false),
    });
  }, []);

  // Handle voice mode - speak introduction then navigate to profile creation
  const handlePlayVoice = () => {
    setHasUserInteracted(true);
    setIsSpeaking(true);
    
    const introMessage = '안녕하세요 저는 FLIO 매니저입니다 지금부터 저와 함께 프로필을 만들어 보아요';
    
    Speech.speak(introMessage, {
      language: 'ko-KR',
      pitch: 1.1,
      rate: 0.9,
      onDone: () => {
        setIsSpeaking(false);
        router.push('/(onboarding)/questions');
      },
      onError: () => {
        setIsSpeaking(false);
        router.push('/(onboarding)/questions');
      },
    });
  };

  // Navigate directly to questions page
  const handleNext = () => {
    Speech.stop();
    setIsSpeaking(false);
    router.push('/(onboarding)/questions');
  };

  const handleStart = () => {
    Speech.stop();
    router.push('/(onboarding)/questions');
  };

  const handleGoBack = () => {
    Speech.stop();
    router.back();
  };

  const waveTranslate = waveAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [0, -20],
  });

  return (
    <View style={styles.container}>
      <StatusBar style="light" />
      
      {/* Clean Ocean Gradient Background */}
      <LinearGradient
        colors={['#2E7D7A', '#4FD1C7', '#7EDDD9', '#B0E7E4']}
        locations={[0, 0.4, 0.7, 1]}
        style={styles.backgroundGradient}
      />

      {/* Top Navigation Bar */}
      <View style={styles.topNavigationContainer}>
        {/* Back Button */}
        <TouchableOpacity
          style={styles.backButton}
          onPress={handleGoBack}
          activeOpacity={0.7}
        >
          <Ionicons name="chevron-back" size={24} color="#FFFFFF" />
        </TouchableOpacity>

        {/* Progress Steps - Next to Back Button */}
        <View style={styles.processContainer}>
          {processSteps.map((step, index) => (
            <View key={index} style={styles.processStep}>
              <View style={[
                styles.processIcon,
                step.active && styles.processIconActive
              ]}>
                <Ionicons 
                  name={step.icon as any} 
                  size={16} 
                  color={step.active ? '#FFFFFF' : 'rgba(255, 255, 255, 0.6)'} 
                />
              </View>
              <Text style={[
                styles.processText,
                step.active && styles.processTextActive
              ]}>
                {step.text}
              </Text>
              {index < processSteps.length - 1 && (
                <View style={styles.processLine} />
              )}
            </View>
          ))}
        </View>
      </View>


      {/* Centered Content */}
      <View style={styles.centeredContent}>
        {/* Natural Avatar */}
        <View style={styles.avatarSection}>
          <Animated.View
            style={[
              styles.avatarContainer,
              { 
                transform: [
                  { scale: Animated.multiply(pulseAnim, speakingAnim) }
                ] 
              },
            ]}
          >
            <View style={styles.imageContainer}>
              <Image 
                source={require('./intro-manger.png')}
                style={styles.managerImage}
                resizeMode="cover"
              />
            </View>
            {isSpeaking && (
              <View style={styles.speakingIndicatorOverlay}>
                <View style={styles.pulseRing} />
              </View>
            )}
          </Animated.View>
        </View>

        {/* Natural Message */}
        <Animated.View style={[styles.messageContainer, { opacity: fadeAnim }]}>
          <Text style={styles.messageText}>{messages[currentMessage].text}</Text>
          <Text style={styles.messageSubtitle}>{messages[currentMessage].subtitle}</Text>
        </Animated.View>
      </View>

      {/* Modern Navigation */}
      <View style={styles.navigationContainer}>

        {/* Modern Action Buttons */}
        <View style={styles.buttonContainer}>
          {currentMessage < messages.length - 1 ? (
            <>
              <TouchableOpacity 
                style={styles.naturalVoiceButton}
                onPress={handlePlayVoice}
                activeOpacity={0.8}
              >
                <Ionicons name="volume-high" size={20} color="#FFFFFF" />
                <Text style={styles.naturalVoiceButtonText}>음성모드</Text>
              </TouchableOpacity>
              <TouchableOpacity 
                style={styles.naturalNextButton}
                onPress={handleNext}
                activeOpacity={0.8}
              >
                <Text style={styles.naturalNextButtonText}>다음</Text>
                <Ionicons name="arrow-forward" size={18} color="#FFFFFF" />
              </TouchableOpacity>
            </>
          ) : (
            <TouchableOpacity onPress={handleStart} activeOpacity={0.9} style={styles.fullWidthButton}>
              <View style={styles.naturalStartButton}>
                <Ionicons name="heart" size={20} color="#FFFFFF" />
                <Text style={styles.naturalStartButtonText}>프로필 작성 시작</Text>
              </View>
            </TouchableOpacity>
          )}
        </View>
      </View>
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
  topNavigationContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingTop: 60,
    paddingHorizontal: 20,
    paddingBottom: 20,
    gap: 12,
  },
  backButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: 'rgba(47, 125, 122, 0.4)',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(79, 209, 199, 0.6)',
  },
  processContainer: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'flex-start',
    gap: 4,
    paddingRight: 20,
  },
  processStep: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 6,
  },
  processIcon: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: 'rgba(255, 255, 255, 0.3)',
  },
  processIconActive: {
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    borderColor: 'rgba(255, 255, 255, 0.9)',
  },
  processText: {
    fontSize: 11,
    color: 'rgba(255, 255, 255, 0.9)',
    marginLeft: 3,
    fontWeight: '600',
  },
  processTextActive: {
    color: '#FFFFFF',
    fontWeight: '700',
  },
  processLine: {
    width: 12,
    height: 3,
    backgroundColor: 'rgba(255, 255, 255, 0.5)',
    marginHorizontal: 3,
    borderRadius: 1.5,
  },
  centeredContent: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 24,
  },
  avatarSection: {
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 24,
  },
  avatarContainer: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  imageContainer: {
    width: 280,
    height: 280,
    borderRadius: 140,
    overflow: 'hidden',
    backgroundColor: 'transparent',
    shadowColor: 'rgba(0, 0, 0, 0.2)',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  managerImage: {
    width: 280,
    height: 280,
  },
  avatarText: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#ffffff',
    letterSpacing: 1,
  },
  speakingIndicatorOverlay: {
    position: 'absolute',
    width: 200,
    height: 200,
    borderRadius: 100,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pulseRing: {
    position: 'absolute',
    width: 220,
    height: 220,
    borderRadius: 110,
    borderWidth: 3,
    borderColor: 'rgba(72, 202, 228, 0.6)',
    backgroundColor: 'transparent',
  },
  speakingIndicator: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: 3,
    marginTop: 16,
  },
  soundBar: {
    width: 4,
    backgroundColor: '#48CAE4',
    borderRadius: 2,
    opacity: 0.8,
  },
  messageContainer: {
    paddingVertical: 24,
    paddingHorizontal: 28,
    marginTop: 20,
  },
  messageText: {
    fontSize: 22,
    color: '#FFFFFF',
    textAlign: 'center',
    lineHeight: 30,
    letterSpacing: 0.3,
    fontWeight: '700',
    textShadowColor: 'rgba(0, 0, 0, 0.4)',
    textShadowOffset: { width: 0, height: 2 },
    textShadowRadius: 4,
  },
  messageSubtitle: {
    fontSize: 16,
    color: '#FFFFFF',
    textAlign: 'center',
    marginTop: 12,
    lineHeight: 22,
    fontWeight: '600',
    textShadowColor: 'rgba(0, 0, 0, 0.4)',
    textShadowOffset: { width: 0, height: 2 },
    textShadowRadius: 4,
  },
  navigationContainer: {
    paddingHorizontal: 24,
    paddingBottom: 50,
    paddingTop: 30,
  },
  buttonContainer: {
    flexDirection: 'row',
    gap: 12,
    justifyContent: 'space-between',
  },
  naturalVoiceButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 16,
    borderRadius: 25,
    gap: 8,
    borderWidth: 2,
    borderColor: '#4FD1C7',
    backgroundColor: 'rgba(47, 125, 122, 0.2)',
  },
  naturalVoiceButtonText: {
    fontSize: 16,
    color: '#4FD1C7',
    fontWeight: '600',
    textShadowColor: 'rgba(47, 125, 122, 0.8)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 2,
  },
  naturalNextButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 16,
    backgroundColor: 'rgba(79, 209, 199, 0.8)',
    borderRadius: 25,
    gap: 8,
  },
  naturalNextButtonText: {
    fontSize: 16,
    color: '#FFFFFF',
    fontWeight: '700',
    textShadowColor: 'rgba(47, 125, 122, 0.8)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 2,
  },
  fullWidthButton: {
    width: '100%',
  },
  naturalStartButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 18,
    borderRadius: 25,
    gap: 10,
    backgroundColor: 'rgba(79, 209, 199, 0.8)',
  },
  naturalStartButtonText: {
    fontSize: 18,
    fontWeight: '700',
    color: '#FFFFFF',
    textShadowColor: 'rgba(47, 125, 122, 0.8)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 2,
  },
});
