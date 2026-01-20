/**
 * Document Verification Screen
 * Accessible from account settings to upload verification documents
 * - ID Card (주민등록증, 운전면허증, 여권)
 * - Diploma (졸업증명서)
 * - Income Certificate (소득금액증명원)
 * - Employment Certificate (재직증명서)
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  Image,
  SafeAreaView,
} from 'react-native';
import { router } from 'expo-router';
import * as ImagePicker from 'expo-image-picker';
import { supabase } from '../services/supabase/client';
import { getCurrentUserId } from '../services/supabase/client';
import { LinearGradient } from 'expo-linear-gradient';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';

type DocumentType = 'id_card' | 'diploma' | 'income_cert' | 'employment_cert';

type DocumentItem = {
  type: DocumentType;
  label: string;
  description: string;
  icon: string;
  uploaded: boolean;
  status?: 'pending' | 'processing' | 'verified' | 'flagged' | 'rejected';
  documentId?: string;
  fileUrl?: string;
};

export default function DocumentVerificationScreen() {
  const [documents, setDocuments] = useState<DocumentItem[]>([
    {
      type: 'id_card',
      label: '신분증',
      description: '주민등록증, 운전면허증, 여권',
      icon: '🪪',
      uploaded: false,
    },
    {
      type: 'diploma',
      label: '졸업증명서',
      description: '대학교 졸업증명서 또는 학위증명서',
      icon: '🎓',
      uploaded: false,
    },
    {
      type: 'income_cert',
      label: '소득금액증명원',
      description: '국세청 발급 소득증명서',
      icon: '💰',
      uploaded: false,
    },
    {
      type: 'employment_cert',
      label: '재직증명서',
      description: '회사 발급 재직증명서',
      icon: '💼',
      uploaded: false,
    },
  ]);

  const [loading, setLoading] = useState(false);
  const [uploadingType, setUploadingType] = useState<DocumentType | null>(null);
  const [userId, setUserId] = useState<string | null>(null);

  useEffect(() => {
    loadUserId();
    loadExistingDocuments();
    requestPermissions();
  }, []);

  const loadUserId = async () => {
    try {
      const id = await getCurrentUserId();
      setUserId(id);
    } catch (error) {
      console.error('Error loading user ID:', error);
      Alert.alert('오류', '사용자 정보를 불러올 수 없습니다.');
      router.back();
    }
  };

  const loadExistingDocuments = async () => {
    try {
      const id = await getCurrentUserId();
      const { data: docsData } = await supabase
        .from('user_documents')
        .select('document_type, verification_status, file_url, id')
        .eq('user_id', id);

      if (docsData && docsData.length > 0) {
        setDocuments(prev =>
          prev.map(doc => {
            const existingDoc = docsData.find(d => d.document_type === doc.type);
            if (existingDoc) {
              return {
                ...doc,
                uploaded: true,
                status: existingDoc.verification_status as any,
                documentId: existingDoc.id,
                fileUrl: existingDoc.file_url,
              };
            }
            return doc;
          })
        );
      }
    } catch (error) {
      console.error('Error loading existing documents:', error);
    }
  };

  const requestPermissions = async () => {
    const { status: cameraStatus } = await ImagePicker.requestCameraPermissionsAsync();
    const { status: mediaStatus } = await ImagePicker.requestMediaLibraryPermissionsAsync();

    if (cameraStatus !== 'granted' || mediaStatus !== 'granted') {
      Alert.alert(
        '권한 필요',
        '카메라 및 사진 라이브러리 접근 권한이 필요합니다.'
      );
    }
  };

  const pickImage = async (documentType: DocumentType) => {
    try {
      Alert.alert(
        '사진 선택',
        '문서 사진을 어떻게 업로드하시겠습니까?',
        [
          {
            text: '카메라로 촬영',
            onPress: () => launchCamera(documentType),
          },
          {
            text: '갤러리에서 선택',
            onPress: () => launchGallery(documentType),
          },
          {
            text: '취소',
            style: 'cancel',
          },
        ]
      );
    } catch (error) {
      console.error('Error picking image:', error);
    }
  };

  const launchCamera = async (documentType: DocumentType) => {
    try {
      const result = await ImagePicker.launchCameraAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        quality: 0.8,
        allowsEditing: true,
        aspect: [4, 3],
      });

      if (!result.canceled && result.assets[0]) {
        await uploadDocument(documentType, result.assets[0].uri);
      }
    } catch (error) {
      console.error('Error launching camera:', error);
      Alert.alert('오류', '카메라를 열 수 없습니다.');
    }
  };

  const launchGallery = async (documentType: DocumentType) => {
    try {
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        quality: 0.8,
        allowsEditing: true,
        aspect: [4, 3],
      });

      if (!result.canceled && result.assets[0]) {
        await uploadDocument(documentType, result.assets[0].uri);
      }
    } catch (error) {
      console.error('Error launching gallery:', error);
      Alert.alert('오류', '갤러리를 열 수 없습니다.');
    }
  };

  const uploadDocument = async (documentType: DocumentType, imageUri: string) => {
    if (!userId) {
      Alert.alert('오류', '사용자 정보를 찾을 수 없습니다.');
      return;
    }

    setUploadingType(documentType);
    setLoading(true);

    try {
      // 1. Convert URI to blob
      const response = await fetch(imageUri);
      const blob = await response.blob();

      // 2. Upload to Supabase Storage
      const fileName = `${userId}/${documentType}_${Date.now()}.jpg`;
      const { data: uploadData, error: uploadError } = await supabase.storage
        .from('flio-documents')
        .upload(fileName, blob, {
          contentType: 'image/jpeg',
          upsert: false,
        });

      if (uploadError) throw uploadError;

      // 3. Get public URL
      const { data: urlData } = supabase.storage
        .from('flio-documents')
        .getPublicUrl(fileName);

      if (!urlData?.publicUrl) {
        throw new Error('Failed to get public URL');
      }

      // 4. Call backend OCR verification API
      const apiUrl = process.env.EXPO_PUBLIC_AI_BACKEND_URL || 'http://localhost:8000';
      const verificationResponse = await fetch(`${apiUrl}/api/v1/verification/document/upload`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId,
          document_type: documentType,
          file_url: urlData.publicUrl,
        }),
      });

      if (!verificationResponse.ok) {
        throw new Error('Verification API failed');
      }

      const verificationResult = await verificationResponse.json();

      // 5. Update UI
      setDocuments(prev =>
        prev.map(doc =>
          doc.type === documentType
            ? {
                ...doc,
                uploaded: true,
                status: 'processing',
                documentId: verificationResult.document_id,
                fileUrl: urlData.publicUrl,
              }
            : doc
        )
      );

      Alert.alert('업로드 완료', '문서가 업로드되어 검증 중입니다.');

      // Reload documents to get latest status
      await loadExistingDocuments();
    } catch (error: any) {
      console.error('Error uploading document:', error);
      Alert.alert('오류', '문서 업로드 중 문제가 발생했습니다.');
    } finally {
      setLoading(false);
      setUploadingType(null);
    }
  };

  const handleBack = () => {
    router.back();
  };

  const getStatusBadge = (status?: string) => {
    switch (status) {
      case 'processing':
        return { text: '검증 중', color: '#FFA500' };
      case 'verified':
        return { text: '✓ 인증됨', color: '#4CAF50' };
      case 'flagged':
        return { text: '⚠ 확인 필요', color: '#FF9800' };
      case 'rejected':
        return { text: '✗ 거부됨', color: '#F44336' };
      default:
        return null;
    }
  };

  if (!userId) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#4FD1C7" />
      </View>
    );
  }

  const uploadedCount = documents.filter(d => d.uploaded).length;

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="light" />

      <LinearGradient
        colors={['#2E7D7A', '#4FD1C7', '#7EDDD9']}
        style={styles.backgroundGradient}
      />

      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity
          style={styles.backButton}
          onPress={handleBack}
          activeOpacity={0.7}
        >
          <Ionicons name="chevron-back" size={24} color="#FFFFFF" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>문서 인증</Text>
        <View style={styles.headerSpacer} />
      </View>

      <ScrollView style={styles.scrollView} contentContainerStyle={styles.content}>
        <Text style={styles.subtitle}>
          신뢰도 점수를 높이기 위해 문서를 업로드하세요{'\n'}
          더 많은 매칭 기회를 얻을 수 있습니다
        </Text>

        <View style={styles.statsCard}>
          <Text style={styles.statsText}>
            업로드된 문서: {uploadedCount}/4
          </Text>
          {uploadedCount > 0 && (
            <Text style={styles.statsSubtext}>
              신뢰도 점수가 향상됩니다 ✨
            </Text>
          )}
        </View>

        {/* Document Cards */}
        {documents.map((doc) => {
          const statusBadge = getStatusBadge(doc.status);
          const isUploading = uploadingType === doc.type && loading;

          return (
            <View key={doc.type} style={styles.documentCard}>
              <View style={styles.documentHeader}>
                <View style={styles.documentInfo}>
                  <Text style={styles.documentIcon}>{doc.icon}</Text>
                  <View style={styles.documentText}>
                    <Text style={styles.documentLabel}>{doc.label}</Text>
                    <Text style={styles.documentDescription}>{doc.description}</Text>
                  </View>
                </View>

                {statusBadge && (
                  <View style={[styles.statusBadge, { backgroundColor: statusBadge.color }]}>
                    <Text style={styles.statusText}>{statusBadge.text}</Text>
                  </View>
                )}
              </View>

              {doc.uploaded && doc.fileUrl && (
                <Image
                  source={{ uri: doc.fileUrl }}
                  style={styles.documentPreview}
                  resizeMode="cover"
                />
              )}

              <TouchableOpacity
                style={[
                  styles.uploadButton,
                  doc.uploaded && styles.uploadButtonUploaded,
                  isUploading && styles.uploadButtonDisabled,
                ]}
                onPress={() => pickImage(doc.type)}
                disabled={isUploading}
              >
                {isUploading ? (
                  <ActivityIndicator color="#FFF" size="small" />
                ) : (
                  <Text style={styles.uploadButtonText}>
                    {doc.uploaded ? '다시 업로드' : '업로드'}
                  </Text>
                )}
              </TouchableOpacity>
            </View>
          );
        })}

        {/* Info Box */}
        <View style={styles.infoBox}>
          <Text style={styles.infoTitle}>💡 인증 팁</Text>
          <Text style={styles.infoText}>
            • 문서가 선명하게 보이도록 촬영해주세요{'\n'}
            • 모든 텍스트가 읽을 수 있어야 합니다{'\n'}
            • 개인정보는 안전하게 암호화되어 저장됩니다{'\n'}
            • 문서 인증 후 신뢰도 점수가 상승합니다
          </Text>
        </View>

        <View style={styles.spacer} />
      </ScrollView>
    </SafeAreaView>
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
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingVertical: 16,
    paddingTop: 20,
  },
  backButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(255,255,255,0.1)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  headerSpacer: {
    width: 40,
  },
  scrollView: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#2E7D7A',
  },
  content: {
    padding: 20,
  },
  subtitle: {
    fontSize: 16,
    color: 'rgba(255,255,255,0.9)',
    marginBottom: 24,
    lineHeight: 24,
  },
  statsCard: {
    backgroundColor: 'rgba(255,255,255,0.15)',
    borderRadius: 12,
    padding: 16,
    marginBottom: 24,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.2)',
  },
  statsText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#FFFFFF',
    marginBottom: 4,
  },
  statsSubtext: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.8)',
  },
  documentCard: {
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.2)',
  },
  documentHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  documentInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  documentIcon: {
    fontSize: 32,
    marginRight: 12,
  },
  documentText: {
    flex: 1,
  },
  documentLabel: {
    fontSize: 18,
    fontWeight: '600',
    color: '#FFFFFF',
    marginBottom: 4,
  },
  documentDescription: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.7)',
  },
  statusBadge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
  },
  statusText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#FFF',
  },
  documentPreview: {
    width: '100%',
    height: 150,
    borderRadius: 8,
    marginBottom: 12,
    backgroundColor: 'rgba(255,255,255,0.1)',
  },
  uploadButton: {
    backgroundColor: '#4FD1C7',
    borderRadius: 8,
    padding: 12,
    alignItems: 'center',
  },
  uploadButtonUploaded: {
    backgroundColor: 'rgba(255,255,255,0.2)',
  },
  uploadButtonDisabled: {
    opacity: 0.6,
  },
  uploadButtonText: {
    color: '#FFF',
    fontSize: 16,
    fontWeight: '600',
  },
  infoBox: {
    backgroundColor: 'rgba(255,237,153,0.2)',
    borderRadius: 12,
    padding: 16,
    marginTop: 8,
    marginBottom: 24,
    borderWidth: 1,
    borderColor: 'rgba(255,237,153,0.3)',
  },
  infoTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFFFFF',
    marginBottom: 8,
  },
  infoText: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.8)',
    lineHeight: 22,
  },
  spacer: {
    height: 40,
  },
});
