/**
 * Trust Badge Component
 * Displays user trust tier badges for Korean marriage agency style verification
 *
 * Tiers:
 * - Platinum (💎): VIP회원 - 90%+
 * - Gold (🥇): 골드회원 - 75-89%
 * - Silver (🥈): 실버회원 - 60-74%
 * - Bronze (🥉): 기본회원 - 40-59%
 * - Unverified (❓): 미인증 - 0-39%
 */

import React from 'react';
import { View, Text, StyleSheet, ViewStyle } from 'react-native';

type TrustTier = 'platinum' | 'gold' | 'silver' | 'bronze' | 'unverified';
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
  platinum: {
    emoji: '💎',
    color: '#1F2937',
    backgroundColor: '#F3F4F6',
    borderColor: '#D1D5DB',
    label: 'VIP회원',
    labelShort: 'VIP',
  },
  gold: {
    emoji: '🥇',
    color: '#92400E',
    backgroundColor: '#FEF3C7',
    borderColor: '#FDE68A',
    label: '골드회원',
    labelShort: '골드',
  },
  silver: {
    emoji: '🥈',
    color: '#1F2937',
    backgroundColor: '#F3F4F6',
    borderColor: '#D1D5DB',
    label: '실버회원',
    labelShort: '실버',
  },
  bronze: {
    emoji: '🥉',
    color: '#78350F',
    backgroundColor: '#FEF3C7',
    borderColor: '#FDE68A',
    label: '기본회원',
    labelShort: '기본',
  },
  unverified: {
    emoji: '❓',
    color: '#6B7280',
    backgroundColor: '#F9FAFB',
    borderColor: '#E5E7EB',
    label: '미인증',
    labelShort: '미인증',
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
 */
export function getTierFromScore(score: number): TrustTier {
  if (score >= 0.90) return 'platinum';
  if (score >= 0.75) return 'gold';
  if (score >= 0.60) return 'silver';
  if (score >= 0.40) return 'bronze';
  return 'unverified';
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
