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
  ScrollView,
  Image,
} from 'react-native';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';

const { width, height } = Dimensions.get('window');

interface Question {
  id: string;
  text: string;
  category: string;
  type: 'text' | 'choice' | 'scale';
  options?: string[];
}

// Sample questions from database (will be replaced with API call)
const INITIAL_QUESTIONS: Question[] = [
  {
    id: 'marriage_when',
    text: '결혼은 언제 하고 싶으세요?',
    category: '결혼',
    type: 'choice',
    options: ['1년 이내', '1-2년 이내', '2-3년 이내', '3-5년 이내', '급하지 않음 (5년 이상)'],
  },
  {
    id: 'children_want',
    text: '자녀를 원하시나요?',
    category: '결혼',
    type: 'choice',
    options: ['네, 반드시 갖고 싶어요', '네, 가능하면 갖고 싶어요', '아니요, 원하지 않아요'],
  },
  {
    id: 'parents_live',
    text: '결혼 후 부모님과 동거할 의향이 있으세요?',
    category: '가족',
    type: 'choice',
    options: ['네, 처음부터 같이 살고 싶어요', '부모님 건강이 안 좋아지시면 모실 의향 있어요', '아니요, 따로 살고 싶어요'],
  },
  {
    id: 'finance_manage',
    text: '결혼 후 가계 재정은 어떻게 관리하고 싶으세요?',
    category: '재정',
    type: 'choice',
    options: ['완전 공동 관리 (모든 수입 합쳐서)', '공동 관리 + 개인 용돈 분리', '수입 비율에 따라 생활비 분담', '완전 분리 (각자 관리)'],
  },
  {
    id: 'dual_income',
    text: '맞벌이에 대해 어떻게 생각하세요?',
    category: '직장',
    type: 'choice',
    options: ['맞벌이 필수 (경제적으로 필요)', '맞벌이 선호 (배우자도 일했으면)', '외벌이 선호 (한 명이 집안일 전담)', '둘 다 괜찮음 (상대 선택 존중)'],
  },
];

/**
 * AI Avatar Question Screen
 * 
 * The avatar asks adaptive questions and collects user responses
 * Voice input available for convenience
 */
export default function QuestionsScreen() {
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [textAnswer, setTextAnswer] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(true);
  
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const pulseAnim = useRef(new Animated.Value(1)).current;

  const currentQuestion = INITIAL_QUESTIONS[currentQuestionIndex];
  const progress = (currentQuestionIndex + 1) / INITIAL_QUESTIONS.length;


  useEffect(() => {
    // Animate question entrance
    fadeAnim.setValue(0);
    Animated.timing(fadeAnim, {
      toValue: 1,
      duration: 500,
      useNativeDriver: true,
    }).start();

    // Simulate TTS speaking
    setIsSpeaking(true);
    const timer = setTimeout(() => setIsSpeaking(false), 2000);
    
    return () => clearTimeout(timer);
  }, [currentQuestionIndex]);

  useEffect(() => {
    // Aurora pulse animation - faster when speaking
    const duration = isSpeaking ? 800 : 2000;
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, {
          toValue: isSpeaking ? 1.2 : 1.1,
          duration,
          useNativeDriver: true,
        }),
        Animated.timing(pulseAnim, {
          toValue: 1,
          duration,
          useNativeDriver: true,
        }),
      ])
    ).start();
  }, [isSpeaking]);

  const handleChoiceSelect = (option: string) => {
    setAnswers((prev) => ({ ...prev, [currentQuestion.id]: option }));
    
    // Move to next question
    setTimeout(() => {
      if (currentQuestionIndex < INITIAL_QUESTIONS.length - 1) {
        setCurrentQuestionIndex((prev) => prev + 1);
      } else {
        // All questions answered
        router.push('/(onboarding)/face-verification');
      }
    }, 300);
  };

  const handleVoiceInput = () => {
    setIsListening(!isListening);
    // TODO: Implement actual voice recognition
  };

  const handleNext = () => {
    if (textAnswer.trim()) {
      setAnswers((prev) => ({ ...prev, [currentQuestion.id]: textAnswer }));
      setTextAnswer('');
      
      if (currentQuestionIndex < INITIAL_QUESTIONS.length - 1) {
        setCurrentQuestionIndex((prev) => prev + 1);
      } else {
        router.push('/(onboarding)/face-verification');
      }
    }
  };

  const handleGoBack = () => {
    if (currentQuestionIndex > 0) {
      // Go back to previous question
      setCurrentQuestionIndex(prev => prev - 1);
    } else {
      // Go back to previous screen
      router.back();
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      {/* Back Button */}
      <TouchableOpacity
        style={styles.backButton}
        onPress={handleGoBack}
        activeOpacity={0.7}
      >
        <Ionicons name="chevron-back" size={24} color="#4FD1C7" />
      </TouchableOpacity>

      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
      >
        {/* Progress Bar */}
        <View style={styles.progressBar}>
          <View style={[styles.progressFill, { width: `${progress * 100}%` }]} />
        </View>
        <Text style={styles.progressText}>
          {currentQuestionIndex + 1} / {INITIAL_QUESTIONS.length}
        </Text>

        {/* Avatar Section */}
        <View style={styles.avatarSection}>
          <Animated.View
            style={[
              styles.avatarContainer,
              { 
                transform: [{ scale: pulseAnim }] 
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

        {/* Question */}
        <Animated.View style={[styles.questionContainer, { opacity: fadeAnim }]}>
          <Text style={styles.categoryLabel}>{getCategoryLabel(currentQuestion.category)}</Text>
          <Text style={styles.questionText}>{currentQuestion.text}</Text>
        </Animated.View>

        {/* Answer Options */}
        {currentQuestion.type === 'choice' && currentQuestion.options && (
          <Animated.View style={[styles.optionsContainer, { opacity: fadeAnim }]}>
            {currentQuestion.options.map((option, index) => (
              <TouchableOpacity
                key={index}
                style={[
                  styles.optionButton,
                  answers[currentQuestion.id] === option && styles.optionSelected,
                ]}
                onPress={() => handleChoiceSelect(option)}
                activeOpacity={0.7}
              >
                <Text
                  style={[
                    styles.optionText,
                    answers[currentQuestion.id] === option && styles.optionTextSelected,
                  ]}
                >
                  {option}
                </Text>
              </TouchableOpacity>
            ))}
          </Animated.View>
        )}

        {/* Text Input */}
        {currentQuestion.type === 'text' && (
          <View style={styles.inputContainer}>
            <TextInput
              style={styles.textInput}
              value={textAnswer}
              onChangeText={setTextAnswer}
              placeholder="답변을 입력해주세요..."
              placeholderTextColor="rgba(255, 255, 255, 0.4)"
              multiline
            />
            <TouchableOpacity
              style={styles.sendButton}
              onPress={handleNext}
              disabled={!textAnswer.trim()}
            >
              <Ionicons
                name="send"
                size={24}
                color={textAnswer.trim() ? '#4FD1C7' : 'rgba(255, 255, 255, 0.3)'}
              />
            </TouchableOpacity>
          </View>
        )}

        {/* Voice Input Button */}
        <TouchableOpacity
          style={[styles.voiceButton, isListening && styles.voiceButtonActive]}
          onPress={handleVoiceInput}
          activeOpacity={0.7}
        >
          <Ionicons
            name={isListening ? 'mic' : 'mic-outline'}
            size={28}
            color={isListening ? '#FF6B6B' : '#FFFFFF'}
          />
          <Text style={styles.voiceButtonText}>
            {isListening ? '듣는 중...' : '음성으로 답변하기'}
          </Text>
        </TouchableOpacity>
      </ScrollView>

    </KeyboardAvoidingView>
  );
}

function getCategoryLabel(category: string): string {
  const labels: Record<string, string> = {
    marriage: '💍 결혼 계획',
    values: '💎 가치관',
    family: '👨‍👩‍👧 가족',
    finance: '💰 경제',
    lifestyle: '🏃 라이프스타일',
  };
  return labels[category] || category;
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000000',
  },
  backButton: {
    position: 'absolute',
    top: 60,
    left: 20,
    zIndex: 10,
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(79, 209, 199, 0.1)',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(79, 209, 199, 0.2)',
  },
  scrollContent: {
    flexGrow: 1,
    paddingTop: 60,
    paddingBottom: 40,
  },
  progressBar: {
    height: 4,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    marginHorizontal: 24,
    borderRadius: 2,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    backgroundColor: '#4FD1C7',
    borderRadius: 2,
  },
  progressText: {
    fontSize: 12,
    color: 'rgba(255, 255, 255, 0.5)',
    textAlign: 'center',
    marginTop: 8,
  },
  avatarSection: {
    height: height * 0.25,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 24,
  },
  avatarContainer: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  imageContainer: {
    width: 200,
    height: 200,
    borderRadius: 100,
    overflow: 'hidden',
    backgroundColor: 'transparent',
    shadowColor: 'rgba(79, 209, 199, 0.8)',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.6,
    shadowRadius: 20,
    elevation: 8,
  },
  managerImage: {
    width: 200,
    height: 200,
  },
  speakingIndicatorOverlay: {
    position: 'absolute',
    width: 220,
    height: 220,
    borderRadius: 110,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pulseRing: {
    position: 'absolute',
    width: 240,
    height: 240,
    borderRadius: 120,
    borderWidth: 3,
    borderColor: 'rgba(79, 209, 199, 0.6)',
    backgroundColor: 'transparent',
  },
  questionContainer: {
    paddingHorizontal: 24,
    marginBottom: 24,
  },
  categoryLabel: {
    fontSize: 14,
    color: '#4FD1C7',
    marginBottom: 8,
  },
  questionText: {
    fontSize: 24,
    fontWeight: '600',
    color: '#FFFFFF',
    lineHeight: 36,
  },
  optionsContainer: {
    paddingHorizontal: 24,
    gap: 12,
  },
  optionButton: {
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 16,
    paddingVertical: 18,
    paddingHorizontal: 24,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
  },
  optionSelected: {
    backgroundColor: 'rgba(79, 209, 199, 0.15)',
    borderColor: '#4FD1C7',
  },
  optionText: {
    fontSize: 16,
    color: '#FFFFFF',
    textAlign: 'center',
  },
  optionTextSelected: {
    color: '#4FD1C7',
    fontWeight: '600',
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    marginHorizontal: 24,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  textInput: {
    flex: 1,
    fontSize: 16,
    color: '#FFFFFF',
    maxHeight: 120,
  },
  sendButton: {
    marginLeft: 12,
    padding: 4,
  },
  voiceButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginHorizontal: 24,
    marginTop: 24,
    paddingVertical: 16,
    borderRadius: 30,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.2)',
    gap: 8,
  },
  voiceButtonActive: {
    backgroundColor: 'rgba(255, 107, 107, 0.15)',
    borderColor: '#FF6B6B',
  },
  voiceButtonText: {
    fontSize: 16,
    color: 'rgba(255, 255, 255, 0.8)',
  },
});
