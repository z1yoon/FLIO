/**
 * FLIO Manager Introduction Screen
 * Manager welcomes user and explains the question process
 */

import { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Dimensions,
  Animated,
  Image,
} from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { StatusBar } from 'expo-status-bar';
import * as Speech from 'expo-speech';

const { width, height } = Dimensions.get('window');

/**
 * Manager Introduction Screen
 * 
 * Shows animated manager character introducing the question process
 * Explains how AI will generate personalized questions
 */
export default function ManagerIntroScreen() {
  const params = useLocalSearchParams();
  
  // User identity data from phone verification
  const userId = params.userId as string;
  const userName = params.name as string;
  const userAge = params.age as string;
  const userGender = params.gender as string;
  
  const [currentStep, setCurrentStep] = useState(0);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isVoiceMode, setIsVoiceMode] = useState(false);
  
  // Animations
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const scaleAnim = useRef(new Animated.Value(0.8)).current;
  const managerBounceAnim = useRef(new Animated.Value(0)).current;
  const textSlideAnim = useRef(new Animated.Value(50)).current;

  // Manager introduction steps
  const introSteps = [
    {
      text: `안녕하세요, ${userName}님! 👋\n저는 FLIO의 AI 매칭 매니저입니다.`,
      action: '다음'
    },
    {
      text: `${userName}님의 완벽한 인연을 찾기 위해\n몇 가지 질문을 드릴게요.`,
      action: '다음'
    },
    {
      text: `AI가 ${userName}님의 답변을 분석해서\n48개의 맞춤형 질문을 준비했습니다.`,
      action: '다음'
    },
    {
      text: `솔직하고 자연스럽게 답변해주세요.\n더 정확한 매칭이 가능해집니다! ✨`,
      action: '질문 시작하기'
    }
  ];

  useEffect(() => {
    // Initial entrance animation
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 800,
        useNativeDriver: true,
      }),
      Animated.spring(scaleAnim, {
        toValue: 1,
        friction: 6,
        useNativeDriver: true,
      }),
    ]).start();

    // Manager bounce animation (continuous)
    const bounceAnimation = Animated.loop(
      Animated.sequence([
        Animated.timing(managerBounceAnim, {
          toValue: -8,
          duration: 1500,
          useNativeDriver: true,
        }),
        Animated.timing(managerBounceAnim, {
          toValue: 0,
          duration: 1500,
          useNativeDriver: true,
        }),
      ])
    );
    bounceAnimation.start();

    return () => bounceAnimation.stop();
  }, []);

  useEffect(() => {
    // Text slide animation when step changes
    textSlideAnim.setValue(50);
    Animated.timing(textSlideAnim, {
      toValue: 0,
      duration: 500,
      useNativeDriver: true,
    }).start();

    // Auto-play speech in voice mode
    if (isVoiceMode) {
      playCurrentStepSpeech();
    }
  }, [currentStep]);

  const playCurrentStepSpeech = async () => {
    const currentText = introSteps[currentStep].text;
    
    try {
      setIsSpeaking(true);
      await Speech.speak(currentText, {
        language: 'ko-KR',
        pitch: 1.0,
        rate: 0.85,
        onDone: () => setIsSpeaking(false),
        onError: () => setIsSpeaking(false),
      });
    } catch (error) {
      console.log('TTS Error:', error);
      setIsSpeaking(false);
    }
  };

  const toggleVoiceMode = () => {
    if (isSpeaking) {
      Speech.stop();
      setIsSpeaking(false);
    }
    
    const newVoiceMode = !isVoiceMode;
    setIsVoiceMode(newVoiceMode);
    
    if (newVoiceMode) {
      playCurrentStepSpeech();
    }
  };

  const toggleSpeech = () => {
    if (isSpeaking) {
      Speech.stop();
      setIsSpeaking(false);
    } else {
      playCurrentStepSpeech();
    }
  };

  const handleNext = () => {
    if (currentStep < introSteps.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      // Navigate to questions with all user data
      const questionParams = new URLSearchParams({
        userId: userId,
        name: userName,
        age: userAge,
        gender: userGender,
        birthDate: params.birthDate as string,
        phone: params.phone as string,
        ci: params.ci as string,
        di: params.di as string
      });
      router.push(`/(onboarding)/questions?${questionParams.toString()}`);
    }
  };

  const handleGoBack = () => {
    router.back();
  };

  const currentIntro = introSteps[currentStep];

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

      {/* Voice Controls */}
      <View style={styles.voiceControls}>
        <TouchableOpacity
          style={[styles.voiceButton, isVoiceMode && styles.voiceButtonActive]}
          onPress={toggleVoiceMode}
          activeOpacity={0.7}
        >
          <Ionicons 
            name={isVoiceMode ? "volume-high" : "volume-mute"} 
            size={20} 
            color={isVoiceMode ? "#4FD1C7" : "#FFFFFF"} 
          />
        </TouchableOpacity>
        
        <TouchableOpacity
          style={[styles.voiceButton, isSpeaking && styles.voiceButtonActive]}
          onPress={toggleSpeech}
          activeOpacity={0.7}
        >
          <Ionicons 
            name={isSpeaking ? "pause" : "play"} 
            size={20} 
            color={isSpeaking ? "#4FD1C7" : "#FFFFFF"} 
          />
        </TouchableOpacity>
      </View>

      <Animated.View
        style={[
          styles.content,
          {
            opacity: fadeAnim,
            transform: [{ scale: scaleAnim }],
          },
        ]}
      >
        {/* Manager Character with Animation */}
        <View style={styles.managerSection}>
          <Animated.View
            style={[
              styles.managerImageContainer,
              {
                transform: [{ translateY: managerBounceAnim }],
              },
            ]}
          >
            <View style={styles.managerPlaceholder}>
              <Ionicons name="person-circle" size={120} color="#4FD1C7" />
              <Text style={styles.managerLabel}>FLIO Manager</Text>
            </View>
          </Animated.View>
        </View>

        {/* Progress Indicator */}
        <View style={styles.progressContainer}>
          {introSteps.map((_, index) => (
            <View
              key={index}
              style={[
                styles.progressDot,
                index <= currentStep && styles.progressDotActive,
              ]}
            />
          ))}
        </View>

        {/* Introduction Text */}
        <Animated.View
          style={[
            styles.textContainer,
            {
              transform: [{ translateY: textSlideAnim }],
            },
          ]}
        >
          <Text style={styles.introText}>{currentIntro.text}</Text>
        </Animated.View>

        {/* Action Button */}
        <TouchableOpacity
          style={styles.actionButton}
          onPress={handleNext}
          activeOpacity={0.8}
        >
          <LinearGradient
            colors={['#4FD1C7', '#2E7D7A']}
            style={styles.actionButtonGradient}
          >
            <Text style={styles.actionButtonText}>{currentIntro.action}</Text>
            {currentStep === introSteps.length - 1 && (
              <Ionicons name="arrow-forward" size={20} color="#FFFFFF" />
            )}
          </LinearGradient>
        </TouchableOpacity>

        {/* Skip Option */}
        {currentStep < introSteps.length - 1 && (
          <TouchableOpacity
            style={styles.skipButton}
            onPress={() => setCurrentStep(introSteps.length - 1)}
          >
            <Text style={styles.skipText}>건너뛰기</Text>
          </TouchableOpacity>
        )}
      </Animated.View>
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
  content: {
    flex: 1,
    paddingHorizontal: 24,
    paddingTop: 120,
    alignItems: 'center',
  },
  managerSection: {
    height: height * 0.35,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 20,
  },
  managerImageContainer: {
    width: width * 0.6,
    height: width * 0.6,
    justifyContent: 'center',
    alignItems: 'center',
  },
  managerPlaceholder: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  managerLabel: {
    fontSize: 14,
    color: '#4FD1C7',
    fontWeight: '600',
    marginTop: 8,
    textShadowColor: 'rgba(0, 0, 0, 0.3)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 2,
  },
  progressContainer: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 32,
  },
  progressDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: 'rgba(255, 255, 255, 0.3)',
  },
  progressDotActive: {
    backgroundColor: '#FFFFFF',
  },
  textContainer: {
    marginBottom: 40,
    minHeight: 80,
    justifyContent: 'center',
  },
  introText: {
    fontSize: 18,
    color: '#FFFFFF',
    textAlign: 'center',
    lineHeight: 28,
    fontWeight: '600',
    textShadowColor: 'rgba(0, 0, 0, 0.3)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 2,
  },
  actionButton: {
    width: '100%',
    marginBottom: 16,
  },
  actionButtonGradient: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 18,
    borderRadius: 30,
    gap: 8,
    shadowColor: 'rgba(0, 0, 0, 0.2)',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  actionButtonText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#FFFFFF',
    textShadowColor: 'rgba(47, 125, 122, 0.8)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 2,
  },
  skipButton: {
    paddingVertical: 12,
    paddingHorizontal: 24,
  },
  skipText: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.7)',
    textAlign: 'center',
    textDecorationLine: 'underline',
  },
  voiceControls: {
    position: 'absolute',
    top: 60,
    right: 20,
    flexDirection: 'row',
    gap: 8,
    zIndex: 10,
  },
  voiceButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: 'rgba(255, 255, 255, 0.15)',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.2)',
  },
  voiceButtonActive: {
    backgroundColor: 'rgba(79, 209, 199, 0.3)',
    borderColor: '#4FD1C7',
  },
});