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
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { StatusBar } from 'expo-status-bar';
import * as Speech from 'expo-speech';

const { width, height } = Dimensions.get('window');

/**
 * FLIO Manager Introduction Screen
 * Manager welcomes user and explains the question process
 */
export default function AvatarIntroScreen() {
  const params = useLocalSearchParams();
  
  // User identity data from phone verification
  const userId = params.userId as string;
  const userName = params.name as string;
  const userAge = params.age as string;
  const userGender = params.gender as string;
  
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isVoiceMode, setIsVoiceMode] = useState(false);
  
  // Animations
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const scaleAnim = useRef(new Animated.Value(0.8)).current;
  const managerBounceAnim = useRef(new Animated.Value(0)).current;

  const introMessage = {
    text: '나에게 딱 맞는 인연을 찾기위한 프로필 작성 시작합니다',
    subtitle: '음성도움이 필요하면 음성모드를 눌러주세요',
  };

  // Process steps to show
  const processSteps = [
    { icon: 'person-outline', text: '프로필작성', active: true },
    { icon: 'shield-checkmark-outline', text: '얼굴인증', active: false },
    { icon: 'heart', text: '매칭시작', active: false }
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

  const playIntroSpeech = async () => {
    try {
      setIsSpeaking(true);
      await Speech.speak(introMessage.text, {
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
      playIntroSpeech();
    }
  };

  const handleNext = () => {
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
  };

  const handleGoBack = () => {
    router.back();
  };

  return (
    <View style={styles.container}>
      <StatusBar style="light" backgroundColor="transparent" translucent />
      
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


      {/* Process Steps */}
      <View style={styles.processSteps}>
        {processSteps.map((step, index) => (
          <View key={index} style={styles.processStep}>
            <View style={[styles.stepIcon, step.active && styles.stepIconActive]}>
              <Ionicons 
                name={step.icon as any} 
                size={20} 
                color={step.active ? "#FFFFFF" : "rgba(255, 255, 255, 0.5)"} 
              />
            </View>
            <Text style={[styles.stepText, step.active && styles.stepTextActive]}>
              {step.text}
            </Text>
            {index < processSteps.length - 1 && (
              <View style={styles.stepConnector} />
            )}
          </View>
        ))}
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
            <Image
              source={require('../../assets/images/flio-manager-intro.png')}
              style={styles.managerImage}
              resizeMode="cover"
            />
          </Animated.View>
        </View>

        {/* Introduction Text */}
        <View style={styles.textContainer}>
          <Text style={styles.introText}>{introMessage.text}</Text>
          <Text style={styles.subtitleText}>{introMessage.subtitle}</Text>
        </View>

        {/* Action Buttons */}
        <View style={styles.buttonContainer}>
          <TouchableOpacity
            style={styles.voiceActionButton}
            onPress={toggleVoiceMode}
            activeOpacity={0.8}
          >
            <Ionicons name="volume-high" size={20} color="#FFFFFF" />
            <Text style={styles.voiceActionText}>음성모드</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.nextButton}
            onPress={handleNext}
            activeOpacity={0.8}
          >
            <Text style={styles.nextButtonText}>다음</Text>
            <Ionicons name="arrow-forward" size={20} color="#FFFFFF" />
          </TouchableOpacity>
        </View>
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
  titleHeader: {
    position: 'absolute',
    top: 60,
    left: 0,
    right: 0,
    zIndex: 5,
    paddingVertical: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  titleText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#4FD1C7',
    textAlign: 'center',
    textShadowColor: 'rgba(0, 0, 0, 0.3)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 2,
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
  processSteps: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: 120,
    paddingHorizontal: 40,
    marginBottom: 40,
    position: 'relative',
  },
  processStep: {
    alignItems: 'center',
    flex: 1,
    position: 'relative',
  },
  stepIcon: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 8,
  },
  stepIconActive: {
    backgroundColor: '#4FD1C7',
  },
  stepText: {
    fontSize: 12,
    color: 'rgba(255, 255, 255, 0.7)',
    fontWeight: '600',
    textAlign: 'center',
  },
  stepTextActive: {
    color: '#FFFFFF',
  },
  stepConnector: {
    position: 'absolute',
    top: 20,
    left: '60%',
    width: '80%',
    height: 2,
    backgroundColor: 'rgba(255, 255, 255, 0.3)',
    zIndex: -1,
  },
  content: {
    flex: 1,
    paddingHorizontal: 24,
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  managerSection: {
    alignItems: 'center',
    marginBottom: 40,
  },
  managerImageContainer: {
    width: width * 0.5,
    height: width * 0.5,
    borderRadius: (width * 0.5) / 2,
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
  },
  managerImage: {
    width: width * 0.5,
    height: width * 0.5,
    borderRadius: (width * 0.5) / 2,
  },
  textContainer: {
    alignItems: 'center',
    marginBottom: 60,
  },
  introText: {
    fontSize: 24,
    fontWeight: '700',
    color: '#FFFFFF',
    textAlign: 'center',
    lineHeight: 34,
    marginBottom: 16,
    textShadowColor: 'rgba(0, 0, 0, 0.3)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 2,
  },
  subtitleText: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.8)',
    textAlign: 'center',
    lineHeight: 20,
    fontWeight: '500',
  },
  buttonContainer: {
    flexDirection: 'row',
    gap: 12,
    width: '100%',
    paddingBottom: 40,
  },
  voiceActionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    flex: 1,
    paddingVertical: 18,
    borderRadius: 30,
    backgroundColor: 'rgba(255, 255, 255, 0.15)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.3)',
    gap: 8,
  },
  voiceActionText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  nextButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    flex: 1,
    paddingVertical: 18,
    borderRadius: 30,
    backgroundColor: 'rgba(79, 209, 199, 0.9)',
    gap: 8,
    shadowColor: 'rgba(0, 0, 0, 0.2)',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  nextButtonText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#FFFFFF',
    textShadowColor: 'rgba(47, 125, 122, 0.8)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 2,
  },
});
