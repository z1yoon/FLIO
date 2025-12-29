/**
 * FLIO AI Avatar Component (Rive)
 * 
 * Why Rive over Three.js/Lottie:
 * 1. State Machine - Real-time state transitions (Idle → Listening → Speaking)
 * 2. Performance - Native renderers (iOS: Core Graphics, Android: Skia)
 * 3. Lip Sync - Number inputs for smooth mouth animation
 * 4. Benchmark - Context7 score: 90.8/100 (vs Lottie: 87.4)
 * 5. File Size - ~60% smaller than Lottie
 * 6. Free - Community plan sufficient for MVP
 * 
 * @see /docs/AVATAR_TECH_COMPARISON.md for detailed comparison
 */

import React, { useRef, useCallback, useEffect } from 'react';
import { View, StyleSheet, ViewStyle } from 'react-native';
import Rive, { RiveRef, Fit, Alignment } from 'rive-react-native';

export type AvatarState = 'idle' | 'listening' | 'thinking' | 'speaking';

interface RiveAvatarProps {
  /** Current avatar state */
  state?: AvatarState;
  
  /** Whether avatar is actively listening to user */
  isListening?: boolean;
  
  /** Whether avatar is speaking (TTS active) */
  isSpeaking?: boolean;
  
  /** Whether avatar is processing/thinking */
  isThinking?: boolean;
  
  /** Emotion intensity (0-100): 0=calm, 100=excited/happy */
  emotionLevel?: number;
  
  /** Mouth open level for lip sync (0-100) */
  mouthOpenLevel?: number;
  
  /** Callback when animation state changes */
  onStateChanged?: (stateName: string) => void;
  
  /** Container style */
  style?: ViewStyle;
}

/**
 * State Machine Input Names
 * These must match the inputs defined in the .riv file
 */
const STATE_MACHINE_NAME = 'AvatarController';
const INPUTS = {
  IS_LISTENING: 'isListening',
  IS_SPEAKING: 'isSpeaking',
  IS_THINKING: 'isThinking',
  EMOTION_LEVEL: 'emotionLevel',
  MOUTH_OPEN: 'mouthOpen',
  TRIGGER_REACT: 'triggerReact',
} as const;

export function RiveAvatar({
  state = 'idle',
  isListening = false,
  isSpeaking = false,
  isThinking = false,
  emotionLevel = 50,
  mouthOpenLevel = 0,
  onStateChanged,
  style,
}: RiveAvatarProps) {
  const riveRef = useRef<RiveRef>(null);

  // Sync state prop to individual boolean states
  useEffect(() => {
    if (state === 'listening' && !isListening) {
      riveRef.current?.setInputState(STATE_MACHINE_NAME, INPUTS.IS_LISTENING, true);
      riveRef.current?.setInputState(STATE_MACHINE_NAME, INPUTS.IS_SPEAKING, false);
      riveRef.current?.setInputState(STATE_MACHINE_NAME, INPUTS.IS_THINKING, false);
    } else if (state === 'speaking' && !isSpeaking) {
      riveRef.current?.setInputState(STATE_MACHINE_NAME, INPUTS.IS_LISTENING, false);
      riveRef.current?.setInputState(STATE_MACHINE_NAME, INPUTS.IS_SPEAKING, true);
      riveRef.current?.setInputState(STATE_MACHINE_NAME, INPUTS.IS_THINKING, false);
    } else if (state === 'thinking' && !isThinking) {
      riveRef.current?.setInputState(STATE_MACHINE_NAME, INPUTS.IS_LISTENING, false);
      riveRef.current?.setInputState(STATE_MACHINE_NAME, INPUTS.IS_SPEAKING, false);
      riveRef.current?.setInputState(STATE_MACHINE_NAME, INPUTS.IS_THINKING, true);
    } else if (state === 'idle') {
      riveRef.current?.setInputState(STATE_MACHINE_NAME, INPUTS.IS_LISTENING, false);
      riveRef.current?.setInputState(STATE_MACHINE_NAME, INPUTS.IS_SPEAKING, false);
      riveRef.current?.setInputState(STATE_MACHINE_NAME, INPUTS.IS_THINKING, false);
    }
  }, [state]);

  // Sync individual boolean props
  useEffect(() => {
    riveRef.current?.setInputState(STATE_MACHINE_NAME, INPUTS.IS_LISTENING, isListening);
  }, [isListening]);

  useEffect(() => {
    riveRef.current?.setInputState(STATE_MACHINE_NAME, INPUTS.IS_SPEAKING, isSpeaking);
  }, [isSpeaking]);

  useEffect(() => {
    riveRef.current?.setInputState(STATE_MACHINE_NAME, INPUTS.IS_THINKING, isThinking);
  }, [isThinking]);

  // Sync emotion level (0-100)
  useEffect(() => {
    const clampedLevel = Math.max(0, Math.min(100, emotionLevel));
    riveRef.current?.setInputState(STATE_MACHINE_NAME, INPUTS.EMOTION_LEVEL, clampedLevel);
  }, [emotionLevel]);

  // Sync mouth open level for lip sync (0-100)
  useEffect(() => {
    const clampedLevel = Math.max(0, Math.min(100, mouthOpenLevel));
    riveRef.current?.setInputState(STATE_MACHINE_NAME, INPUTS.MOUTH_OPEN, clampedLevel);
  }, [mouthOpenLevel]);

  // Handle state machine state changes
  const handleStateChanged = useCallback(
    (stateMachineName: string, stateName: string) => {
      console.log(`[RiveAvatar] State changed: ${stateMachineName} → ${stateName}`);
      onStateChanged?.(stateName);
    },
    [onStateChanged]
  );

  // Trigger a reaction animation (e.g., nod, smile)
  const triggerReaction = useCallback(() => {
    riveRef.current?.fireState(STATE_MACHINE_NAME, INPUTS.TRIGGER_REACT);
  }, []);

  return (
    <View style={[styles.container, style]}>
      <Rive
        ref={riveRef}
        resourceName="flio_avatar" // Must have flio_avatar.riv in assets
        stateMachineName={STATE_MACHINE_NAME}
        fit={Fit.Contain}
        alignment={Alignment.Center}
        style={styles.avatar}
        autoplay={true}
        onStateChanged={handleStateChanged}
        onPlay={(animationName, isStateMachine) => {
          console.log(`[RiveAvatar] Playing: ${animationName}, isStateMachine: ${isStateMachine}`);
        }}
        onError={(error) => {
          console.error('[RiveAvatar] Error:', error);
        }}
      />
    </View>
  );
}

/**
 * Hook for lip sync integration
 * 
 * Usage:
 * const { mouthOpenLevel, startLipSync, stopLipSync } = useLipSync();
 * <RiveAvatar mouthOpenLevel={mouthOpenLevel} />
 */
export function useLipSync() {
  const [mouthOpenLevel, setMouthOpenLevel] = React.useState(0);
  const animationFrameRef = useRef<number | null>(null);
  const isActiveRef = useRef(false);

  // Simple audio level simulation (replace with actual audio analysis)
  const simulateLipSync = useCallback(() => {
    if (!isActiveRef.current) return;

    // Simulate mouth movement with some randomness
    const baseLevel = 30;
    const variation = Math.random() * 40;
    setMouthOpenLevel(baseLevel + variation);

    animationFrameRef.current = requestAnimationFrame(simulateLipSync);
  }, []);

  const startLipSync = useCallback(() => {
    isActiveRef.current = true;
    simulateLipSync();
  }, [simulateLipSync]);

  const stopLipSync = useCallback(() => {
    isActiveRef.current = false;
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }
    setMouthOpenLevel(0);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, []);

  return { mouthOpenLevel, startLipSync, stopLipSync };
}

const styles = StyleSheet.create({
  container: {
    width: '100%',
    height: 400,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'transparent',
  },
  avatar: {
    width: '100%',
    height: '100%',
  },
});

export default RiveAvatar;
