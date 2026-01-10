import React, { useState, useEffect } from 'react';
import { View, Text, Switch, StyleSheet } from 'react-native';
import { voiceAccessibilityService, VoiceSettings } from '../services/voiceAccessibilityService';

export const VoiceSettingsComponent: React.FC = () => {
  const [settings, setSettings] = useState<VoiceSettings>(
    voiceAccessibilityService.getSettings()
  );

  useEffect(() => {
    voiceAccessibilityService.updateSettings(settings);
  }, [settings]);

  const updateSetting = (key: keyof VoiceSettings, value: any) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>음성 접근성 설정</Text>
      
      <View style={styles.settingRow}>
        <Text style={styles.settingLabel}>음성 기능 사용</Text>
        <Switch
          value={settings.enabled}
          onValueChange={(value) => updateSetting('enabled', value)}
          accessibilityLabel="음성 기능 사용 여부"
        />
      </View>

      <View style={styles.settingRow}>
        <Text style={styles.settingLabel}>질문 자동 읽기</Text>
        <Switch
          value={settings.autoReadQuestions}
          onValueChange={(value) => updateSetting('autoReadQuestions', value)}
          disabled={!settings.enabled}
          accessibilityLabel="질문 자동 읽기 여부"
        />
      </View>

      <Text style={styles.description}>
        음성 기능을 켜면 질문을 들을 수 있고, 음성으로 답변할 수 있습니다.
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    padding: 16,
    backgroundColor: 'white',
    borderRadius: 8,
    marginVertical: 8,
  },
  title: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 16,
    color: '#333',
  },
  settingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F0F0',
  },
  settingLabel: {
    fontSize: 16,
    color: '#333',
    flex: 1,
  },
  description: {
    fontSize: 14,
    color: '#666',
    marginTop: 12,
    lineHeight: 20,
  },
});