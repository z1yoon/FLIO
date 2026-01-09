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
  AccessibilityInfo,
} from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { StatusBar } from 'expo-status-bar';
import { supabaseQuestionService, Question, Answer } from '../../services/supabaseQuestionService';
import { FLIOAlertAPI } from '../../components/FLIOAlert';
import { supabase, getCurrentUserId } from '../../services/supabase/client';

const { width, height } = Dimensions.get('window');

// Generate unique user ID for this session
const generateUserId = () => `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

// Helper to track user answers locally
interface AnswerContext {
  user_id: string;
  previous_answers: Answer[];
}

/**
 * AI Question Screen
 * 
 * Presents adaptive questions and collects user responses
 * Uses AI backend for dynamic question generation with conditional logic
 */
export default function QuestionsScreen() {
  const params = useLocalSearchParams();
  
  // Korean identity data from verification
  const userName = params.name as string;
  const userAge = params.age as string;
  const userGender = params.gender as string;
  
  // Get authenticated user ID from Supabase Auth
  const [userId, setUserId] = useState<string | null>(null);
  
  // AI-driven state management
  const [questions, setQuestions] = useState<Question[]>([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(() => {
    // If coming back from complete page, start at the specified index
    const backIndex = params.currentQuestionIndex as string;
    return backIndex ? parseInt(backIndex) : 0;
  });
  const [answersContext, setAnswersContext] = useState<AnswerContext>({ user_id: '', previous_answers: [] });
  const [isLoadingQuestion, setIsLoadingQuestion] = useState(true);
  const [textAnswer, setTextAnswer] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isScreenReaderEnabled, setIsScreenReaderEnabled] = useState(false);
  
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const pulseAnim = useRef(new Animated.Value(1)).current;

  const currentQuestion = questions[currentQuestionIndex];
  const progress = questions.length > 0 ? (currentQuestionIndex + 1) / questions.length : 0;


  // Get authenticated user ID on mount
  useEffect(() => {
    const fetchUserId = async () => {
      const currentUserId = await getCurrentUserId();
      if (currentUserId) {
        setUserId(currentUserId);
        setAnswersContext(prev => ({ ...prev, user_id: currentUserId }));
        // Load questions after getting user ID
        loadInitialQuestions(currentUserId);
      } else if (params.userId) {
        // Validate UUID format
        const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
        if (uuidRegex.test(params.userId as string)) {
          // Valid UUID from password setup
          setUserId(params.userId as string);
          setAnswersContext(prev => ({ ...prev, user_id: params.userId as string }));
          loadInitialQuestions(params.userId as string);
        } else {
          console.error('❌ Invalid user ID format (not UUID):', params.userId);
          FLIOAlertAPI.alert('오류', '유효하지 않은 사용자 ID입니다. 다시 로그인해주세요.');
          router.replace('/(onboarding)/phone-verification');
        }
      } else {
        console.log('⚠️ No authenticated user - redirecting to phone verification');
        router.replace('/(onboarding)/phone-verification');
      }
    };
    fetchUserId();
  }, []);

  // Load questions from Supabase (only after phone verification)
  const loadInitialQuestions = async (currentUserId: string) => {
    try {
      setIsLoadingQuestion(true);
      
      // Get user's current progress
      const userProfile = await supabaseQuestionService.getUserProfile(currentUserId);
      const answeredCount = userProfile?.total_answers || 0;
      const completionPercentage = userProfile?.profile_completion.completion_percentage || 0;
      
      console.log(`📊 Resuming profile completion: ${answeredCount} answers (${completionPercentage.toFixed(1)}%)`);
      
      // Load unanswered questions from Supabase
      const unansweredQuestions = await supabaseQuestionService.getUnansweredQuestions(currentUserId);
      
      if (unansweredQuestions.length === 0) {
        // No more unanswered questions - check if user can start matching
        const canStartMatching = userProfile?.profile_completion.can_start_matching || false;
        
        if (canStartMatching) {
          // Profile complete - go to complete screen
          console.log('✅ All questions completed and can start matching!');
          router.replace({
            pathname: '/(onboarding)/complete',
            params: { 
              userId: currentUserId,
              name: userName,
              age: userAge,
              gender: userGender,
              hasAIProfile: 'true'
            }
          });
        } else {
          // Answered all available questions but not enough for matching
          console.log('⚠️ No unanswered questions but insufficient answers for matching');
          FLIOAlertAPI.alert(
            '프로필 완성 중',
            `현재 ${answeredCount}개의 질문에 답변하셨습니다. 더 많은 질문이 곧 추가될 예정입니다. 지금은 매칭 화면으로 이동합니다.`,
            [
              {
                text: '확인',
                onPress: () => router.replace('/(tabs)/matches')
              }
            ]
          );
        }
        return;
      }
      
      setQuestions(unansweredQuestions);
      console.log(`📝 Loaded ${unansweredQuestions.length} unanswered questions (continuing from ${answeredCount} answered)`);
      
      // Show resumption message for existing users
      if (answeredCount > 0) {
        FLIOAlertAPI.alert(
          '프로필 완성 재개',
          `이전에 답변하신 ${answeredCount}개 질문에서 이어서 진행합니다.`,
          [{ text: '계속하기', onPress: () => {} }]
        );
      }
    } catch (error) {
      console.error('❌ Failed to load questions from Supabase:', error);
      FLIOAlertAPI.alert('연결 오류', 'Supabase 연결에 문제가 있습니다. 다시 시도해주세요.');
    } finally {
      setIsLoadingQuestion(false);
    }
  };

  // Production answer processing with Supabase integration
  const processAnswerAndGetNext = async (answer: string, importance: number = 3, isDealbreaker: boolean = false) => {
    if (!currentQuestion || !userId) {
      console.error('❌ Cannot process answer: missing question or user ID');
      return;
    }

    try {
      setIsLoadingQuestion(true);

      // Submit answer to Supabase database
      const result = await supabaseQuestionService.submitAnswer(
        userId,
        currentQuestion.id,
        answer,
        importance,
        isDealbreaker
      );

      if (result.success) {
        // Store the answer locally in context
        const newAnswer: Answer = {
          question_id: currentQuestion.id,
          answer_value: answer,
          importance,
          is_dealbreaker: isDealbreaker,
          timestamp: new Date().toISOString(),
        };

        const updatedContext: AnswerContext = {
          ...answersContext,
          previous_answers: [...answersContext.previous_answers, newAnswer],
        };

        setAnswersContext(updatedContext);

        // Progress to next question or complete
        if (currentQuestionIndex < questions.length - 1) {
          setCurrentQuestionIndex(currentQuestionIndex + 1);
          setTextAnswer(''); // Clear text input
        } else {
          // All questions completed - check profile status
          console.log('🎯 All questions completed! Checking profile status...');
          
          try {
            // Get user profile to check completion status
            const userProfile = await supabaseQuestionService.getUserProfile(userId);
            const canStartMatching = userProfile?.profile_completion.can_start_matching || false;
            const completionPercentage = userProfile?.profile_completion.completion_percentage || 0;
            
            console.log(`✅ Profile completed: ${completionPercentage.toFixed(1)}% (${userProfile?.total_answers} answers)`);
            
            // Go directly to completion screen
            router.replace({
              pathname: '/(onboarding)/complete',
              params: { 
                userId: userId,
                name: userName,
                age: userAge,
                gender: userGender,
                hasAIProfile: canStartMatching ? 'true' : 'false',
                completionPercentage: completionPercentage.toString()
              }
            });
          } catch (profileError) {
            console.error('Profile check failed:', profileError);
            // Continue even if profile check fails
            router.replace({
              pathname: '/(onboarding)/complete',
              params: { 
                userId: userId,
                name: userName,
                age: userAge,
                gender: userGender
              }
            });
          }
        }
      } else {
        FLIOAlertAPI.alert('오류', result.message || '답변 저장 중 문제가 발생했습니다.');
      }

    } catch (error) {
      console.error('❌ Failed to process answer:', error);
      FLIOAlertAPI.alert('연결 오류', 'Supabase 연결에 문제가 있습니다. 다시 시도해주세요.');
    } finally {
      setIsLoadingQuestion(false);
    }
  };

  // Initialize screen reader check
  useEffect(() => {
    AccessibilityInfo.isScreenReaderEnabled().then(screenReaderEnabled => {
      setIsScreenReaderEnabled(screenReaderEnabled);
    });
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
    if (!isScreenReaderEnabled) return;
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
      // Can't go back from first question - user is in onboarding flow
      // Just stay on the first question
      console.log('⚠️ Already at first question');
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
        showsVerticalScrollIndicator={false}
        bounces={true}
      >
        {/* Progress Bar */}
        <View style={styles.progressContainer}>
          <Text 
            style={styles.progressText}
            accessible={true}
            accessibilityRole="text"
            accessibilityLabel={`진행률: ${questions.length}개 질문 중 ${currentQuestionIndex + 1}번째`}
          >
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
              <Text 
                style={styles.categoryLabel}
                accessible={true}
                accessibilityRole="text"
                accessibilityLabel={`카테고리: ${getCategoryLabel(currentQuestion.category)}`}
              >
                {getCategoryLabel(currentQuestion.category)}
              </Text>
              <Text 
                style={styles.questionText}
                accessible={true}
                accessibilityRole="text"
                accessibilityLabel={`질문: ${currentQuestion.text}`}
              >
                {currentQuestion.text}
              </Text>
            </>
          ) : isLoadingQuestion ? (
            <>
              <Text style={styles.categoryLabel}>질문 불러오는 중...</Text>
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
                accessible={true}
                accessibilityRole="button"
                accessibilityLabel={`답변 선택: ${option}`}
                accessibilityHint="이 답변을 선택하려면 두 번 탭하세요"
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

        {/* Open-ended Question Input */}
        {currentQuestion && currentQuestion.type === 'text' && (
          <Animated.View style={[styles.openEndedContainer, { opacity: fadeAnim }]}>
            <View style={styles.textInputWrapper}>
              {currentQuestion.placeholder && (
                <Text style={styles.placeholderGuide}>
                  {currentQuestion.placeholder}
                </Text>
              )}
              <TextInput
                style={[styles.textInput, isLoadingQuestion && styles.textInputDisabled]}
                value={textAnswer}
                onChangeText={setTextAnswer}
                placeholder="터치해서 답변을 입력하세요..."
                placeholderTextColor="rgba(255, 255, 255, 0.4)"
                multiline
                textAlignVertical="top"
                editable={!isLoadingQuestion}
                maxLength={currentQuestion.maxLength || 500}
                accessible={true}
                accessibilityLabel="개방형 질문 답변 입력"
                accessibilityHint="여기에 자세한 답변을 입력하세요"
              />
              <View style={styles.textInputFooter}>
                <Text style={styles.characterCount}>
                  {textAnswer.length}/{currentQuestion.maxLength || 500}
                </Text>
                <TouchableOpacity
                  style={[
                    styles.submitTextButton,
                    (!textAnswer.trim() || isLoadingQuestion) && styles.submitButtonDisabled
                  ]}
                  onPress={handleNext}
                  disabled={!textAnswer.trim() || isLoadingQuestion}
                  accessible={true}
                  accessibilityRole="button"
                  accessibilityLabel="답변 제출"
                  accessibilityHint="작성한 답변을 제출하고 다음 질문으로 넘어갑니다"
                >
                  {isLoadingQuestion ? (
                    <Text style={styles.submitButtonText}>처리중...</Text>
                  ) : (
                    <>
                      <Text style={styles.submitButtonText}>다음</Text>
                      <Ionicons name="arrow-forward" size={16} color="#FFFFFF" />
                    </>
                  )}
                </TouchableOpacity>
              </View>
            </View>
            
            {/* Helpful Tips for Open-ended Questions */}
            <View style={styles.helpTips}>
              <Text style={styles.helpTipsTitle}>💡 작성 팁</Text>
              <Text style={styles.helpTipsText}>
                • 솔직하고 구체적으로 표현해주세요{'\n'}
                • 본인의 경험이나 생각을 자유롭게 써주세요{'\n'}
                • 더 나은 매칭을 위해 진실된 답변을 부탁드려요
              </Text>
            </View>
          </Animated.View>
        )}

        {/* Voice Input Button - Show only for screen reader users */}
        {isScreenReaderEnabled && (
          <TouchableOpacity
            style={[styles.voiceButton, isListening && styles.voiceButtonActive]}
            onPress={handleVoiceInput}
            activeOpacity={0.7}
            accessible={true}
            accessibilityRole="button"
            accessibilityLabel="음성으로 답변하기"
            accessibilityHint="음성 입력을 시작하려면 두 번 탭하세요"
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
        )}
      </ScrollView>
      </KeyboardAvoidingView>
    </View>
  );
}

function getCategoryLabel(category: string): string {
  const labels: Record<string, string> = {
    'MBTI성향': '🧠 MBTI 성향',
    '갈등해결': '💬 갈등해결',
    '가족관계': '👨‍👩‍👧 가족관계',
    '재정관리': '💰 재정관리',
    '감정지원': '❤️ 감정지원',
    '미래계획': '🎯 미래계획',
    '친밀감': '💕 친밀감',
    '소통방식': '🗣️ 소통방식',
    '결혼계획': '💍 결혼계획',
    '가족가치관': '🏠 가족가치관',
    '라이프스타일': '🏃 라이프스타일',
    '경제관념': '💼 경제관념',
    '애착스타일': '🤝 애착스타일',
    '성격': '🎭 성격',
    '가치관': '💎 가치관',
    // Legacy support
    결혼: '💍 결혼계획',
    가족: '🏠 가족가치관',
    재정: '💼 경제관념',
    연애: '💕 애착스타일',
    직장: '💼 경제관념'
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
    backgroundColor: 'transparent',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: 'rgba(255, 255, 255, 0.8)',
  },
  scrollContent: {
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
    height: height * 0.22,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 20,
  },
  avatarContainer: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  imageContainer: {
    width: 160,
    height: 160,
    borderRadius: 80,
    overflow: 'hidden',
    backgroundColor: 'transparent',
    shadowColor: 'rgba(79, 209, 199, 0.8)',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.6,
    shadowRadius: 20,
    elevation: 8,
  },
  managerImage: {
    width: 160,
    height: 160,
    borderRadius: 80,
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
    fontSize: 20,
    fontWeight: '700',
    color: '#FFFFFF',
    lineHeight: 28,
    textAlign: 'center',
  },
  optionsContainer: {
    paddingHorizontal: 24,
    paddingBottom: 20,
    gap: 10,
  },
  optionButton: {
    backgroundColor: 'transparent',
    borderRadius: 14,
    paddingVertical: 14,
    paddingHorizontal: 22,
    borderWidth: 2,
    borderColor: 'rgba(255, 255, 255, 0.6)',
  },
  optionSelected: {
    backgroundColor: 'rgba(79, 209, 199, 0.15)',
    borderColor: '#4FD1C7',
  },
  optionText: {
    fontSize: 15,
    color: '#FFFFFF',
    textAlign: 'center',
  },
  optionTextSelected: {
    color: '#4FD1C7',
    fontWeight: '600',
  },
  // Open-ended question styles
  openEndedContainer: {
    paddingHorizontal: 24,
    paddingBottom: 20,
  },
  textInputWrapper: {
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 16,
    paddingHorizontal: 20,
    paddingVertical: 16,
    borderWidth: 1.5,
    borderColor: 'rgba(79, 209, 199, 0.3)',
  },
  placeholderGuide: {
    fontSize: 13,
    color: 'rgba(255, 255, 255, 0.6)',
    marginBottom: 12,
    lineHeight: 18,
    fontStyle: 'italic',
  },
  textInput: {
    fontSize: 16,
    color: '#FFFFFF',
    minHeight: 120,
    textAlignVertical: 'top',
    lineHeight: 22,
  },
  textInputFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 16,
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.1)',
  },
  characterCount: {
    fontSize: 12,
    color: 'rgba(255, 255, 255, 0.5)',
  },
  submitTextButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#4FD1C7',
    paddingVertical: 10,
    paddingHorizontal: 20,
    borderRadius: 20,
    gap: 6,
  },
  submitButtonDisabled: {
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
  },
  submitButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  helpTips: {
    marginTop: 16,
    backgroundColor: 'rgba(79, 209, 199, 0.08)',
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderLeftWidth: 3,
    borderLeftColor: '#4FD1C7',
  },
  helpTipsTitle: {
    fontSize: 13,
    fontWeight: '600',
    color: '#4FD1C7',
    marginBottom: 6,
  },
  helpTipsText: {
    fontSize: 12,
    color: 'rgba(255, 255, 255, 0.7)',
    lineHeight: 16,
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
