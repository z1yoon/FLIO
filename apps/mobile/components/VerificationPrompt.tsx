/**
 * Verification Prompt Modal
 * Shown when users with low trust tiers try to access premium features
 * Encourages document verification to unlock better matches
 */

import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Modal } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';

interface VerificationPromptProps {
  visible: boolean;
  currentTier: string;
  onClose: () => void;
  onVerify: () => void;
}

export default function VerificationPrompt({
  visible,
  currentTier,
  onClose,
  onVerify
}: VerificationPromptProps) {
  const getTierInfo = (tier: string) => {
    const tierMap: Record<string, { emoji: string; name: string; limitation: string }> = {
      pebble: {
        emoji: '🪨',
        name: '조약돌 회원',
        limitation: '조약돌 회원만 매칭 가능'
      },
      shell: {
        emoji: '🐚',
        name: '조개 회원',
        limitation: '조개급 이하 회원 매칭 가능'
      },
      pearl: {
        emoji: '🫧',
        name: '진주 회원',
        limitation: '진주급 이하 회원 매칭 가능'
      },
      coral: {
        emoji: '🪸',
        name: '산호 회원',
        limitation: '모든 회원 매칭 가능'
      }
    };
    return tierMap[tier] || tierMap['pebble'];
  };

  const tierInfo = getTierInfo(currentTier);

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={onClose}
    >
      <View style={styles.overlay}>
        <View style={styles.modalContainer}>
          <LinearGradient
            colors={['#2E7D7A', '#4FD1C7']}
            style={styles.modalGradient}
          />

          <TouchableOpacity style={styles.closeButton} onPress={onClose}>
            <Ionicons name="close" size={24} color="#FFFFFF" />
          </TouchableOpacity>

          {/* Tier Icon */}
          <View style={styles.iconContainer}>
            <Text style={styles.tierEmoji}>{tierInfo.emoji}</Text>
          </View>

          {/* Title */}
          <Text style={styles.title}>신뢰도 인증이 필요합니다</Text>

          {/* Current Status */}
          <View style={styles.statusCard}>
            <Text style={styles.statusLabel}>현재 등급</Text>
            <Text style={styles.statusValue}>{tierInfo.name}</Text>
            <Text style={styles.statusLimitation}>{tierInfo.limitation}</Text>
          </View>

          {/* Benefits */}
          <View style={styles.benefitsSection}>
            <Text style={styles.benefitsTitle}>인증 혜택</Text>
            <View style={styles.benefitsList}>
              <View style={styles.benefitItem}>
                <Ionicons name="checkmark-circle" size={20} color="#4FD1C7" />
                <Text style={styles.benefitText}>더 많은 검증된 회원과 매칭</Text>
              </View>
              <View style={styles.benefitItem}>
                <Ionicons name="checkmark-circle" size={20} color="#4FD1C7" />
                <Text style={styles.benefitText}>프로필 신뢰도 상승</Text>
              </View>
              <View style={styles.benefitItem}>
                <Ionicons name="checkmark-circle" size={20} color="#4FD1C7" />
                <Text style={styles.benefitText}>우선 매칭 기회</Text>
              </View>
              <View style={styles.benefitItem}>
                <Ionicons name="checkmark-circle" size={20} color="#4FD1C7" />
                <Text style={styles.benefitText}>더 많은 매칭 조회 가능</Text>
              </View>
            </View>
          </View>

          {/* Action Buttons */}
          <View style={styles.actionButtons}>
            <TouchableOpacity
              style={styles.laterButton}
              onPress={onClose}
              activeOpacity={0.8}
            >
              <Text style={styles.laterButtonText}>나중에</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.verifyButton}
              onPress={onVerify}
              activeOpacity={0.8}
            >
              <LinearGradient
                colors={['#00FFC8', '#00D4AA']}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 0 }}
                style={styles.verifyButtonGradient}
              >
                <Text style={styles.verifyButtonText}>지금 인증하기</Text>
                <Ionicons name="arrow-forward" size={18} color="#FFFFFF" />
              </LinearGradient>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.7)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  modalContainer: {
    width: '100%',
    maxWidth: 400,
    backgroundColor: '#2E7D7A',
    borderRadius: 24,
    padding: 24,
    alignItems: 'center',
  },
  modalGradient: {
    ...StyleSheet.absoluteFillObject,
    borderRadius: 24,
  },
  closeButton: {
    position: 'absolute',
    top: 16,
    right: 16,
    zIndex: 1,
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: 'rgba(255,255,255,0.15)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconContainer: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: 'rgba(255,255,255,0.15)',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 24,
    marginTop: 8,
  },
  tierEmoji: {
    fontSize: 40,
  },
  title: {
    fontSize: 22,
    fontWeight: '700',
    color: '#FFFFFF',
    textAlign: 'center',
    marginBottom: 24,
  },
  statusCard: {
    width: '100%',
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 16,
    padding: 20,
    marginBottom: 24,
    alignItems: 'center',
  },
  statusLabel: {
    fontSize: 13,
    color: 'rgba(255,255,255,0.7)',
    marginBottom: 8,
  },
  statusValue: {
    fontSize: 20,
    fontWeight: '700',
    color: '#FFFFFF',
    marginBottom: 12,
  },
  statusLimitation: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.8)',
    textAlign: 'center',
  },
  benefitsSection: {
    width: '100%',
    marginBottom: 24,
  },
  benefitsTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#FFFFFF',
    marginBottom: 16,
  },
  benefitsList: {
    gap: 12,
  },
  benefitItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  benefitText: {
    fontSize: 15,
    color: 'rgba(255,255,255,0.9)',
    flex: 1,
  },
  actionButtons: {
    width: '100%',
    flexDirection: 'row',
    gap: 12,
  },
  laterButton: {
    flex: 1,
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 16,
    paddingVertical: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  laterButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: 'rgba(255,255,255,0.8)',
  },
  verifyButton: {
    flex: 2,
  },
  verifyButtonGradient: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 16,
    paddingVertical: 16,
    gap: 8,
  },
  verifyButtonText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#FFFFFF',
  },
});
