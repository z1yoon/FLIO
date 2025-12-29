import React, { useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Image,
  Animated,
  Easing,
} from 'react-native';

interface AIManagerAvatarProps {
  size?: number;
  showInfo?: boolean;
  style?: any;
  isActive?: boolean;
  pulseColor?: string;
}

const AIManagerAvatar: React.FC<AIManagerAvatarProps> = ({ 
  size = 150, 
  showInfo = true,
  style,
  isActive = true,
  pulseColor = '#40e0d0'
}) => {
  // Animation values
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const glowAnim = useRef(new Animated.Value(0)).current;
  const rotateAnim = useRef(new Animated.Value(0)).current;
  const breatheAnim = useRef(new Animated.Value(1)).current;
  
  useEffect(() => {
    if (isActive) {
      // Subtle breathing animation
      Animated.loop(
        Animated.sequence([
          Animated.timing(breatheAnim, {
            toValue: 1.05,
            duration: 2000,
            easing: Easing.inOut(Easing.sin),
            useNativeDriver: true,
          }),
          Animated.timing(breatheAnim, {
            toValue: 1,
            duration: 2000,
            easing: Easing.inOut(Easing.sin),
            useNativeDriver: true,
          }),
        ])
      ).start();

      // Pulsing glow effect
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, {
            toValue: 1.2,
            duration: 1500,
            easing: Easing.inOut(Easing.quad),
            useNativeDriver: true,
          }),
          Animated.timing(pulseAnim, {
            toValue: 1,
            duration: 1500,
            easing: Easing.inOut(Easing.quad),
            useNativeDriver: true,
          }),
        ])
      ).start();

      // Gentle glow animation
      Animated.loop(
        Animated.sequence([
          Animated.timing(glowAnim, {
            toValue: 1,
            duration: 2500,
            easing: Easing.inOut(Easing.sine),
            useNativeDriver: false,
          }),
          Animated.timing(glowAnim, {
            toValue: 0.3,
            duration: 2500,
            easing: Easing.inOut(Easing.sine),
            useNativeDriver: false,
          }),
        ])
      ).start();

      // Slow rotation for depth
      Animated.loop(
        Animated.timing(rotateAnim, {
          toValue: 1,
          duration: 20000,
          easing: Easing.linear,
          useNativeDriver: true,
        })
      ).start();
    }
  }, [isActive]);

  const rotateInterpolate = rotateAnim.interpolate({
    inputRange: [0, 1],
    outputRange: ['0deg', '360deg'],
  });

  const glowOpacity = glowAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [0.3, 0.8],
  });
  // Try to load the actual AI manager image, fallback to enhanced placeholder
  const renderAvatar = () => {
    try {
      // Try to use the actual manager image
      return (
        <Animated.View 
          style={[
            styles.avatarImageContainer, 
            { 
              width: size - 10, 
              height: size - 10,
              transform: [{ scale: breatheAnim }]
            }
          ]}
        >
          <Image
            source={require('../assets/images/flio-manager.png')}
            style={[styles.avatarImage, { width: size - 10, height: size - 10 }]}
            resizeMode="cover"
          />
          <Animated.View 
            style={[
              styles.avatarOverlay,
              { 
                opacity: glowOpacity,
                backgroundColor: pulseColor + '20',
              }
            ]} 
          />
        </Animated.View>
      );
    } catch {
      // Enhanced fallback placeholder
      return (
        <Animated.View 
          style={[
            styles.avatarPlaceholder, 
            { 
              width: size - 10, 
              height: size - 10,
              transform: [{ scale: breatheAnim }]
            }
          ]}
        >
          <Animated.View 
            style={[
              styles.avatarGlow,
              { 
                opacity: glowOpacity,
                backgroundColor: pulseColor + '20',
              }
            ]} 
          />
          <Animated.View
            style={[
              styles.avatarCore,
              {
                transform: [{ rotate: rotateInterpolate }]
              }
            ]}
          >
            <Text style={styles.avatarInitials}>AI</Text>
          </Animated.View>
          <View style={styles.energyRings}>
            <Animated.View 
              style={[
                styles.energyRing,
                { 
                  transform: [{ scale: pulseAnim }],
                  borderColor: pulseColor + '60',
                }
              ]} 
            />
            <Animated.View 
              style={[
                styles.energyRing,
                styles.energyRingSecond,
                { 
                  transform: [{ scale: pulseAnim }, { rotate: rotateInterpolate }],
                  borderColor: pulseColor + '40',
                }
              ]} 
            />
          </View>
        </Animated.View>
      );
    }
  };

  return (
    <View style={[styles.container, style]}>
      {/* Outer glow effect */}
      <Animated.View 
        style={[
          styles.outerGlow,
          { 
            width: size + 40, 
            height: size + 40, 
            borderRadius: (size + 40) / 2,
            opacity: glowOpacity,
            backgroundColor: pulseColor + '10',
            transform: [{ scale: pulseAnim }]
          }
        ]}
      />
      
      {/* Main avatar frame */}
      <Animated.View 
        style={[
          styles.avatarFrame, 
          { 
            width: size, 
            height: size, 
            borderRadius: size / 2,
            borderColor: pulseColor + '60',
            shadowColor: pulseColor,
            transform: [{ scale: breatheAnim }]
          }
        ]}
      >
        {renderAvatar()}
      </Animated.View>
      
      {showInfo && (
        <Animated.View 
          style={[
            styles.aiManagerInfo,
            { opacity: glowOpacity }
          ]}
        >
          <Text style={styles.managerName}>FLIO AI 매니저</Text>
          <Text style={styles.managerRole}>신뢰할 수 있는 연결 전문가</Text>
          <View style={styles.statusIndicator}>
            <Animated.View 
              style={[
                styles.statusDot,
                { 
                  backgroundColor: pulseColor,
                  transform: [{ scale: pulseAnim }]
                }
              ]}
            />
            <Text style={styles.statusText}>온라인</Text>
          </View>
        </Animated.View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  outerGlow: {
    position: 'absolute',
  },
  avatarFrame: {
    borderWidth: 3,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.8,
    shadowRadius: 25,
    elevation: 20,
    zIndex: 10,
  },
  avatarImageContainer: {
    borderRadius: 70,
    overflow: 'hidden',
    justifyContent: 'center',
    alignItems: 'center',
  },
  avatarImage: {
    borderRadius: 70,
  },
  avatarOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    borderRadius: 70,
  },
  avatarPlaceholder: {
    borderRadius: 70,
    backgroundColor: 'rgba(100, 150, 255, 0.15)',
    justifyContent: 'center',
    alignItems: 'center',
    overflow: 'hidden',
  },
  avatarGlow: {
    position: 'absolute',
    width: '100%',
    height: '100%',
    borderRadius: 70,
  },
  avatarCore: {
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 5,
  },
  avatarInitials: {
    fontSize: 32,
    fontWeight: 'bold',
    color: 'rgba(255, 255, 255, 0.95)',
    letterSpacing: 2,
    textShadowColor: 'rgba(0, 0, 0, 0.8)',
    textShadowOffset: { width: 0, height: 2 },
    textShadowRadius: 8,
  },
  energyRings: {
    position: 'absolute',
    width: '100%',
    height: '100%',
    justifyContent: 'center',
    alignItems: 'center',
  },
  energyRing: {
    position: 'absolute',
    width: '90%',
    height: '90%',
    borderRadius: 1000,
    borderWidth: 2,
  },
  energyRingSecond: {
    width: '110%',
    height: '110%',
    borderWidth: 1,
  },
  aiManagerInfo: {
    marginTop: 20,
    alignItems: 'center',
  },
  managerName: {
    fontSize: 18,
    fontWeight: '600',
    color: 'rgba(255, 255, 255, 0.95)',
    letterSpacing: 1,
    marginBottom: 4,
    textShadowColor: 'rgba(0, 0, 0, 0.6)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 6,
  },
  managerRole: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.8)',
    letterSpacing: 0.5,
    textAlign: 'center',
    textShadowColor: 'rgba(0, 0, 0, 0.5)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 4,
    marginBottom: 8,
  },
  statusIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 4,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 6,
  },
  statusText: {
    fontSize: 12,
    color: 'rgba(255, 255, 255, 0.7)',
    letterSpacing: 0.5,
    fontWeight: '500',
  },
});

export default AIManagerAvatar;