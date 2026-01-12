import React, { useState } from 'react';
import { TouchableOpacity, Text, StyleSheet, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { voiceAccessibilityService } from '../services/voiceAccessibilityService';

interface VoiceButtonProps {
  onTranscription: (text: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export const VoiceButton: React.FC<VoiceButtonProps> = ({
  onTranscription,
  disabled = false,
  placeholder = "음성 입력"
}) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleVoiceInput = async () => {
    if (disabled) return;

    try {
      if (!isRecording) {
        // Start recording
        await voiceAccessibilityService.startRecording();
        setIsRecording(true);
        await voiceAccessibilityService.speak("음성 입력을 시작합니다");
      } else {
        // Stop recording and transcribe
        setIsRecording(false);
        setIsLoading(true);
        
        const audioUri = await voiceAccessibilityService.stopRecording();
        if (audioUri) {
          const transcription = await voiceAccessibilityService.transcribeAudio(audioUri);
          onTranscription(transcription);
          await voiceAccessibilityService.speak("음성이 인식되었습니다");
        }
      }
    } catch (error) {
      console.error('Voice input error:', error);
      setIsRecording(false);
      await voiceAccessibilityService.speak("음성 인식에 실패했습니다");
    } finally {
      setIsLoading(false);
    }
  };

  const getButtonText = () => {
    if (isLoading) return "처리 중...";
    if (isRecording) return "녹음 중 (탭하여 완료)";
    return "음성 입력";
  };

  const getButtonStyle = () => {
    if (disabled) return [styles.button, styles.disabled];
    if (isRecording) return [styles.button, styles.recording];
    return styles.button;
  };

  return (
    <TouchableOpacity
      style={getButtonStyle()}
      onPress={handleVoiceInput}
      disabled={disabled || isLoading}
      accessibilityLabel={getButtonText()}
      accessibilityRole="button"
    >
      <Text style={styles.buttonText}>
        {getButtonText()}
      </Text>
    </TouchableOpacity>
  );
};

interface SpeakButtonProps {
  text: string;
  options?: string[];
  disabled?: boolean;
}

export const SpeakButton: React.FC<SpeakButtonProps> = ({
  text,
  options = [],
  disabled = false
}) => {
  const [isSpeaking, setIsSpeaking] = useState(false);

  const handleSpeak = async () => {
    if (disabled || !text) return;

    try {
      setIsSpeaking(true);

      // Read the question first
      await voiceAccessibilityService.speak(text);

      // Then read all options if provided
      if (options.length > 0) {
        for (let i = 0; i < options.length; i++) {
          await voiceAccessibilityService.speak(`보기 ${i + 1}: ${options[i]}`);
        }
      }
    } catch (error) {
      console.error('Speech error:', error);
    } finally {
      setIsSpeaking(false);
    }
  };

  return (
    <TouchableOpacity
      style={[styles.speakButton, disabled && styles.disabled, isSpeaking && styles.speaking]}
      onPress={handleSpeak}
      disabled={disabled || isSpeaking}
      accessibilityLabel={isSpeaking ? "읽는 중" : options.length > 0 ? "질문과 보기 전체 듣기" : "텍스트 읽기"}
      accessibilityRole="button"
    >
      <Ionicons
        name={isSpeaking ? "volume-high" : "volume-medium-outline"}
        size={20}
        color="#FFFFFF"
      />
    </TouchableOpacity>
  );
};


const styles = StyleSheet.create({
  button: {
    backgroundColor: '#007AFF',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 8,
    marginTop: 8,
    minHeight: 44,
    justifyContent: 'center',
    alignItems: 'center',
  },
  recording: {
    backgroundColor: '#FF3B30',
  },
  disabled: {
    backgroundColor: '#C7C7CC',
    opacity: 0.6,
  },
  buttonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '500',
    textAlign: 'center',
  },
  speakButton: {
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    width: 36,
    height: 36,
    borderRadius: 18,
    marginLeft: 8,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.3)',
  },
  speaking: {
    backgroundColor: 'rgba(79, 209, 199, 0.3)',
    borderColor: '#4FD1C7',
  },
});