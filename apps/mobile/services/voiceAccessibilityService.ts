import { Audio } from 'expo-av';
import * as Speech from 'expo-speech';
import * as FileSystem from 'expo-file-system';
import { aiQuestionService } from './aiQuestionService';

export interface VoiceSettings {
  enabled: boolean;
  autoReadQuestions: boolean;
  speechRate: number;
  language: string;
}

class VoiceAccessibilityService {
  private recording: Audio.Recording | null = null;
  private settings: VoiceSettings = {
    enabled: false,
    autoReadQuestions: false,
    speechRate: 0.8,
    language: 'ko-KR'
  };

  async initialize(): Promise<void> {
    const { status } = await Audio.requestPermissionsAsync();
    if (status !== 'granted') {
      throw new Error('Audio permission not granted');
    }
  }

  getSettings(): VoiceSettings {
    return this.settings;
  }

  updateSettings(newSettings: Partial<VoiceSettings>): void {
    this.settings = { ...this.settings, ...newSettings };
  }

  async speak(text: string): Promise<void> {
    if (!this.settings.enabled) return;

    return new Promise((resolve) => {
      Speech.speak(text, {
        language: this.settings.language,
        rate: this.settings.speechRate,
        pitch: 1.0,
        onDone: () => resolve(),
        onError: () => resolve()
      });
    });
  }

  stopSpeaking(): void {
    Speech.stop();
  }

  async startRecording(): Promise<void> {
    try {
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });

      const recordingOptions = Audio.RecordingOptionsPresets.HIGH_QUALITY;
      const { recording } = await Audio.Recording.createAsync(recordingOptions);
      this.recording = recording;
    } catch (error) {
      console.error('Failed to start recording:', error);
      throw error;
    }
  }

  async stopRecording(): Promise<string | null> {
    if (!this.recording) return null;

    try {
      await this.recording.stopAndUnloadAsync();
      const uri = this.recording.getURI();
      this.recording = null;
      return uri;
    } catch (error) {
      console.error('Failed to stop recording:', error);
      return null;
    }
  }

  async transcribeAudio(audioUri: string): Promise<string> {
    try {
      // Create form data for audio file
      const formData = new FormData();
      formData.append('file', {
        uri: audioUri,
        type: 'audio/m4a',
        name: 'recording.m4a',
      } as any);
      formData.append('model', 'whisper-1');
      formData.append('language', 'ko');

      // Send to backend for transcription
      const baseUrl = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
      const response = await fetch(`${baseUrl}/voice/transcribe`, {
        method: 'POST',
        body: formData,
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      if (!response.ok) {
        throw new Error(`Transcription failed: ${response.status}`);
      }

      const result = await response.json();
      return result.text || '';
    } catch (error) {
      console.error('Transcription error:', error);
      throw new Error('음성 인식에 실패했습니다.');
    }
  }

  async readQuestion(questionText: string): Promise<void> {
    await this.speak(questionText);
  }

  async readQuestionOptions(options: string[]): Promise<void> {
    if (!options || options.length === 0) return;

    await this.speak('선택지를 읽어드릴게요');
    
    for (let i = 0; i < options.length; i++) {
      await this.speak(`${i + 1}번. ${options[i]}`);
    }
  }

  async confirmAnswer(answer: string): Promise<void> {
    await this.speak(`답변을 저장했습니다. ${answer}`);
  }

  async announceProgress(current: number, total: number): Promise<void> {
    await this.speak(`${total}개 질문 중 ${current}번째 질문입니다`);
  }

  async announceMatchResults(count: number): Promise<void> {
    await this.speak(`${count}명의 매칭 결과를 찾았습니다`);
  }

  async readMatchExplanation(explanation: string): Promise<void> {
    await this.speak(explanation);
  }
}

export const voiceAccessibilityService = new VoiceAccessibilityService();