/**
 * Family Background Onboarding Screen (Optional)
 * Collects optional family information for enhanced matching:
 * - Parents occupation, education, status
 * - Sibling information
 * - Family property and location
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { router } from 'expo-router';
import { Picker } from '@react-native-picker/picker';
import { supabase } from '@/services/supabase/client';
import { getCurrentUserId } from '@/services/supabase/client';

type FamilyData = {
  father_occupation: string;
  father_education: string;
  father_alive: boolean;
  mother_occupation: string;
  mother_education: string;
  mother_alive: boolean;
  parents_status: string;
  parents_marital_status: string;
  parents_financial_stability: string;
  sibling_count: string;
  birth_order: string;
  family_property_type: string;
  family_location: string;
};

export default function FamilyBackgroundScreen() {
  const [formData, setFormData] = useState<FamilyData>({
    father_occupation: '',
    father_education: '',
    father_alive: true,
    mother_occupation: '',
    mother_education: '',
    mother_alive: true,
    parents_status: '양친',
    parents_marital_status: '기혼',
    parents_financial_stability: '보통',
    sibling_count: '0',
    birth_order: '1',
    family_property_type: '',
    family_location: '',
  });

  const [loading, setLoading] = useState(false);
  const [userId, setUserId] = useState<string | null>(null);

  useEffect(() => {
    loadUserId();
  }, []);

  const loadUserId = async () => {
    try {
      const id = await getCurrentUserId();
      setUserId(id);
    } catch (error) {
      console.error('Error loading user ID:', error);
      Alert.alert('오류', '사용자 정보를 불러올 수 없습니다.');
      router.replace('/(auth)/login');
    }
  };

  const updateField = (field: keyof FamilyData, value: string | boolean) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSkip = () => {
    // Skip to questions screen
    router.push('/(onboarding)/questions');
  };

  const handleSubmit = async () => {
    if (!userId) {
      Alert.alert('오류', '사용자 정보를 찾을 수 없습니다.');
      return;
    }

    setLoading(true);

    try {
      // Prepare data for database
      const familyData = {
        user_id: userId,
        father_occupation: formData.father_occupation || null,
        father_education: formData.father_education || null,
        father_alive: formData.father_alive,
        mother_occupation: formData.mother_occupation || null,
        mother_education: formData.mother_education || null,
        mother_alive: formData.mother_alive,
        parents_status: formData.parents_status,
        parents_marital_status: formData.parents_marital_status || null,
        parents_financial_stability: formData.parents_financial_stability || null,
        sibling_count: parseInt(formData.sibling_count) || 0,
        sibling_info: [],
        birth_order: parseInt(formData.birth_order) || 1,
        family_property_type: formData.family_property_type || null,
        family_location: formData.family_location || null,
      };

      // Upsert into user_family_background table
      const { error } = await supabase
        .from('user_family_background')
        .upsert(familyData, { onConflict: 'user_id' });

      if (error) throw error;

      // Navigate to questions screen
      router.push('/(onboarding)/questions');
    } catch (error: any) {
      console.error('Error saving family background:', error);
      Alert.alert('오류', '가족 정보 저장 중 문제가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  if (!userId) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#FF6B9D" />
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>가족 배경 (선택)</Text>
      <Text style={styles.subtitle}>
        입력하시면 더 정확한 매칭이 가능합니다{'\n'}
        원하지 않으시면 건너뛰기를 눌러주세요
      </Text>

      {/* Parents Information */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>부모님 정보</Text>

        <Text style={styles.label}>가족 구성</Text>
        <View style={styles.pickerContainer}>
          <Picker
            selectedValue={formData.parents_status}
            onValueChange={(value) => updateField('parents_status', value)}
            style={styles.picker}
          >
            <Picker.Item label="양친" value="양친" />
            <Picker.Item label="한부모(부)" value="한부모(부)" />
            <Picker.Item label="한부모(모)" value="한부모(모)" />
            <Picker.Item label="조부모 양육" value="조부모양육" />
            <Picker.Item label="기타" value="기타" />
          </Picker>
        </View>

        <Text style={styles.label}>부모님 혼인 상태</Text>
        <View style={styles.pickerContainer}>
          <Picker
            selectedValue={formData.parents_marital_status}
            onValueChange={(value) => updateField('parents_marital_status', value)}
            style={styles.picker}
          >
            <Picker.Item label="기혼" value="기혼" />
            <Picker.Item label="이혼" value="이혼" />
            <Picker.Item label="사별" value="사별" />
          </Picker>
        </View>

        <Text style={styles.subSectionTitle}>아버지</Text>

        <Text style={styles.label}>직업</Text>
        <TextInput
          style={styles.input}
          placeholder="예: 회사원"
          value={formData.father_occupation}
          onChangeText={(value) => updateField('father_occupation', value)}
        />

        <Text style={styles.label}>학력</Text>
        <View style={styles.pickerContainer}>
          <Picker
            selectedValue={formData.father_education}
            onValueChange={(value) => updateField('father_education', value)}
            style={styles.picker}
          >
            <Picker.Item label="선택 안함" value="" />
            <Picker.Item label="고졸" value="고졸" />
            <Picker.Item label="전문대졸" value="전문대졸" />
            <Picker.Item label="대졸" value="대졸" />
            <Picker.Item label="석사" value="석사" />
            <Picker.Item label="박사" value="박사" />
          </Picker>
        </View>

        <Text style={styles.subSectionTitle}>어머니</Text>

        <Text style={styles.label}>직업</Text>
        <TextInput
          style={styles.input}
          placeholder="예: 주부"
          value={formData.mother_occupation}
          onChangeText={(value) => updateField('mother_occupation', value)}
        />

        <Text style={styles.label}>학력</Text>
        <View style={styles.pickerContainer}>
          <Picker
            selectedValue={formData.mother_education}
            onValueChange={(value) => updateField('mother_education', value)}
            style={styles.picker}
          >
            <Picker.Item label="선택 안함" value="" />
            <Picker.Item label="고졸" value="고졸" />
            <Picker.Item label="전문대졸" value="전문대졸" />
            <Picker.Item label="대졸" value="대졸" />
            <Picker.Item label="석사" value="석사" />
            <Picker.Item label="박사" value="박사" />
          </Picker>
        </View>

        <Text style={styles.label}>경제적 안정성</Text>
        <View style={styles.pickerContainer}>
          <Picker
            selectedValue={formData.parents_financial_stability}
            onValueChange={(value) => updateField('parents_financial_stability', value)}
            style={styles.picker}
          >
            <Picker.Item label="매우 안정" value="매우안정" />
            <Picker.Item label="안정" value="안정" />
            <Picker.Item label="보통" value="보통" />
            <Picker.Item label="불안정" value="불안정" />
          </Picker>
        </View>
      </View>

      {/* Siblings */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>형제자매</Text>

        <View style={styles.row}>
          <View style={styles.halfInput}>
            <Text style={styles.label}>형제자매 수</Text>
            <TextInput
              style={styles.input}
              placeholder="0"
              keyboardType="numeric"
              value={formData.sibling_count}
              onChangeText={(value) => updateField('sibling_count', value)}
            />
          </View>

          <View style={styles.halfInput}>
            <Text style={styles.label}>출생 순서</Text>
            <TextInput
              style={styles.input}
              placeholder="1"
              keyboardType="numeric"
              value={formData.birth_order}
              onChangeText={(value) => updateField('birth_order', value)}
            />
          </View>
        </View>
      </View>

      {/* Family Assets */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>가족 자산 (민감정보 - 선택)</Text>

        <Text style={styles.label}>주거 형태</Text>
        <View style={styles.pickerContainer}>
          <Picker
            selectedValue={formData.family_property_type}
            onValueChange={(value) => updateField('family_property_type', value)}
            style={styles.picker}
          >
            <Picker.Item label="선택 안함" value="" />
            <Picker.Item label="자가" value="자가" />
            <Picker.Item label="전세" value="전세" />
            <Picker.Item label="월세" value="월세" />
          </Picker>
        </View>

        <Text style={styles.label}>거주 지역</Text>
        <TextInput
          style={styles.input}
          placeholder="예: 서울 강남구"
          value={formData.family_location}
          onChangeText={(value) => updateField('family_location', value)}
        />
      </View>

      {/* Buttons */}
      <TouchableOpacity
        style={[styles.button, loading && styles.buttonDisabled]}
        onPress={handleSubmit}
        disabled={loading}
      >
        {loading ? (
          <ActivityIndicator color="#FFF" />
        ) : (
          <Text style={styles.buttonText}>다음</Text>
        )}
      </TouchableOpacity>

      <TouchableOpacity
        style={styles.skipButton}
        onPress={handleSkip}
      >
        <Text style={styles.skipButtonText}>건너뛰기</Text>
      </TouchableOpacity>

      <View style={styles.spacer} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFF',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#FFF',
  },
  content: {
    padding: 20,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: '#666',
    marginBottom: 24,
    lineHeight: 24,
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: '#333',
    marginBottom: 16,
  },
  subSectionTitle: {
    fontSize: 18,
    fontWeight: '500',
    color: '#333',
    marginTop: 16,
    marginBottom: 12,
  },
  label: {
    fontSize: 14,
    color: '#666',
    marginBottom: 8,
    marginTop: 12,
  },
  input: {
    borderWidth: 1,
    borderColor: '#DDD',
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    color: '#333',
    backgroundColor: '#F9F9F9',
  },
  pickerContainer: {
    borderWidth: 1,
    borderColor: '#DDD',
    borderRadius: 8,
    backgroundColor: '#F9F9F9',
    overflow: 'hidden',
  },
  picker: {
    height: 50,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  halfInput: {
    flex: 1,
    marginHorizontal: 4,
  },
  button: {
    backgroundColor: '#FF6B9D',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    marginTop: 24,
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: {
    color: '#FFF',
    fontSize: 18,
    fontWeight: '600',
  },
  skipButton: {
    padding: 16,
    alignItems: 'center',
    marginTop: 12,
  },
  skipButtonText: {
    color: '#FF6B9D',
    fontSize: 16,
    fontWeight: '600',
  },
  spacer: {
    height: 40,
  },
});
