import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  Modal,
  Animated,
  Easing,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { aiManagerService, ChatMessage } from '../services/aiManagerService';

interface AIManagerChatProps {
  userId: string;
  visible: boolean;
  onClose: () => void;
  /** Optional pre-loaded context hint shown as first AI message */
  contextHint?: string;
}

const TEAL = '#40e0d0';
const DARK_BG = '#0a0e1a';
const CARD_BG = '#111827';
const USER_BUBBLE = '#1e3a5f';
const AI_BUBBLE = '#1a2e2e';

// Quick-reply chips shown after each AI response
const QUICK_REPLIES = [
  '매칭이 마음에 안 들어요',
  '프로필 개선하고 싶어요',
  '결혼 상담 받고 싶어요',
  '매칭 설명 더 듣고 싶어요',
];

export default function AIManagerChat({ userId, visible, onClose, contextHint }: AIManagerChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);
  const [suggestedActions, setSuggestedActions] = useState<string[]>(QUICK_REPLIES);
  const [isHistoryLoaded, setIsHistoryLoaded] = useState(false);

  const flatListRef = useRef<FlatList>(null);
  const typingDot1 = useRef(new Animated.Value(0)).current;
  const typingDot2 = useRef(new Animated.Value(0)).current;
  const typingDot3 = useRef(new Animated.Value(0)).current;

  // Typing indicator animation
  const startTypingAnimation = () => {
    const dot = (val: Animated.Value, delay: number) =>
      Animated.loop(
        Animated.sequence([
          Animated.delay(delay),
          Animated.timing(val, { toValue: -6, duration: 300, useNativeDriver: true, easing: Easing.inOut(Easing.quad) }),
          Animated.timing(val, { toValue: 0, duration: 300, useNativeDriver: true, easing: Easing.inOut(Easing.quad) }),
        ])
      );
    Animated.parallel([dot(typingDot1, 0), dot(typingDot2, 150), dot(typingDot3, 300)]).start();
  };

  const stopTypingAnimation = () => {
    typingDot1.stopAnimation();
    typingDot2.stopAnimation();
    typingDot3.stopAnimation();
    typingDot1.setValue(0);
    typingDot2.setValue(0);
    typingDot3.setValue(0);
  };

  // Load history when modal opens
  useEffect(() => {
    if (visible && !isHistoryLoaded) {
      loadHistory();
    }
  }, [visible]);

  const loadHistory = async () => {
    try {
      const history = await aiManagerService.getSessionHistory(userId);
      if (history.has_history && history.session_id) {
        setMessages(history.messages);
        setSessionId(history.session_id);
      } else {
        // Show welcome message
        const welcome: ChatMessage = {
          role: 'assistant',
          content: contextHint ||
            '안녕하세요! FLIO AI 매니저입니다 😊\n\n결혼정보회사 매니저처럼 여러분의 매칭을 도와드릴게요. 매칭 추천이 마음에 들지 않으시거나, 프로필 개선이 필요하시거나, 결혼에 대해 이야기 나누고 싶으실 때 편하게 말씀해 주세요.',
          timestamp: new Date().toISOString(),
        };
        setMessages([welcome]);
      }
      setIsHistoryLoaded(true);
    } catch (e) {
      console.error('Failed to load AI manager history:', e);
      setIsHistoryLoaded(true);
    }
  };

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || isLoading) return;

    const userMsg: ChatMessage = {
      role: 'user',
      content: text.trim(),
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMsg]);
    setInputText('');
    setIsLoading(true);
    setSuggestedActions([]);
    startTypingAnimation();

    try {
      const response = await aiManagerService.chat(userId, text.trim(), sessionId);
      stopTypingAnimation();

      const aiMsg: ChatMessage = {
        role: 'assistant',
        content: response.message,
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, aiMsg]);
      setSessionId(response.session_id);

      if (response.suggested_actions?.length) {
        setSuggestedActions(response.suggested_actions);
      } else {
        setSuggestedActions(QUICK_REPLIES.slice(0, 2));
      }
    } catch (e) {
      stopTypingAnimation();
      const errMsg: ChatMessage = {
        role: 'assistant',
        content: '죄송합니다. 잠시 후 다시 시도해 주세요.',
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errMsg]);
    } finally {
      setIsLoading(false);
    }
  }, [userId, sessionId, isLoading]);

  const scrollToBottom = () => {
    setTimeout(() => flatListRef.current?.scrollToEnd({ animated: true }), 100);
  };

  useEffect(() => {
    if (messages.length > 0) scrollToBottom();
  }, [messages, isLoading]);

  const renderMessage = ({ item }: { item: ChatMessage }) => {
    const isUser = item.role === 'user';
    return (
      <View style={[styles.messageRow, isUser ? styles.messageRowUser : styles.messageRowAI]}>
        {!isUser && (
          <View style={styles.aiAvatar}>
            <Text style={styles.aiAvatarText}>AI</Text>
          </View>
        )}
        <View style={[styles.bubble, isUser ? styles.bubbleUser : styles.bubbleAI]}>
          <Text style={styles.bubbleText}>{item.content}</Text>
          <Text style={styles.bubbleTime}>
            {new Date(item.timestamp).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}
          </Text>
        </View>
      </View>
    );
  };

  const renderTypingIndicator = () => {
    if (!isLoading) return null;
    return (
      <View style={[styles.messageRow, styles.messageRowAI]}>
        <View style={styles.aiAvatar}>
          <Text style={styles.aiAvatarText}>AI</Text>
        </View>
        <View style={[styles.bubble, styles.bubbleAI, styles.typingBubble]}>
          <View style={styles.typingDots}>
            {[typingDot1, typingDot2, typingDot3].map((dot, i) => (
              <Animated.View
                key={i}
                style={[styles.typingDot, { transform: [{ translateY: dot }] }]}
              />
            ))}
          </View>
        </View>
      </View>
    );
  };

  return (
    <Modal visible={visible} animationType="slide" presentationStyle="pageSheet" onRequestClose={onClose}>
      <View style={styles.container}>
        {/* Header */}
        <LinearGradient colors={['#0f2027', '#203a43', '#2c5364']} style={styles.header}>
          <View style={styles.headerLeft}>
            <View style={styles.headerAvatar}>
              <Text style={styles.headerAvatarText}>AI</Text>
              <View style={styles.onlineDot} />
            </View>
            <View>
              <Text style={styles.headerTitle}>FLIO AI 매니저</Text>
              <Text style={styles.headerSubtitle}>신뢰할 수 있는 연결 전문가</Text>
            </View>
          </View>
          <TouchableOpacity onPress={onClose} style={styles.closeButton}>
            <Ionicons name="close" size={24} color="rgba(255,255,255,0.8)" />
          </TouchableOpacity>
        </LinearGradient>

        {/* Messages */}
        <KeyboardAvoidingView
          style={styles.flex}
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
          keyboardVerticalOffset={0}
        >
          <FlatList
            ref={flatListRef}
            data={messages}
            keyExtractor={(_, i) => String(i)}
            renderItem={renderMessage}
            ListFooterComponent={renderTypingIndicator}
            contentContainerStyle={styles.messageList}
            showsVerticalScrollIndicator={false}
          />

          {/* Quick replies */}
          {suggestedActions.length > 0 && !isLoading && (
            <View style={styles.quickRepliesContainer}>
              <FlatList
                data={suggestedActions}
                horizontal
                showsHorizontalScrollIndicator={false}
                keyExtractor={(item) => item}
                contentContainerStyle={styles.quickReplies}
                renderItem={({ item }) => (
                  <TouchableOpacity style={styles.quickReplyChip} onPress={() => sendMessage(item)}>
                    <Text style={styles.quickReplyText}>{item}</Text>
                  </TouchableOpacity>
                )}
              />
            </View>
          )}

          {/* Input bar */}
          <View style={styles.inputBar}>
            <TextInput
              style={styles.input}
              placeholder="AI 매니저에게 물어보세요..."
              placeholderTextColor="rgba(255,255,255,0.3)"
              value={inputText}
              onChangeText={setInputText}
              multiline
              maxLength={500}
              onSubmitEditing={() => sendMessage(inputText)}
            />
            <TouchableOpacity
              style={[styles.sendButton, (!inputText.trim() || isLoading) && styles.sendButtonDisabled]}
              onPress={() => sendMessage(inputText)}
              disabled={!inputText.trim() || isLoading}
            >
              {isLoading
                ? <ActivityIndicator size="small" color={TEAL} />
                : <Ionicons name="send" size={20} color={inputText.trim() ? TEAL : 'rgba(255,255,255,0.3)'} />
              }
            </TouchableOpacity>
          </View>
        </KeyboardAvoidingView>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: {
    flex: 1,
    backgroundColor: DARK_BG,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 14,
    paddingTop: Platform.OS === 'ios' ? 52 : 14,
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  headerAvatar: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: `${TEAL}22`,
    borderWidth: 2,
    borderColor: `${TEAL}80`,
    justifyContent: 'center',
    alignItems: 'center',
    position: 'relative',
  },
  headerAvatarText: {
    color: TEAL,
    fontWeight: 'bold',
    fontSize: 14,
  },
  onlineDot: {
    position: 'absolute',
    bottom: 1,
    right: 1,
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: '#4ade80',
    borderWidth: 2,
    borderColor: DARK_BG,
  },
  headerTitle: {
    color: '#fff',
    fontWeight: '700',
    fontSize: 16,
  },
  headerSubtitle: {
    color: 'rgba(255,255,255,0.5)',
    fontSize: 12,
    marginTop: 1,
  },
  closeButton: {
    padding: 8,
  },
  messageList: {
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 8,
  },
  messageRow: {
    flexDirection: 'row',
    marginBottom: 12,
    alignItems: 'flex-end',
  },
  messageRowUser: {
    justifyContent: 'flex-end',
  },
  messageRowAI: {
    justifyContent: 'flex-start',
  },
  aiAvatar: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: `${TEAL}22`,
    borderWidth: 1,
    borderColor: `${TEAL}60`,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 8,
    flexShrink: 0,
  },
  aiAvatarText: {
    color: TEAL,
    fontWeight: 'bold',
    fontSize: 10,
  },
  bubble: {
    maxWidth: '75%',
    borderRadius: 18,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  bubbleUser: {
    backgroundColor: USER_BUBBLE,
    borderBottomRightRadius: 4,
  },
  bubbleAI: {
    backgroundColor: AI_BUBBLE,
    borderBottomLeftRadius: 4,
    borderWidth: 1,
    borderColor: `${TEAL}20`,
  },
  bubbleText: {
    color: 'rgba(255,255,255,0.92)',
    fontSize: 15,
    lineHeight: 22,
  },
  bubbleTime: {
    color: 'rgba(255,255,255,0.3)',
    fontSize: 10,
    marginTop: 4,
    textAlign: 'right',
  },
  typingBubble: {
    paddingVertical: 14,
  },
  typingDots: {
    flexDirection: 'row',
    gap: 4,
    alignItems: 'center',
  },
  typingDot: {
    width: 7,
    height: 7,
    borderRadius: 4,
    backgroundColor: `${TEAL}90`,
  },
  quickRepliesContainer: {
    borderTopWidth: 1,
    borderTopColor: 'rgba(255,255,255,0.06)',
    paddingVertical: 10,
  },
  quickReplies: {
    paddingHorizontal: 16,
    gap: 8,
  },
  quickReplyChip: {
    backgroundColor: `${TEAL}18`,
    borderWidth: 1,
    borderColor: `${TEAL}50`,
    borderRadius: 20,
    paddingHorizontal: 14,
    paddingVertical: 7,
  },
  quickReplyText: {
    color: TEAL,
    fontSize: 13,
    fontWeight: '500',
  },
  inputBar: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    paddingHorizontal: 16,
    paddingVertical: 12,
    paddingBottom: Platform.OS === 'ios' ? 28 : 12,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255,255,255,0.06)',
    backgroundColor: CARD_BG,
    gap: 10,
  },
  input: {
    flex: 1,
    backgroundColor: 'rgba(255,255,255,0.06)',
    borderRadius: 22,
    paddingHorizontal: 16,
    paddingVertical: 10,
    color: '#fff',
    fontSize: 15,
    maxHeight: 120,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
  },
  sendButton: {
    width: 42,
    height: 42,
    borderRadius: 21,
    backgroundColor: `${TEAL}18`,
    borderWidth: 1,
    borderColor: `${TEAL}60`,
    justifyContent: 'center',
    alignItems: 'center',
  },
  sendButtonDisabled: {
    opacity: 0.4,
  },
});
