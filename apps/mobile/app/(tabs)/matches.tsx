import { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Image,
  Dimensions,
  RefreshControl,
  ActivityIndicator,
  TextInput,
} from 'react-native';
import * as SecureStore from 'expo-secure-store';
import { LinearGradient } from 'expo-linear-gradient';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';

import { aiQuestionService, MatchResult, MatchExplanation } from '../../services/aiQuestionService';
import { FLIOAlertAPI } from '../../components/FLIOAlert';
import { getCurrentUserId } from '../../services/supabase/client';
import { supabaseQuestionService } from '../../services/supabaseQuestionService';

const { width, height } = Dimensions.get('window');

/**
 * AI-Powered Matching Screen
 * Shows compatible matches found using Azure OpenAI embeddings
 */
export default function MatchesScreen() {
  const [matches, setMatches] = useState<MatchResult[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedMatch, setSelectedMatch] = useState<MatchResult | null>(null);
  const [explanation, setExplanation] = useState<MatchExplanation | null>(null);
  const [showExplanation, setShowExplanation] = useState(false);
  const [showReshuffleDialog, setShowReshuffleDialog] = useState(false);
  const [reshufflePreference, setReshufflePreference] = useState('');
  const [currentUserId, setCurrentUserId] = useState<string | null>(null);
  const [isLoadingExplanation, setIsLoadingExplanation] = useState(false);
  const [hasLoadedMatches, setHasLoadedMatches] = useState(false);

  // Load cached matches from storage
  const loadCachedMatches = async (userId: string) => {
    try {
      console.log(`🔍 Looking for cached matches with key: matches_${userId}`);
      const cachedMatches = await SecureStore.getItemAsync(`matches_${userId}`);
      
      if (cachedMatches) {
        const parsedMatches = JSON.parse(cachedMatches);
        console.log(`✅ Found and loaded ${parsedMatches.length} cached matches for user`);
        setMatches(parsedMatches);
        setHasLoadedMatches(true);
        setIsLoading(false);
        return true;
      } else {
        console.log(`❌ No cached matches found for user ${userId}`);
      }
    } catch (error) {
      console.error('❌ Failed to load cached matches:', error);
    }
    return false;
  };

  // Save matches to storage
  const saveCachedMatches = async (userId: string, matches: MatchResult[]) => {
    try {
      await SecureStore.setItemAsync(`matches_${userId}`, JSON.stringify(matches));
      console.log(`💾 Cached ${matches.length} matches for user`);
    } catch (error) {
      console.error('❌ Failed to cache matches:', error);
    }
  };

  // Get authenticated user ID on mount
  useEffect(() => {
    const fetchUserId = async () => {
      const userId = await getCurrentUserId();
      if (userId) {
        setCurrentUserId(userId);
        // Try to load cached matches first
        const hasCachedMatches = await loadCachedMatches(userId);
        
        // If no cached matches, we need to load from API
        if (!hasCachedMatches) {
          console.log('🔄 No cached matches found - will fetch from API...');
          // Don't call loadMatches here - let the useEffect below handle it
        }
      }
    };
    fetchUserId();
  }, []);

  const loadMatches = async (isRefresh = false) => {
    try {
      if (isRefresh) setRefreshing(true);
      else setIsLoading(true);

      // Get current user ID - should be available since auth is handled at root level
      const userId = currentUserId || await getCurrentUserId();
      if (!userId) {
        console.error('❌ No user ID available in matches screen');
        FLIOAlertAPI.alert('오류', '사용자 정보를 불러올 수 없습니다.');
        return;
      }

      console.log('🔄 Loading AI-powered matches...');

      // Check if user has profile embedding
      const embeddingStatus = await aiQuestionService.checkEmbeddingStatus(userId);
      
      if (!embeddingStatus.has_embedding) {
        console.log('⚠️ No profile embedding found - attempting to create it...');
        // Try to create embedding if questions are answered but embedding doesn't exist
        const createResult = await aiQuestionService.createProfileEmbedding(userId);
        if (!createResult.success) {
          console.log('⚠️ AI profile analysis in progress - continuing with available data');
          // No alert needed - just continue silently with available functionality
        }
      }

      // Find matches with AI
      const matchResults = await aiQuestionService.findMatches(userId, 10, 0.4);

      if (matchResults.error) {
        FLIOAlertAPI.alert('오류', matchResults.error);
        return;
      }

      console.log(`✅ Found ${matchResults.total_found} AI matches`);
      setMatches(matchResults.matches);
      setHasLoadedMatches(true);
      
      // Cache the matches
      if (userId) {
        await saveCachedMatches(userId, matchResults.matches);
      }

    } catch (error) {
      console.error('❌ Failed to load matches:', error);
      FLIOAlertAPI.alert('연결 오류', 'AI 매칭 서비스 연결에 문제가 있습니다.');
    } finally {
      setIsLoading(false);
      setRefreshing(false);
    }
  };

  const handleMatchPress = async (match: MatchResult) => {
    try {
      setSelectedMatch(match);
      setIsLoadingExplanation(true);
      setShowExplanation(true);
      
      console.log(`🔍 Getting AI explanation for match with ${match.user_id}...`);
      
      const userId = currentUserId || await getCurrentUserId();
      if (!userId) {
        setIsLoadingExplanation(false);
        return;
      }
      
      const explanationResult = await aiQuestionService.getMatchExplanation(
        userId, 
        match.user_id
      );

      if (explanationResult.explanation) {
        setExplanation(explanationResult.explanation);
      } else {
        setShowExplanation(false);
        FLIOAlertAPI.alert('오류', explanationResult.error || '매칭 분석을 불러올 수 없습니다.');
      }
    } catch (error) {
      console.error('❌ Failed to get match explanation:', error);
      setShowExplanation(false);
      FLIOAlertAPI.alert('오류', '매칭 분석 중 문제가 발생했습니다.');
    } finally {
      setIsLoadingExplanation(false);
    }
  };

  const handleLikeMatch = (match: MatchResult) => {
    // In production, this would send like to backend
    console.log(`💕 Liked match: ${match.user_id}`);
    FLIOAlertAPI.alert('좋아요! 💕', `${match.name || '회원'}님에게 좋아요를 보냈습니다!`);
  };

  const handlePassMatch = (match: MatchResult) => {
    // Remove from current matches
    setMatches(prev => prev.filter(m => m.user_id !== match.user_id));
    console.log(`👋 Passed on match: ${match.user_id}`);
  };

  const closeExplanation = () => {
    setShowExplanation(false);
    setSelectedMatch(null);
    setExplanation(null);
  };

  const handleReshuffle = async () => {
    if (!reshufflePreference.trim()) {
      FLIOAlertAPI.alert('알림', '선호도를 입력해주세요.');
      return;
    }

    setShowReshuffleDialog(false);
    
    try {
      console.log('🔄 AI Reshuffle with preference:', reshufflePreference);
      
      // Show loading state
      setIsLoading(true);
      
      const userId = currentUserId || await getCurrentUserId();
      if (!userId) return;
      
      // Send current match IDs to exclude them from new results
      const currentMatchIds = matches.map(m => m.user_id);
      const improvedMatches = await aiQuestionService.findMatchesWithPreference(
        userId, 
        reshufflePreference,
        10,
        0.3,
        currentMatchIds
      );
      
      if (improvedMatches.error) {
        FLIOAlertAPI.alert('오류', improvedMatches.error);
        return;
      }
      
      console.log(`✨ Found ${improvedMatches.total_found} NEW matches based on preference`);
      
      // Backend already excluded previous matches, so just replace
      setMatches(improvedMatches.matches);
      setHasLoadedMatches(true);
      
      // Cache the new matches
      if (userId) {
        await saveCachedMatches(userId, improvedMatches.matches);
      }
      
      // Clear preference for next time
      setReshufflePreference('');
      
      FLIOAlertAPI.alert(
        '새로운 매칭! ✨',
        `당신의 선호도를 반영해 ${improvedMatches.total_found}명의 새로운 분들을 찾았어요!`
      );
      
    } catch (error) {
      console.error('❌ Failed to reshuffle:', error);
      FLIOAlertAPI.alert('연결 오류', '매칭 갱신 중 문제가 발생했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    // Add a small delay to ensure cached data is loaded first
    const timer = setTimeout(() => {
      console.log(`🔍 Effect triggered - userId: ${currentUserId ? 'exists' : 'none'}, hasLoaded: ${hasLoadedMatches}, matches: ${matches.length}`);
      
      if (currentUserId && !hasLoadedMatches && matches.length === 0) {
        console.log('🔄 First load for user - fetching matches from API...');
        loadMatches();
      } else if (currentUserId && (hasLoadedMatches || matches.length > 0)) {
        console.log('✅ User already has cached matches - skipping API call');
        setIsLoading(false);
      }
    }, 100);

    return () => clearTimeout(timer);
  }, [currentUserId, hasLoadedMatches, matches.length]);

  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <LinearGradient
          colors={['#2E7D7A', '#4FD1C7', '#7EDDD9']}
          style={styles.backgroundGradient}
        />
        <ActivityIndicator size="large" color="#FFFFFF" />
        <Text style={styles.loadingText}>AI가 호환되는 분들을 찾고 있어요...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <StatusBar style="light" />
      
      <LinearGradient
        colors={['#2E7D7A', '#4FD1C7', '#7EDDD9']}
        style={styles.backgroundGradient}
      />

      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerContent}>
          <View style={styles.titleSection}>
            <Text style={styles.headerTitle}>AI 매칭</Text>
            <Text style={styles.headerSubtitle}>당신과 잘 맞는 특별한 분들</Text>
          </View>
          <View style={styles.headerActions}>
            <TouchableOpacity
              style={styles.reshuffleButton}
              onPress={() => setShowReshuffleDialog(true)}
            >
              <Ionicons name="shuffle" size={20} color="#FFFFFF" />
              <Text style={styles.reshuffleButtonText}>새로운 매칭</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.userAccountButton}
              onPress={() => router.push('/account')}
              activeOpacity={0.7}
            >
              <Ionicons name="person-circle" size={32} color="#FFFFFF" />
            </TouchableOpacity>
          </View>
        </View>
      </View>

      {/* Matches List */}
      <ScrollView
        style={styles.scrollView}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => loadMatches(true)}
            tintColor="#FFFFFF"
          />
        }
      >
        {matches.length === 0 ? (
          <View style={styles.emptyState}>
            <Ionicons name="heart-outline" size={60} color="rgba(255,255,255,0.5)" />
            <Text style={styles.emptyTitle}>아직 매칭된 분이 없어요</Text>
            <Text style={styles.emptySubtitle}>
              더 많은 분들이 가입하면{'\n'}호환되는 분들을 찾아드릴게요!
            </Text>
            <TouchableOpacity 
              style={styles.refreshButton}
              onPress={() => loadMatches(true)}
            >
              <Text style={styles.refreshButtonText}>새로고침</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <View style={styles.matchesContainer}>
            {matches.map((match, index) => (
              <TouchableOpacity
                key={match.user_id}
                style={styles.matchCard}
                onPress={() => handleMatchPress(match)}
                activeOpacity={0.8}
              >
                {/* Profile Image Placeholder */}
                <View style={styles.profileImageContainer}>
                  <View style={styles.profileImagePlaceholder}>
                    <Ionicons name="person" size={40} color="rgba(255,255,255,0.7)" />
                  </View>
                  <View style={styles.compatibilityBadge}>
                    <Text style={styles.compatibilityText}>
                      {Math.round(match.compatibility_score * 100)}%
                    </Text>
                  </View>
                </View>

                {/* Profile Info */}
                <View style={styles.profileInfo}>
                  <Text style={styles.profileName}>
                    {match.name || `사용자 ${match.user_id.slice(0, 8)}`}
                  </Text>
                  {match.age && (
                    <Text style={styles.profileAge}>{match.age}세</Text>
                  )}
                </View>

                {/* Action Buttons */}
                <View style={styles.actionButtons}>
                  <TouchableOpacity
                    style={styles.passButton}
                    onPress={() => handlePassMatch(match)}
                  >
                    <Ionicons name="close" size={20} color="#FF6B6B" />
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={styles.likeButton}
                    onPress={() => handleLikeMatch(match)}
                  >
                    <Ionicons name="heart" size={20} color="#4FD1C7" />
                  </TouchableOpacity>
                </View>
              </TouchableOpacity>
            ))}
          </View>
        )}
      </ScrollView>

      {/* Match Explanation Modal */}
      {showExplanation && selectedMatch && (
        <View style={styles.modalOverlay}>
          <View style={styles.explanationModal}>
            <TouchableOpacity
              style={styles.closeButton}
              onPress={closeExplanation}
            >
              <Ionicons name="close" size={24} color="#FFFFFF" />
            </TouchableOpacity>

            {/* Loading State */}
            {isLoadingExplanation ? (
              <View style={styles.modalLoadingContainer}>
                <ActivityIndicator size="large" color="#4FD1C7" />
                <Text style={styles.loadingTitle}>매칭 분석 중</Text>
                <Text style={styles.loadingSubtitle}>
                  {selectedMatch?.name || '회원'}님과의 궁합을 분석하고 있어요
                </Text>
              </View>
            ) : explanation ? (
              <ScrollView 
              showsVerticalScrollIndicator={false}
              scrollEnabled={true}
              bounces={true}
              contentContainerStyle={styles.scrollContent}
            >
              <View style={styles.compatibilityHeader}>
                <Text style={styles.compatibilityPercentage}>
                  {Math.round(explanation.compatibility_score * 100)}%
                </Text>
                <Text style={styles.compatibilityLabelModal}>호환성</Text>
              </View>

              {/* AI Deep Analysis - First, matching category style */}
              {explanation.ai_analysis?.summary && (
                <View style={styles.reasonsSection}>
                  <Text style={styles.sectionTitle}>매니저의 매칭 분석</Text>
                  
                  {/* Summary Card */}
                  <View style={styles.aiSummaryCard}>
                    <Text style={styles.aiSummaryLabel}>요약</Text>
                    <Text style={styles.aiSummaryText}>{explanation.ai_analysis.summary}</Text>
                  </View>
                  
                  {/* Compatibility Reasons */}
                  {explanation.ai_analysis.compatibility_reasons?.length > 0 && (
                    <View style={styles.aiReasonsContainer}>
                      {explanation.ai_analysis.compatibility_reasons.map((reason: string, index: number) => (
                        <View key={index} style={styles.aiReasonCard}>
                          <Text style={styles.aiReasonNumber}>{index + 1}</Text>
                          <Text style={styles.aiReasonText}>{reason}</Text>
                        </View>
                      ))}
                    </View>
                  )}
                </View>
              )}
              
              {/* Category Graphs - Visual Stats */}
              {explanation.compatibility_graphs && Object.keys(explanation.compatibility_graphs).length > 0 && (
                <View style={styles.reasonsSection}>
                  <Text style={styles.sectionTitle}>영역별 호환성</Text>
                  
                  {/* Total Questions Summary */}
                  <View style={styles.totalQuestionsCard}>
                    <Text style={styles.totalQuestionsLabel}>전체 질문 일치도</Text>
                    <Text style={styles.totalQuestionsCount}>
                      {Object.values(explanation.compatibility_graphs).reduce((sum: number, cat: any) => sum + (cat.matching_questions || 0), 0)}/
                      {Object.values(explanation.compatibility_graphs).reduce((sum: number, cat: any) => sum + (cat.total_questions || 0), 0)}
                    </Text>
                    <Text style={styles.totalQuestionsSubtext}>질문 일치</Text>
                  </View>
                  
                  {/* Category Match Status - Simple Icons */}
                  {Object.entries(explanation.compatibility_graphs).map(([category, stats]: [string, any]) => (
                    <View key={category} style={styles.categoryMatchItem}>
                      <View style={styles.categoryMatchContent}>
                        <Ionicons 
                          name={stats.match_percentage === 100 ? "checkmark-circle" : stats.match_percentage === 0 ? "close-circle" : "remove-circle"} 
                          size={24} 
                          color={stats.match_percentage === 100 ? "#4FD1C7" : stats.match_percentage === 0 ? "#FF6B6B" : "#FFA500"} 
                        />
                        <Text style={styles.categoryMatchName}>{category}</Text>
                      </View>
                      <Text style={styles.categoryMatchDetail}>
                        {stats.matching_questions}/{stats.total_questions}
                      </Text>
                    </View>
                  ))}
                </View>
              )}


              {explanation.conversation_starters.length > 0 && (
                <View style={styles.startersSection}>
                  <Text style={styles.sectionTitle}>대화 시작 주제</Text>
                  {explanation.conversation_starters.map((starter, index) => (
                    <TouchableOpacity key={index} style={styles.starterItem}>
                      <Text style={styles.starterText}>"{starter}"</Text>
                    </TouchableOpacity>
                  ))}
                </View>
              )}

              <TouchableOpacity
                style={styles.sendMessageButton}
                onPress={() => {
                  closeExplanation();
                  // Navigate to chat or send like
                  handleLikeMatch(selectedMatch);
                }}
              >
                <Ionicons name="heart" size={20} color="#FFFFFF" />
                <Text style={styles.sendMessageText}>좋아요 보내기</Text>
              </TouchableOpacity>
              </ScrollView>
            ) : null}
          </View>
        </View>
      )}

      {/* Reshuffle Preference Dialog */}
      {showReshuffleDialog && (
        <View style={styles.modalOverlay}>
          <View style={styles.reshuffleModal}>
            <TouchableOpacity
              style={styles.closeButton}
              onPress={() => {
                setShowReshuffleDialog(false);
                setReshufflePreference('');
              }}
            >
              <Ionicons name="close" size={24} color="#666" />
            </TouchableOpacity>

            <Text style={styles.reshuffleTitle}>새로운 매칭 요청 🔄</Text>
            
            <Text style={styles.reshuffleQuestion}>
              어떤 이유로 새로운 매칭을 원하시나요?{"\n"}
              또는 특별히 중요하게 생각하는 부분이 있나요?
            </Text>
            
            <Text style={styles.reshuffleHint}>
              예시: "더 비슷한 취미를 가진 분", "좋아하는 음식이 비슷한 분", "운동을 좋아하는 분" 등
            </Text>

            <TextInput
              style={styles.preferenceInput}
              value={reshufflePreference}
              onChangeText={setReshufflePreference}
              placeholder="어떤 분을 더 만나고 싶으신지 알려주세요..."
              placeholderTextColor="rgba(0,0,0,0.4)"
              multiline
              numberOfLines={3}
              maxLength={200}
            />

            <View style={styles.reshuffleActions}>
              <TouchableOpacity
                style={styles.cancelButton}
                onPress={() => {
                  setShowReshuffleDialog(false);
                  setReshufflePreference('');
                }}
              >
                <Text style={styles.cancelButtonText}>취소</Text>
              </TouchableOpacity>
              
              <TouchableOpacity
                style={styles.confirmReshuffleButton}
                onPress={handleReshuffle}
              >
                <Ionicons name="shuffle" size={16} color="#FFFFFF" />
                <Text style={styles.confirmReshuffleText}>새로운 매칭 찾기</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      )}
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
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 16,
  },
  loadingText: {
    fontSize: 16,
    color: '#FFFFFF',
    textAlign: 'center',
  },
  header: {
    paddingTop: 60,
    paddingHorizontal: 24,
    paddingBottom: 20,
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: '700',
    color: '#FFFFFF',
    marginBottom: 4,
  },
  headerSubtitle: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.8)',
  },
  scrollView: {
    flex: 1,
  },
  matchesContainer: {
    paddingHorizontal: 20,
    paddingBottom: 20,
    gap: 16,
  },
  matchCard: {
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 16,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
  },
  profileImageContainer: {
    position: 'relative',
  },
  profileImagePlaceholder: {
    width: 70,
    height: 70,
    borderRadius: 35,
    backgroundColor: 'rgba(255,255,255,0.2)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  compatibilityBadge: {
    position: 'absolute',
    bottom: -5,
    right: -5,
    backgroundColor: '#4FD1C7',
    borderRadius: 12,
    paddingHorizontal: 8,
    paddingVertical: 2,
  },
  compatibilityText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  profileInfo: {
    flex: 1,
    gap: 4,
  },
  profileName: {
    fontSize: 18,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  profileAge: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.7)',
  },
  compatibilityBreakdown: {
    marginTop: 8,
    gap: 2,
  },
  compatibilityItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  compatibilityLabel: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.6)',
  },
  compatibilityValue: {
    fontSize: 12,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  actionButtons: {
    flexDirection: 'row',
    gap: 8,
  },
  passButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(255,107,107,0.2)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  likeButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(79,209,199,0.2)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  emptyState: {
    alignItems: 'center',
    paddingTop: 100,
    paddingHorizontal: 40,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#FFFFFF',
    marginTop: 16,
    textAlign: 'center',
  },
  emptySubtitle: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.7)',
    marginTop: 8,
    textAlign: 'center',
    lineHeight: 20,
  },
  refreshButton: {
    marginTop: 24,
    backgroundColor: '#4FD1C7',
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 24,
  },
  refreshButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  // Modal styles
  modalOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.7)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  explanationModal: {
    backgroundColor: '#2E7D7A',
    borderRadius: 20,
    padding: 24,
    maxHeight: '85%',
    width: '100%',
    minHeight: 400,
  },
  closeButton: {
    position: 'absolute',
    top: 16,
    right: 16,
    zIndex: 1,
    backgroundColor: 'rgba(255,255,255,0.2)',
    borderRadius: 20,
    padding: 8,
  },
  explanationTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#FFFFFF',
    textAlign: 'center',
    marginBottom: 20,
  },
  compatibilityHeader: {
    alignItems: 'center',
    marginBottom: 20,
  },
  compatibilityPercentage: {
    fontSize: 48,
    fontWeight: '700',
    color: '#4FD1C7',
  },
  compatibilityLabelModal: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFFFFF',
    marginTop: 8,
  },
  explanationSummary: {
    fontSize: 16,
    color: 'rgba(255,255,255,0.9)',
    lineHeight: 24,
    marginBottom: 20,
    textAlign: 'center',
  },
  reasonsSection: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#FFFFFF',
    marginBottom: 16,
    textShadowColor: 'rgba(0, 0, 0, 0.3)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 2,
  },
  aiSectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#FFFFFF',
    marginBottom: 12,
    textAlign: 'left',
  },
  aiSummaryCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.25)',
    borderRadius: 16,
    padding: 20,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.3)',
  },
  aiSummaryLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#4FD1C7',
    marginBottom: 12,
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  aiSummaryText: {
    fontSize: 16,
    color: '#FFFFFF',
    lineHeight: 26,
    fontWeight: '500',
    textShadowColor: 'rgba(0, 0, 0, 0.3)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 2,
  },
  aiReasonsContainer: {
    gap: 12,
  },
  aiReasonCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    borderRadius: 12,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'flex-start',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.25)',
  },
  aiReasonNumber: {
    fontSize: 18,
    fontWeight: '700',
    color: '#4FD1C7',
    marginRight: 12,
    minWidth: 24,
  },
  aiReasonText: {
    flex: 1,
    fontSize: 15,
    color: '#FFFFFF',
    lineHeight: 24,
    fontWeight: '500',
    textShadowColor: 'rgba(0, 0, 0, 0.3)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 2,
  },
  reasonItem: {
    marginBottom: 8,
  },
  reasonText: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.9)',
    lineHeight: 20,
  },
  startersSection: {
    marginBottom: 24,
  },
  starterItem: {
    backgroundColor: '#F0F9FF',
    borderRadius: 12,
    padding: 12,
    marginBottom: 8,
  },
  starterText: {
    fontSize: 14,
    color: '#2E7D7A',
    fontStyle: 'italic',
  },
  sendMessageButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#4FD1C7',
    borderRadius: 24,
    paddingVertical: 16,
    gap: 8,
  },
  sendMessageText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  totalQuestionsCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.15)',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    marginBottom: 12,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.3)',
  },
  totalQuestionsLabel: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.9)',
    marginBottom: 8,
  },
  totalQuestionsCount: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#4FD1C7',
    marginBottom: 4,
  },
  totalQuestionsSubtext: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.7)',
  },
  personalityCard: {
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  personalityTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFFFFF',
    marginBottom: 8,
  },
  personalityDescription: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.9)',
    marginBottom: 12,
    lineHeight: 20,
  },
  traitsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  traitTag: {
    backgroundColor: 'rgba(79, 209, 199, 0.3)',
    borderRadius: 16,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  traitText: {
    fontSize: 12,
    color: '#FFFFFF',
    fontWeight: '500',
  },
  matchSummaryCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.15)',
    borderRadius: 12,
    padding: 16,
    marginTop: 8,
  },
  matchSummaryText: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.95)',
    lineHeight: 20,
    textAlign: 'center',
  },
  aiAnalysisHeader: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.8)',
    marginBottom: 12,
    lineHeight: 20,
    fontStyle: 'italic',
  },
  // Modal Loading styles
  modalLoadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 60,
    paddingHorizontal: 30,
  },
  loadingTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#FFFFFF',
    marginTop: 24,
    marginBottom: 16,
    textAlign: 'center',
  },
  loadingSubtitle: {
    fontSize: 16,
    color: 'rgba(255,255,255,0.8)',
    textAlign: 'center',
    lineHeight: 24,
    paddingHorizontal: 20,
  },
  scrollContent: {
    paddingBottom: 20,
  },
  // AI Analysis emotional styles - NATURAL FLOW
  aiSectionTitleModal: {
    fontSize: 18,
    fontWeight: '700',
    color: '#4FD1C7',
    marginBottom: 16,
    textAlign: 'center',
    textShadowColor: 'rgba(0, 0, 0, 0.3)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 2,
  },
  aiAnalysisFlow: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 24,
    marginTop: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 3,
  },
  aiFlowText: {
    fontSize: 16,
    color: '#2C3E50',
    lineHeight: 28,
    fontWeight: '400',
    marginBottom: 16,
  },
  aiMainCard: {
    backgroundColor: 'rgba(79, 209, 199, 0.2)',
    borderRadius: 16,
    padding: 20,
    marginBottom: 20,
    borderWidth: 2,
    borderColor: 'rgba(79, 209, 199, 0.4)',
  },
  aiMainSummary: {
    fontSize: 16,
    color: '#FFFFFF',
    lineHeight: 26,
    textAlign: 'center',
    fontWeight: '500',
  },
  aiSubtitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#4FD1C7',
    marginBottom: 12,
    marginTop: 8,
  },
  aiReasonCardModal: {
    backgroundColor: 'rgba(255, 255, 255, 0.15)',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderLeftWidth: 4,
    borderLeftColor: '#4FD1C7',
  },
  aiAnalysisCard: {
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderRadius: 12,
    padding: 16,
  },
  aiAnalysisSummary: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.8)',
    lineHeight: 22,
    marginBottom: 16,
    fontStyle: 'italic',
  },
  emotionalReasonItem: {
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    borderRadius: 12,
    padding: 12,
    marginBottom: 8,
  },
  emotionalReasonText: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.9)',
    lineHeight: 22,
  },
  // Category match styles
  categoryMatchItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: 16,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    borderRadius: 12,
    marginBottom: 8,
  },
  categoryMatchContent: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    flex: 1,
  },
  categoryMatchName: {
    fontSize: 15,
    fontWeight: '500',
    color: '#FFFFFF',
  },
  categoryMatchDetail: {
    fontSize: 14,
    fontWeight: '600',
    color: 'rgba(255, 255, 255, 0.8)',
  },
  categoryDetail: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.5)',
    marginTop: 4,
  },
  // Header styles
  headerContent: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    width: '100%',
  },
  titleSection: {
    flex: 1,
  },
  headerActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  userAccountButton: {
    padding: 4,
    borderRadius: 20,
    backgroundColor: 'rgba(255,255,255,0.1)',
  },
  reshuffleButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.3)',
    borderRadius: 20,
    paddingHorizontal: 12,
    paddingVertical: 8,
    gap: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 3,
  },
  reshuffleButtonText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  // Reshuffle modal styles
  reshuffleModal: {
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    padding: 24,
    width: '100%',
    maxHeight: '70%',
  },
  reshuffleTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#2E7D7A',
    textAlign: 'center',
    marginBottom: 16,
    marginTop: 12,
  },
  reshuffleQuestion: {
    fontSize: 16,
    color: '#333',
    lineHeight: 24,
    marginBottom: 12,
    textAlign: 'center',
  },
  reshuffleHint: {
    fontSize: 13,
    color: '#666',
    lineHeight: 20,
    marginBottom: 20,
    fontStyle: 'italic',
  },
  preferenceInput: {
    backgroundColor: '#F5F5F5',
    borderRadius: 12,
    padding: 16,
    fontSize: 15,
    color: '#333',
    textAlignVertical: 'top',
    height: 100,
    marginBottom: 24,
    borderWidth: 1,
    borderColor: '#E0E0E0',
  },
  reshuffleActions: {
    flexDirection: 'row',
    gap: 12,
  },
  cancelButton: {
    flex: 1,
    backgroundColor: '#F0F0F0',
    borderRadius: 24,
    paddingVertical: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  cancelButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#666',
  },
  confirmReshuffleButton: {
    flex: 2,
    flexDirection: 'row',
    backgroundColor: '#4FD1C7',
    borderRadius: 24,
    paddingVertical: 14,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
  },
  confirmReshuffleText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFFFFF',
  },
});