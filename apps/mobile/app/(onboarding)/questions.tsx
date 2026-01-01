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
  Alert,
} from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { StatusBar } from 'expo-status-bar';
import { aiQuestionService, Question, UserContext, Answer } from '../../services/aiQuestionService';

const { width, height } = Dimensions.get('window');

// Generate unique user ID for this session
const generateUserId = () => `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

// Helper to create initial user context
const createUserContext = (userId: string, previousAnswers: Answer[] = []): UserContext => ({
  user_id: userId,
  previous_answers: previousAnswers,
  demographics: {
    // Can be populated from registration data
  },
});

/**
 * AI Question Screen
 * 
 * Presents adaptive questions and collects user responses
 * Uses AI backend for dynamic question generation with conditional logic
 */
export default function QuestionsScreen() {
  const params = useLocalSearchParams();
  const userId = params.userId as string;
  
  // Korean identity data from verification
  const userName = params.name as string;
  const userAge = params.age as string;
  const userGender = params.gender as string;
  
  // AI-driven state management
  const [questions, setQuestions] = useState<Question[]>([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [userContext, setUserContext] = useState<UserContext>(() => createUserContext(userId));
  const [isLoadingQuestion, setIsLoadingQuestion] = useState(true);
  const [textAnswer, setTextAnswer] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(true);
  
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const pulseAnim = useRef(new Animated.Value(1)).current;

  const currentQuestion = questions[currentQuestionIndex];
  const progress = questions.length > 0 ? (currentQuestionIndex + 1) / questions.length : 0;


  // Load initial questions from AI backend (only after phone verification)
  const loadInitialQuestions = async () => {
    try {
      setIsLoadingQuestion(true);
      
      // Check if user came from phone verification
      if (!params.userId) {
        console.log('⚠️ No phone verification - redirecting to phone verification');
        router.replace('/(onboarding)/phone-verification');
        return;
      }
      
      const initialQuestions = await aiQuestionService.getInitialQuestions();
      
      setQuestions(initialQuestions); // All 48 questions from backend
    } catch (error) {
      console.error('❌ Failed to load initial questions:', error);
      Alert.alert('연결 오류', 'AI 서비스 연결에 문제가 있습니다. 다시 시도해주세요.');
    } finally {
      setIsLoadingQuestion(false);
    }
  };

  // Simple sequential question progression
  const processAnswerAndGetNext = async (answer: string) => {
    if (!currentQuestion) return;

    try {
      setIsLoadingQuestion(true);

      // Store the answer
      const newAnswer: Answer = {
        question_id: currentQuestion.id,
        answer: answer,
        timestamp: new Date().toISOString(),
      };

      const updatedContext: UserContext = {
        ...userContext,
        previous_answers: [...userContext.previous_answers, newAnswer],
      };

      setUserContext(updatedContext);

      // Simple progression: go to next question in the array
      if (currentQuestionIndex < questions.length - 1) {
        // Move to next question
        setCurrentQuestionIndex(currentQuestionIndex + 1);
      } else {
        // All questions completed, go to face verification
        router.push('/(onboarding)/face-verification');
      }

    } catch (error) {
      console.error('Failed to process answer:', error);
      Alert.alert('오류', '답변 처리 중 문제가 발생했습니다.');
    } finally {
      setIsLoadingQuestion(false);
    }
  };

  // Initialize questions when component mounts
  useEffect(() => {
    loadInitialQuestions();
  }, []);


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

  const handleChoiceSelect = async (option: string) => {
    if (isLoadingQuestion) return;
    
    // Process the answer through AI service
    await processAnswerAndGetNext(option);
  };

  const handleVoiceInput = () => {
    setIsListening(!isListening);
    // TODO: Implement actual voice recognition
  };

  const handleNext = async () => {
    if (textAnswer.trim() && !isLoadingQuestion) {
      const answer = textAnswer.trim();
      setTextAnswer('');
      
      // Process the answer through AI service
      await processAnswerAndGetNext(answer);
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
    <View style={styles.container}>
      <StatusBar style="light" />
      
      {/* FLIO Ocean Gradient Background */}
      <LinearGradient
        colors={['#2E7D7A', '#4FD1C7', '#7EDDD9', '#B0E7E4']}
        locations={[0, 0.4, 0.7, 1]}
        style={styles.backgroundGradient}
      />

      <KeyboardAvoidingView
        style={styles.keyboardAvoidingView}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        {/* Back Button */}
        <TouchableOpacity
          style={styles.backButton}
          onPress={handleGoBack}
          activeOpacity={0.7}
        >
          <Ionicons name="chevron-back" size={24} color="#FFFFFF" />
        </TouchableOpacity>

      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
      >
        {/* Progress Bar */}
        <View style={styles.progressContainer}>
          <Text style={styles.progressText}>
            {currentQuestionIndex + 1} / {questions.length}
          </Text>
          <View style={styles.progressBar}>
            <View style={[styles.progressFill, { width: `${progress * 100}%` }]} />
          </View>
        </View>

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
                source={require('../../assets/images/flio-manager-question.png')}
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
          {currentQuestion ? (
            <>
              <Text style={styles.categoryLabel}>{getCategoryLabel(currentQuestion.category)}</Text>
              <Text style={styles.questionText}>{currentQuestion.text}</Text>
            </>
          ) : isLoadingQuestion ? (
            <>
              <Text style={styles.categoryLabel}>AI 질문 생성 중...</Text>
              <Text style={styles.questionText}>다음 질문을 준비하고 있습니다</Text>
            </>
          ) : (
            <>
              <Text style={styles.categoryLabel}>오류</Text>
              <Text style={styles.questionText}>질문을 불러올 수 없습니다</Text>
            </>
          )}
        </Animated.View>

        {/* Answer Options */}
        {currentQuestion && currentQuestion.type === 'choice' && currentQuestion.options && (
          <Animated.View style={[styles.optionsContainer, { opacity: fadeAnim }]}>
            {currentQuestion.options.map((option, index) => (
              <TouchableOpacity
                key={index}
                style={[
                  styles.optionButton,
                  isLoadingQuestion && styles.optionDisabled,
                ]}
                onPress={() => handleChoiceSelect(option)}
                disabled={isLoadingQuestion}
                activeOpacity={0.7}
              >
                <Text
                  style={[
                    styles.optionText,
                    isLoadingQuestion && styles.optionTextDisabled,
                  ]}
                >
                  {option}
                </Text>
                {isLoadingQuestion && (
                  <View style={styles.loadingOverlay}>
                    <Text style={styles.loadingText}>처리중...</Text>
                  </View>
                )}
              </TouchableOpacity>
            ))}
          </Animated.View>
        )}

        {/* Text Input */}
        {currentQuestion && currentQuestion.type === 'text' && (
          <View style={styles.inputContainer}>
            <TextInput
              style={[styles.textInput, isLoadingQuestion && styles.textInputDisabled]}
              value={textAnswer}
              onChangeText={setTextAnswer}
              placeholder="답변을 입력해주세요..."
              placeholderTextColor="rgba(255, 255, 255, 0.4)"
              multiline
              editable={!isLoadingQuestion}
            />
            <TouchableOpacity
              style={styles.sendButton}
              onPress={handleNext}
              disabled={!textAnswer.trim() || isLoadingQuestion}
            >
              <Ionicons
                name="send"
                size={24}
                color={textAnswer.trim() && !isLoadingQuestion ? '#4FD1C7' : 'rgba(255, 255, 255, 0.3)'}
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
    </View>
  );
}

function getCategoryLabel(category: string): string {
  const labels: Record<string, string> = {
    결혼: '💍 결혼 계획',
    가족: '👨‍👩‍👧 가족',
    재정: '💰 경제',
    종교: '🕊️ 종교',
    직장: '💼 직업',
    라이프스타일: '🏃 라이프스타일',
    성격: '🎭 성격',
    접근성: '♿ 접근성',
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
    backgroundColor: '#2E7D7A',
  },
  backgroundGradient: {
    ...StyleSheet.absoluteFillObject,
  },
  keyboardAvoidingView: {
    flex: 1,
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
  scrollContent: {
    flexGrow: 1,
    paddingTop: 120,
    paddingBottom: 40,
  },
  progressContainer: {
    position: 'absolute',
    top: 80,
    left: 20,
    right: 20,
    alignItems: 'center',
    zIndex: 10,
  },
  progressBar: {
    height: 3,
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    borderRadius: 2,
    overflow: 'hidden',
    width: 60,
    marginTop: 4,
  },
  progressFill: {
    height: '100%',
    backgroundColor: '#4FD1C7',
    borderRadius: 2,
  },
  progressText: {
    fontSize: 12,
    color: 'rgba(255, 255, 255, 0.9)',
    textAlign: 'center',
    fontWeight: '700',
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
    borderRadius: 100,
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
    fontWeight: '600',
    textAlign: 'center',
  },
  questionText: {
    fontSize: 22,
    fontWeight: '700',
    color: '#FFFFFF',
    lineHeight: 32,
    textAlign: 'center',
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
  // New styles for AI loading states
  optionDisabled: {
    opacity: 0.6,
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
  },
  optionTextDisabled: {
    color: 'rgba(255, 255, 255, 0.5)',
  },
  loadingOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  loadingText: {
    fontSize: 12,
    color: '#4FD1C7',
    fontWeight: '700',
    textShadowColor: 'rgba(47, 125, 122, 0.8)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 2,
  },
  textInputDisabled: {
    opacity: 0.6,
    color: 'rgba(255, 255, 255, 0.5)',
  },
});
