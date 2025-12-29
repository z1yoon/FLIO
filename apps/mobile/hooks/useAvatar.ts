import { useState, useCallback, useRef, useEffect } from 'react';
import { AvatarState } from '@/components/avatar/AuroraAvatar';
import * as Speech from 'expo-speech';

interface UseAvatarOptions {
  onSpeakStart?: () => void;
  onSpeakEnd?: () => void;
  onListenStart?: () => void;
  onListenEnd?: () => void;
}

interface UseAvatarReturn {
  /** Current avatar state */
  state: AvatarState;
  /** Lip sync value for animations (0-100) */
  lipSyncValue: number;
  /** Emotion intensity (0-100) */
  emotionLevel: number;
  /** Make the avatar speak text */
  speak: (text: string) => Promise<void>;
  /** Start listening for user input */
  startListening: () => void;
  /** Stop listening */
  stopListening: () => void;
  /** Set avatar to thinking state */
  think: () => void;
  /** Reset to idle state */
  idle: () => void;
  /** Set emotion level */
  setEmotion: (level: number) => void;
  /** Whether the avatar is currently speaking */
  isSpeaking: boolean;
  /** Whether the avatar is currently listening */
  isListening: boolean;
}

/**
 * useAvatar Hook
 * 
 * Controls the AI avatar state and TTS/STT integration
 * 
 * Usage:
 * ```tsx
 * const { state, speak, startListening, lipSyncValue } = useAvatar();
 * 
 * // Make avatar speak
 * await speak('안녕하세요! 저는 FLIO의 AI 매니저예요.');
 * 
 * // Start listening for voice input
 * startListening();
 * ```
 */
export function useAvatar(options: UseAvatarOptions = {}): UseAvatarReturn {
  const [state, setState] = useState<AvatarState>('idle');
  const [lipSyncValue, setLipSyncValue] = useState(0);
  const [emotionLevel, setEmotionLevel] = useState(50);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isListening, setIsListening] = useState(false);
  
  const lipSyncInterval = useRef<NodeJS.Timeout | null>(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (lipSyncInterval.current) {
        clearInterval(lipSyncInterval.current);
      }
      Speech.stop();
    };
  }, []);

  /**
   * Make the avatar speak using TTS
   */
  const speak = useCallback(async (text: string): Promise<void> => {
    return new Promise((resolve, reject) => {
      // Stop any current speech
      Speech.stop();
      
      setState('speaking');
      setIsSpeaking(true);
      options.onSpeakStart?.();

      // Simulate lip sync with random values
      // In production, you'd analyze the audio output for actual amplitude
      lipSyncInterval.current = setInterval(() => {
        setLipSyncValue(Math.random() * 100);
      }, 100);

      Speech.speak(text, {
        language: 'ko-KR',
        pitch: 1.0,
        rate: 0.9, // Slightly slower for clarity
        onStart: () => {
          console.log('Speech started');
        },
        onDone: () => {
          if (lipSyncInterval.current) {
            clearInterval(lipSyncInterval.current);
          }
          setLipSyncValue(0);
          setState('idle');
          setIsSpeaking(false);
          options.onSpeakEnd?.();
          resolve();
        },
        onStopped: () => {
          if (lipSyncInterval.current) {
            clearInterval(lipSyncInterval.current);
          }
          setLipSyncValue(0);
          setState('idle');
          setIsSpeaking(false);
          options.onSpeakEnd?.();
          resolve();
        },
        onError: (error) => {
          if (lipSyncInterval.current) {
            clearInterval(lipSyncInterval.current);
          }
          setLipSyncValue(0);
          setState('idle');
          setIsSpeaking(false);
          reject(error);
        },
      });
    });
  }, [options]);

  /**
   * Start listening for user voice input
   */
  const startListening = useCallback(() => {
    setState('listening');
    setIsListening(true);
    options.onListenStart?.();
    
    // TODO: Implement actual STT using expo-speech-recognition or similar
    // For now, we'll just set the state
  }, [options]);

  /**
   * Stop listening
   */
  const stopListening = useCallback(() => {
    setState('idle');
    setIsListening(false);
    options.onListenEnd?.();
  }, [options]);

  /**
   * Set avatar to thinking state
   */
  const think = useCallback(() => {
    setState('thinking');
  }, []);

  /**
   * Reset to idle state
   */
  const idle = useCallback(() => {
    setState('idle');
    setIsSpeaking(false);
    setIsListening(false);
    setLipSyncValue(0);
  }, []);

  /**
   * Set emotion intensity
   */
  const setEmotion = useCallback((level: number) => {
    setEmotionLevel(Math.max(0, Math.min(100, level)));
  }, []);

  return {
    state,
    lipSyncValue,
    emotionLevel,
    speak,
    startListening,
    stopListening,
    think,
    idle,
    setEmotion,
    isSpeaking,
    isListening,
  };
}

export default useAvatar;
