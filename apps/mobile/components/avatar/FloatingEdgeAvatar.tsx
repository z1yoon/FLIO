import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Animated,
  Platform,
  Easing,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';

export type AvatarState = 'idle' | 'listening' | 'thinking' | 'speaking';

interface FloatingEdgeAvatarProps {
  /** Current avatar state */
  state?: AvatarState;
  
  /** Whether avatar is actively listening to user */
  isListening?: boolean;
  
  /** Whether avatar is speaking (TTS active) */
  isSpeaking?: boolean;
  
  /** Whether avatar is processing/thinking */
  isThinking?: boolean;
  
  /** Contextual message to display */
  message?: string;
  
  /** Position: 'bottom-right' | 'bottom-left' */
  position?: 'bottom-right' | 'bottom-left';
  
  /** Callback when avatar is tapped */
  onPress?: () => void;
}

/**
 * Floating Edge Avatar Component
 * 
 * A small, unobtrusive avatar that appears at the edge of the screen
 * during profile creation. Expands to show guidance messages when tapped.
 */
export function FloatingEdgeAvatar({
  state = 'idle',
  isListening = false,
  isSpeaking = false,
  isThinking = false,
  message,
  position = 'bottom-right',
  onPress,
}: FloatingEdgeAvatarProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [currentMessage, setCurrentMessage] = useState(message);
  
  const scaleAnim = useRef(new Animated.Value(1)).current;
  const expandAnim = useRef(new Animated.Value(0)).current;
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const opacityAnim = useRef(new Animated.Value(0)).current;

  // Update message when prop changes
  useEffect(() => {
    if (message) {
      setCurrentMessage(message);
    }
  }, [message]);

  // Pulse animation when speaking/listening
  useEffect(() => {
    if (isSpeaking || isListening) {
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, {
            toValue: 1.15,
            duration: 600,
            easing: Easing.inOut(Easing.ease),
            useNativeDriver: true,
          }),
          Animated.timing(pulseAnim, {
            toValue: 1,
            duration: 600,
            easing: Easing.inOut(Easing.ease),
            useNativeDriver: true,
          }),
        ])
      ).start();
    } else {
      pulseAnim.setValue(1);
    }
  }, [isSpeaking, isListening]);

  // Auto-expand when there's a message
  useEffect(() => {
    if (currentMessage && !isExpanded) {
      setIsExpanded(true);
      Animated.parallel([
        Animated.spring(expandAnim, {
          toValue: 1,
          tension: 50,
          friction: 7,
          useNativeDriver: true,
        }),
        Animated.timing(opacityAnim, {
          toValue: 1,
          duration: 300,
          useNativeDriver: true,
        }),
      ]).start();

      // Auto-collapse after 5 seconds
      const timer = setTimeout(() => {
        handleCollapse();
      }, 5000);

      return () => clearTimeout(timer);
    }
  }, [currentMessage]);

  const handlePress = () => {
    if (isExpanded) {
      handleCollapse();
    } else {
      handleExpand();
    }
    onPress?.();
  };

  const handleExpand = () => {
    setIsExpanded(true);
    Animated.parallel([
      Animated.spring(expandAnim, {
        toValue: 1,
        tension: 50,
        friction: 7,
        useNativeDriver: true,
      }),
      Animated.timing(opacityAnim, {
        toValue: 1,
        duration: 300,
        useNativeDriver: true,
      }),
    ]).start();
  };

  const handleCollapse = () => {
    Animated.parallel([
      Animated.spring(expandAnim, {
        toValue: 0,
        tension: 50,
        friction: 7,
        useNativeDriver: true,
      }),
      Animated.timing(opacityAnim, {
        toValue: 0,
        duration: 200,
        useNativeDriver: true,
      }),
    ]).start(() => {
      setIsExpanded(false);
    });
  };

  // Get icon based on state
  const getIcon = () => {
    if (isSpeaking) return 'volume-high';
    if (isListening) return 'mic';
    if (isThinking) return 'hourglass-outline';
    return 'sparkles';
  };

  // Get color based on state
  const getColor = () => {
    if (isSpeaking) return '#48CAE4';
    if (isListening) return '#FF6B6B';
    if (isThinking) return '#FFD93D';
    return '#00FFC8';
  };

  const avatarColor = getColor();
  const iconName = getIcon();

  // Chat bubble width animation
  const bubbleWidth = expandAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [60, 280],
  });

  const messageOpacity = expandAnim.interpolate({
    inputRange: [0, 0.5, 1],
    outputRange: [0, 0, 1],
  });

  return (
    <View
      style={[
        styles.container,
        position === 'bottom-right' ? styles.bottomRight : styles.bottomLeft,
      ]}
      pointerEvents="box-none"
    >
      {/* Chat Bubble */}
      <Animated.View
        style={[
          styles.chatBubble,
          {
            width: bubbleWidth,
            opacity: opacityAnim,
            transform: [{ scale: expandAnim }],
          },
        ]}
      >
        {isExpanded && currentMessage && (
          <Animated.View
            style={[
              styles.messageContainer,
              { opacity: messageOpacity },
            ]}
          >
            <Text style={styles.messageText}>{currentMessage}</Text>
            <TouchableOpacity
              style={styles.closeButton}
              onPress={handleCollapse}
              hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
            >
              <Ionicons name="close" size={16} color="rgba(255,255,255,0.6)" />
            </TouchableOpacity>
          </Animated.View>
        )}
      </Animated.View>

      {/* Avatar Button */}
      <TouchableOpacity
        activeOpacity={0.8}
        onPress={handlePress}
        style={styles.avatarButton}
      >
        <Animated.View
          style={[
            styles.avatarContainer,
            {
              transform: [{ scale: Animated.multiply(scaleAnim, pulseAnim) }],
              borderColor: avatarColor,
            },
          ]}
        >
          {/* Glow layers */}
          <View style={[styles.glowLayer, { backgroundColor: `${avatarColor}20` }]} />
          <View style={[styles.glowLayer, { backgroundColor: `${avatarColor}15` }]} />
          
          {/* Core */}
          <View style={[styles.avatarCore, { backgroundColor: `${avatarColor}30` }]}>
            <Ionicons name={iconName} size={24} color={avatarColor} />
          </View>

          {/* Speaking indicator */}
          {(isSpeaking || isListening) && (
            <View style={styles.speakingIndicator}>
              <View style={[styles.soundBar, { height: 4 }]} />
              <View style={[styles.soundBar, { height: 8 }]} />
              <View style={[styles.soundBar, { height: 6 }]} />
            </View>
          )}
        </Animated.View>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    bottom: Platform.OS === 'ios' ? 100 : 80,
    zIndex: 1000,
  },
  bottomRight: {
    right: 20,
    alignItems: 'flex-end',
  },
  bottomLeft: {
    left: 20,
    alignItems: 'flex-start',
  },
  chatBubble: {
    backgroundColor: 'rgba(0, 0, 0, 0.85)',
    borderRadius: 20,
    padding: 0,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: 'rgba(72, 202, 228, 0.3)',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
    overflow: 'hidden',
  },
  messageContainer: {
    padding: 16,
    paddingRight: 36,
  },
  messageText: {
    fontSize: 14,
    color: '#FFFFFF',
    lineHeight: 20,
  },
  closeButton: {
    position: 'absolute',
    top: 12,
    right: 12,
    padding: 4,
  },
  avatarButton: {
    width: 60,
    height: 60,
  },
  avatarContainer: {
    width: 60,
    height: 60,
    borderRadius: 30,
    borderWidth: 2,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    shadowColor: '#48CAE4',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.6,
    shadowRadius: 20,
    elevation: 8,
  },
  glowLayer: {
    position: 'absolute',
    width: '100%',
    height: '100%',
    borderRadius: 30,
  },
  avatarCore: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: 'center',
    justifyContent: 'center',
  },
  speakingIndicator: {
    position: 'absolute',
    bottom: -12,
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: 2,
  },
  soundBar: {
    width: 3,
    backgroundColor: '#48CAE4',
    borderRadius: 2,
    opacity: 0.8,
  },
});

export default FloatingEdgeAvatar;
