/**
 * Extended Profile Onboarding Screen
 * Collects detailed information for Korean marriage agency style matching:
 * - Physical info (height, weight)
 * - Education (level, university, major, graduation year)
 * - Career (employment status, company, job title, industry, income)
 * - Marital history (status, children)
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

type FormData = {
  height_cm: string;
  weight_kg: string;
  education_level: string;
  university_name: string;
  major: string;
  graduation_year: string;
  employment_status: string;
  company_name: string;
  job_title: string;
  industry: string;
  annual_income_range: string;
  marital_status: string;
  divorce_reason: string;
  has_children: boolean;
  children_count: string;
};

export default function ExtendedProfileScreen() {
  const [formData, setFormData] = useState<FormData>({
    height_cm: '',
    weight_kg: '',
    education_level: '',
    university_name: '',
    major: '',
    graduation_year: '',
    employment_status: '',
    company_name: '',
    job_title: '',
    industry: '',
    annual_income_range: '',
    marital_status: '미혼',
    divorce_reason: '',
    has_children: false,
    children_count: '0',
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

  const updateField = (field: keyof FormData, value: string | boolean) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async () => {
    if (!userId) {
      Alert.alert('오류', '사용자 정보를 찾을 수 없습니다.');
      return;
    }

    // Validation
    if (!formData.education_level) {
      Alert.alert('필수 입력', '학력을 선택해주세요.');
      return;
    }

    if (!formData.employment_status) {
      Alert.alert('필수 입력', '고용 상태를 선택해주세요.');
      return;
    }

    setLoading(true);

    try {
      // Prepare data for database
      const profileData: any = {
        height_cm: formData.height_cm ? parseInt(formData.height_cm) : null,
        weight_kg: formData.weight_kg ? parseInt(formData.weight_kg) : null,
        education_level: formData.education_level,
        university_name: formData.university_name || null,
        major: formData.major || null,
        graduation_year: formData.graduation_year ? parseInt(formData.graduation_year) : null,
        employment_status: formData.employment_status,
        company_name: formData.company_name || null,
        job_title: formData.job_title || null,
        industry: formData.industry || null,
        annual_income_range: formData.annual_income_range || null,
        marital_status: formData.marital_status,
        divorce_reason: formData.divorce_reason || null,
        has_children: formData.has_children,
        children_count: formData.has_children ? parseInt(formData.children_count) : 0,
      };

      // Update profile in Supabase
      const { error } = await supabase
        .from('profiles')
        .update(profileData)
        .eq('user_id', userId);

      if (error) throw error;

      // Navigate to next screen (family background - optional)
      router.push('/(onboarding)/family-background');
    } catch (error: any) {
      console.error('Error saving profile:', error);
      Alert.alert('오류', '프로필 저장 중 문제가 발생했습니다.');
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
      <Text style={styles.title}>추가 프로필 정보</Text>
      <Text style={styles.subtitle}>
        더 정확한 매칭을 위한 상세 정보를 입력해주세요
      </Text>

      {/* Physical Information */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>신체 정보 (선택)</Text>

        <View style={styles.row}>
          <View style={styles.halfInput}>
            <Text style={styles.label}>키 (cm)</Text>
            <TextInput
              style={styles.input}
              placeholder="170"
              keyboardType="numeric"
              value={formData.height_cm}
              onChangeText={(value) => updateField('height_cm', value)}
            />
          </View>

          <View style={styles.halfInput}>
            <Text style={styles.label}>몸무게 (kg) (선택)</Text>
            <TextInput
              style={styles.input}
              placeholder="65"
              keyboardType="numeric"
              value={formData.weight_kg}
              onChangeText={(value) => updateField('weight_kg', value)}
            />
          </View>
        </View>
      </View>

      {/* Education */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>학력 *</Text>

        <Text style={styles.label}>최종 학력</Text>
        <View style={styles.pickerContainer}>
          <Picker
            selectedValue={formData.education_level}
            onValueChange={(value) => updateField('education_level', value)}
            style={styles.picker}
          >
            <Picker.Item label="선택해주세요" value="" />
            <Picker.Item label="고졸" value="고졸" />
            <Picker.Item label="전문대졸" value="전문대졸" />
            <Picker.Item label="대졸" value="대졸" />
            <Picker.Item label="석사" value="석사" />
            <Picker.Item label="박사" value="박사" />
          </Picker>
        </View>

        <Text style={styles.label}>대학교명 (선택)</Text>
        <TextInput
          style={styles.input}
          placeholder="예: 서울대학교"
          value={formData.university_name}
          onChangeText={(value) => updateField('university_name', value)}
        />

        <Text style={styles.label}>전공 (선택)</Text>
        <TextInput
          style={styles.input}
          placeholder="예: 경영학"
          value={formData.major}
          onChangeText={(value) => updateField('major', value)}
        />

        <Text style={styles.label}>졸업 연도 (선택)</Text>
        <TextInput
          style={styles.input}
          placeholder="예: 2020"
          keyboardType="numeric"
          value={formData.graduation_year}
          onChangeText={(value) => updateField('graduation_year', value)}
        />
      </View>

      {/* Career & Income */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>직업 및 소득 *</Text>

        <Text style={styles.label}>고용 상태</Text>
        <View style={styles.pickerContainer}>
          <Picker
            selectedValue={formData.employment_status}
            onValueChange={(value) => updateField('employment_status', value)}
            style={styles.picker}
          >
            <Picker.Item label="선택해주세요" value="" />
            <Picker.Item label="정규직" value="정규직" />
            <Picker.Item label="계약직" value="계약직" />
            <Picker.Item label="자영업" value="자영업" />
            <Picker.Item label="프리랜서" value="프리랜서" />
            <Picker.Item label="공무원" value="공무원" />
            <Picker.Item label="전문직" value="전문직" />
            <Picker.Item label="학생" value="학생" />
            <Picker.Item label="무직" value="무직" />
          </Picker>
        </View>

        {formData.employment_status && formData.employment_status !== '무직' && formData.employment_status !== '학생' && (
          <>
            <Text style={styles.label}>회사명 (선택)</Text>
            <TextInput
              style={styles.input}
              placeholder="예: 삼성전자"
              value={formData.company_name}
              onChangeText={(value) => updateField('company_name', value)}
            />

            <Text style={styles.label}>직책 (선택)</Text>
            <TextInput
              style={styles.input}
              placeholder="예: 소프트웨어 엔지니어"
              value={formData.job_title}
              onChangeText={(value) => updateField('job_title', value)}
            />

            <Text style={styles.label}>산업 (선택)</Text>
            <TextInput
              style={styles.input}
              placeholder="예: IT/소프트웨어"
              value={formData.industry}
              onChangeText={(value) => updateField('industry', value)}
            />

            <Text style={styles.label}>연봉 범위 (선택)</Text>
            <View style={styles.pickerContainer}>
              <Picker
                selectedValue={formData.annual_income_range}
                onValueChange={(value) => updateField('annual_income_range', value)}
                style={styles.picker}
              >
                <Picker.Item label="선택 안함" value="" />
                <Picker.Item label="~3천만원" value="~3천만" />
                <Picker.Item label="3천만~5천만원" value="3천만~5천만" />
                <Picker.Item label="5천만~7천만원" value="5천만~7천만" />
                <Picker.Item label="7천만~1억원" value="7천만~1억" />
                <Picker.Item label="1억~1.5억원" value="1억~1.5억" />
                <Picker.Item label="1.5억~2억원" value="1.5억~2억" />
                <Picker.Item label="2억원 이상" value="2억~" />
              </Picker>
            </View>
          </>
        )}
      </View>

      {/* Marital History */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>혼인 이력 *</Text>

        <Text style={styles.label}>혼인 상태</Text>
        <View style={styles.pickerContainer}>
          <Picker
            selectedValue={formData.marital_status}
            onValueChange={(value) => updateField('marital_status', value)}
            style={styles.picker}
          >
            <Picker.Item label="미혼" value="미혼" />
            <Picker.Item label="이혼" value="이혼" />
            <Picker.Item label="사별" value="사별" />
          </Picker>
        </View>

        {formData.marital_status === '이혼' && (
          <>
            <Text style={styles.label}>이혼 사유 (선택)</Text>
            <TextInput
              style={[styles.input, styles.multiline]}
              placeholder="간단히 입력해주세요"
              multiline
              numberOfLines={3}
              value={formData.divorce_reason}
              onChangeText={(value) => updateField('divorce_reason', value)}
            />
          </>
        )}

        {(formData.marital_status === '이혼' || formData.marital_status === '사별') && (
          <>
            <View style={styles.checkboxRow}>
              <TouchableOpacity
                style={styles.checkbox}
                onPress={() => updateField('has_children', !formData.has_children)}
              >
                <View style={[
                  styles.checkboxBox,
                  formData.has_children && styles.checkboxBoxChecked
                ]}>
                  {formData.has_children && <Text style={styles.checkmark}>✓</Text>}
                </View>
                <Text style={styles.checkboxLabel}>자녀가 있습니다</Text>
              </TouchableOpacity>
            </View>

            {formData.has_children && (
              <>
                <Text style={styles.label}>자녀 수</Text>
                <TextInput
                  style={styles.input}
                  placeholder="1"
                  keyboardType="numeric"
                  value={formData.children_count}
                  onChangeText={(value) => updateField('children_count', value)}
                />
              </>
            )}
          </>
        )}
      </View>

      {/* Submit Button */}
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
  multiline: {
    height: 80,
    textAlignVertical: 'top',
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
  checkboxRow: {
    marginTop: 12,
  },
  checkbox: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  checkboxBox: {
    width: 24,
    height: 24,
    borderWidth: 2,
    borderColor: '#DDD',
    borderRadius: 4,
    marginRight: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  checkboxBoxChecked: {
    backgroundColor: '#FF6B9D',
    borderColor: '#FF6B9D',
  },
  checkmark: {
    color: '#FFF',
    fontSize: 16,
    fontWeight: 'bold',
  },
  checkboxLabel: {
    fontSize: 16,
    color: '#333',
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
  spacer: {
    height: 40,
  },
});
