/**
 * Trust Badge Component - Ocean Pearl Theme
 * FLIO의 바다 보물 등급 시스템
 *
 * Tiers (Ocean Treasure Theme):
 * - Diamond (💎): 다이아 - 80-100% (Elite)
 * - Coral (🪸): 산호 - 60-79% (Premium)
 * - Pearl (🫧): 진주 - 40-59% (Standard)
 * - Shell (🐚): 조개 - 20-39% (Basic)
 * - Pebble (🪨): 조약돌 - 0-19% (Starter)
 */

import React from 'react';
import { View, Text, StyleSheet, ViewStyle } from 'react-native';

type TrustTier = 'diamond' | 'coral' | 'pearl' | 'shell' | 'pebble';
type BadgeSize = 'small' | 'medium' | 'large';

interface TrustBadgeProps {
  tier: TrustTier;
  size?: BadgeSize;
  style?: ViewStyle;
  showLabel?: boolean;
}

interface BadgeConfig {
  emoji: string;
  color: string;
  backgroundColor: string;
  borderColor: string;
  label: string;
  labelShort: string;
}

const BADGE_CONFIGS: Record<TrustTier, BadgeConfig> = {
  diamond: {
    emoji: '💎',
    color: '#1E3A8A',
    backgroundColor: 'rgba(147, 197, 253, 0.25)',
    borderColor: '#93C5FD',
    label: '다이아 회원',
    labelShort: '다이아',
  },
  coral: {
    emoji: '🪸',
    color: '#92400E',
    backgroundColor: 'rgba(255, 215, 0, 0.2)',
    borderColor: '#FFD700',
    label: '산호 회원',
    labelShort: '산호',
  },
  pearl: {
    emoji: '🫧',
    color: '#1F2937',
    backgroundColor: 'rgba(192, 192, 192, 0.25)',
    borderColor: '#C0C0C0',
    label: '진주 회원',
    labelShort: '진주',
  },
  shell: {
    emoji: '🐚',
    color: '#78350F',
    backgroundColor: 'rgba(205, 127, 50, 0.2)',
    borderColor: '#CD7F32',
    label: '조개 회원',
    labelShort: '조개',
  },
  pebble: {
    emoji: '🪨',
    color: '#6B7280',
    backgroundColor: 'rgba(158, 158, 158, 0.15)',
    borderColor: '#9E9E9E',
    label: '조약돌 회원',
    labelShort: '조약돌',
  },
};

const SIZE_CONFIGS = {
  small: {
    emojiSize: 12,
    fontSize: 10,
    padding: 4,
    borderRadius: 8,
    height: 24,
  },
  medium: {
    emojiSize: 16,
    fontSize: 12,
    padding: 6,
    borderRadius: 10,
    height: 28,
  },
  large: {
    emojiSize: 24,
    fontSize: 16,
    padding: 10,
    borderRadius: 12,
    height: 44,
  },
};

export default function TrustBadge({
  tier,
  size = 'medium',
  style,
  showLabel = true,
}: TrustBadgeProps) {
  const badgeConfig = BADGE_CONFIGS[tier];
  const sizeConfig = SIZE_CONFIGS[size];

  const label = size === 'small' ? badgeConfig.labelShort : badgeConfig.label;

  return (
    <View
      style={[
        styles.container,
        {
          backgroundColor: badgeConfig.backgroundColor,
          borderColor: badgeConfig.borderColor,
          borderRadius: sizeConfig.borderRadius,
          paddingHorizontal: sizeConfig.padding * 2,
          paddingVertical: sizeConfig.padding,
          height: sizeConfig.height,
        },
        style,
      ]}
    >
      <Text style={[styles.emoji, { fontSize: sizeConfig.emojiSize }]}>
        {badgeConfig.emoji}
      </Text>
      {showLabel && (
        <Text
          style={[
            styles.label,
            {
              fontSize: sizeConfig.fontSize,
              color: badgeConfig.color,
              marginLeft: sizeConfig.padding,
            },
          ]}
        >
          {label}
        </Text>
      )}
    </View>
  );
}

/**
 * Trust Badge Icon Only (circular)
 * Compact version for small spaces
 */
interface TrustBadgeIconProps {
  tier: TrustTier;
  size?: number;
  style?: ViewStyle;
}

export function TrustBadgeIcon({ tier, size = 24, style }: TrustBadgeIconProps) {
  const badgeConfig = BADGE_CONFIGS[tier];

  return (
    <View
      style={[
        styles.iconContainer,
        {
          backgroundColor: badgeConfig.backgroundColor,
          borderColor: badgeConfig.borderColor,
          width: size,
          height: size,
          borderRadius: size / 2,
        },
        style,
      ]}
    >
      <Text style={[styles.emoji, { fontSize: size * 0.6 }]}>
        {badgeConfig.emoji}
      </Text>
    </View>
  );
}

/**
 * Trust Score Progress Bar
 * Shows trust score percentage with colored bar
 */
interface TrustScoreBarProps {
  score: number; // 0.0 - 1.0
  tier: TrustTier;
  style?: ViewStyle;
}

export function TrustScoreBar({ score, tier, style }: TrustScoreBarProps) {
  const badgeConfig = BADGE_CONFIGS[tier];
  const percentage = Math.round(score * 100);

  return (
    <View style={[styles.scoreBarContainer, style]}>
      <View style={styles.scoreBarHeader}>
        <Text style={styles.scoreLabel}>신뢰도 점수</Text>
        <Text style={[styles.scoreValue, { color: badgeConfig.color }]}>
          {percentage}%
        </Text>
      </View>
      <View style={styles.scoreBarTrack}>
        <View
          style={[
            styles.scoreBarFill,
            {
              width: `${percentage}%`,
              backgroundColor: badgeConfig.borderColor,
            },
          ]}
        />
      </View>
      <TrustBadge tier={tier} size="small" style={styles.scoreBarBadge} />
    </View>
  );
}

/**
 * Get badge configuration by tier
 * Useful for custom styling
 */
export function getBadgeConfig(tier: TrustTier): BadgeConfig {
  return BADGE_CONFIGS[tier];
}

/**
 * Get tier from score
 * Helper function to determine tier from trust score
 * Ocean Pearl Theme: 조약돌 → 조개 → 진주 → 산호 → 다이아
 */
export function getTierFromScore(score: number): TrustTier {
  if (score >= 0.80) return 'diamond';
  if (score >= 0.60) return 'coral';
  if (score >= 0.40) return 'pearl';
  if (score >= 0.20) return 'shell';
  return 'pebble';
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    alignSelf: 'flex-start',
  },
  emoji: {
    lineHeight: undefined,
  },
  label: {
    fontWeight: '600',
  },
  iconContainer: {
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
  },
  scoreBarContainer: {
    width: '100%',
  },
  scoreBarHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  scoreLabel: {
    fontSize: 14,
    color: '#6B7280',
    fontWeight: '500',
  },
  scoreValue: {
    fontSize: 20,
    fontWeight: 'bold',
  },
  scoreBarTrack: {
    height: 8,
    backgroundColor: '#E5E7EB',
    borderRadius: 4,
    overflow: 'hidden',
    marginBottom: 8,
  },
  scoreBarFill: {
    height: '100%',
    borderRadius: 4,
  },
  scoreBarBadge: {
    alignSelf: 'flex-end',
  },
});
