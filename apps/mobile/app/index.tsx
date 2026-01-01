import { useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Platform,
  Animated,
  Easing,
  ImageBackground,
  Image,
} from 'react-native';
import { router } from 'expo-router';
import { StatusBar } from 'expo-status-bar';




export default function LandingScreen() {
  const fadeIn = useRef(new Animated.Value(0)).current;
  const slideUp = useRef(new Animated.Value(30)).current;
  const slideDown = useRef(new Animated.Value(-30)).current;
  
  // Multiple wave components for realistic ocean movement
  const wave1 = useRef(new Animated.Value(0)).current;
  const wave2 = useRef(new Animated.Value(0)).current;
  const wave3 = useRef(new Animated.Value(0)).current;
  const wave4 = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    // Entry animations
    Animated.parallel([
      Animated.timing(fadeIn, {
        toValue: 1,
        duration: 1000,
        delay: 300,
        useNativeDriver: true,
      }),
      Animated.timing(slideUp, {
        toValue: 0,
        duration: 800,
        delay: 500,
        easing: Easing.out(Easing.cubic),
        useNativeDriver: true,
      }),
      Animated.timing(slideDown, {
        toValue: 0,
        duration: 800,
        delay: 500,
        easing: Easing.out(Easing.cubic),
        useNativeDriver: true,
      }),
    ]).start();

    // Realistic ocean wave animation using Sum of Sines method
    // Wave 1: Primary wave (longest period)
    Animated.loop(
      Animated.timing(wave1, {
        toValue: 1,
        duration: 4000,
        easing: Easing.linear,
        useNativeDriver: true,
      })
    ).start();

    // Wave 2: Secondary wave (medium period)
    Animated.loop(
      Animated.timing(wave2, {
        toValue: 1,
        duration: 3200,
        easing: Easing.linear,
        useNativeDriver: true,
      })
    ).start();

    // Wave 3: Tertiary wave (shorter period)
    Animated.loop(
      Animated.timing(wave3, {
        toValue: 1,
        duration: 5600,
        easing: Easing.linear,
        useNativeDriver: true,
      })
    ).start();

    // Wave 4: Surface ripples (fastest)
    Animated.loop(
      Animated.timing(wave4, {
        toValue: 1,
        duration: 2800,
        easing: Easing.linear,
        useNativeDriver: true,
      })
    ).start();
  }, []);

  const handleStart = () => {
    router.push('/(onboarding)/phone-verification');
  };

  const handleLogin = () => {
    router.push('/(auth)/login');
  };

  // Calculate Sum of Sines wave displacement - industry standard for realistic ocean
  // Each wave component has different frequency and amplitude
  const waveX1 = wave1.interpolate({
    inputRange: [0, 1],
    outputRange: [0, 8],  // 8px amplitude * sin(2πt) 
  });
  
  const waveX2 = wave2.interpolate({
    inputRange: [0, 1],
    outputRange: [2, -2],  // 4px amplitude with phase shift
  });
  
  const waveX3 = wave3.interpolate({
    inputRange: [0, 1],
    outputRange: [-1, 3],  // 2px amplitude, different phase
  });
  
  const waveY1 = wave1.interpolate({
    inputRange: [0, 1],
    outputRange: [0, 6],   // Trochoidal (circular) movement
  });
  
  const waveY2 = wave2.interpolate({
    inputRange: [0, 1], 
    outputRange: [-2, 2],  // Counter-phase for realism
  });
  
  const waveY3 = wave3.interpolate({
    inputRange: [0, 1],
    outputRange: [1, -1],  // Surface ripples
  });

  // Combine multiple waves (Sum of Sines method)
  const combinedWaveX = Animated.add(Animated.add(waveX1, waveX2), waveX3);
  const combinedWaveY = Animated.add(Animated.add(waveY1, waveY2), waveY3);

  return (
    <View style={styles.container}>
      <StatusBar style="light" />
      
      {/* Full Screen Background with Manager and Ocean */}
      <View style={styles.waveBackground}>
        <ImageBackground
          source={require('../assets/images/flio-background.png')}
          style={styles.waveImage}
          resizeMode="cover"
        >
          <View style={styles.waveOverlay} />
        </ImageBackground>
      </View>

      {/* Header */}
      <Animated.View
        style={[
          styles.header,
          {
            opacity: fadeIn,
            transform: [{ translateY: slideDown }],
          },
        ]}
      >
        <Text style={styles.logo}>FLIO</Text>
        <Text style={styles.tagline}>Finding Love In the Ocean</Text>
      </Animated.View>

      {/* Footer */}
      <Animated.View
        style={[
          styles.footer,
          {
            opacity: fadeIn,
            transform: [{ translateY: slideUp }],
          },
        ]}
      >
        <Text style={styles.slogan}>전문 AI 매니저가 도와드리는</Text>
        <Text style={styles.sloganSecond}>진정한 만남</Text>
        
        <TouchableOpacity onPress={handleStart} style={styles.primaryButton}>
          <Text style={styles.primaryButtonText}>AI 매니저와 시작하기</Text>
        </TouchableOpacity>
        
        <TouchableOpacity onPress={handleLogin} style={styles.secondaryButton}>
          <Text style={styles.secondaryButtonText}>이미 계정이 있어요</Text>
        </TouchableOpacity>
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0a1825',
  },
  waveBackground: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    width: '100%',
    height: '100%',
  },
  waveImage: {
    width: '100%',
    height: '100%',
  },
  waveOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(10, 24, 37, 0.4)',
  },
  header: {
    paddingTop: Platform.OS === 'ios' ? 80 : 60,
    paddingHorizontal: 32,
    alignItems: 'center',
    zIndex: 10,
  },
  logo: {
    fontSize: 56,
    fontWeight: 'bold',
    color: '#ffffff',
    letterSpacing: 8,
    fontFamily: Platform.OS === 'ios' ? 'Avenir Next' : 'sans-serif',
    textShadowColor: 'rgba(0, 0, 0, 0.7)',
    textShadowOffset: { width: 0, height: 2 },
    textShadowRadius: 10,
  },
  tagline: {
    fontSize: 18,
    color: 'rgba(255, 255, 255, 0.95)',
    letterSpacing: 3,
    marginTop: 12,
    fontWeight: '500',
    textShadowColor: 'rgba(0, 0, 0, 0.6)',
    textShadowOffset: { width: 0, height: 2 },
    textShadowRadius: 8,
  },
  footer: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    paddingBottom: Platform.OS === 'ios' ? 50 : 30,
    paddingHorizontal: 32,
    alignItems: 'center',
    zIndex: 10,
  },
  slogan: {
    fontSize: 16,
    color: 'rgba(255, 255, 255, 0.9)',
    letterSpacing: 1,
    marginBottom: 8,
    textAlign: 'center',
    fontWeight: '400',
    lineHeight: 24,
    textShadowColor: 'rgba(0, 0, 0, 0.6)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 8,
  },
  sloganSecond: {
    fontSize: 18,
    color: 'rgba(255, 255, 255, 0.95)',
    letterSpacing: 1.5,
    marginBottom: 32,
    textAlign: 'center',
    fontWeight: '500',
    lineHeight: 26,
    textShadowColor: 'rgba(0, 0, 0, 0.6)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 8,
  },
  primaryButton: {
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    paddingVertical: 16,
    paddingHorizontal: 40,
    borderRadius: 25,
    marginBottom: 16,
    width: '100%',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.3)',
  },
  primaryButtonText: {
    fontSize: 16,
    color: '#FFFFFF',
    fontWeight: '600',
    letterSpacing: 0.5,
  },
  secondaryButton: {
    paddingVertical: 16,
    paddingHorizontal: 24,
    borderRadius: 25,
    borderWidth: 1.5,
    borderColor: 'rgba(255, 255, 255, 0.4)',
    width: '100%',
    alignItems: 'center',
  },
  secondaryButtonText: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.9)',
    fontWeight: '400',
    letterSpacing: 0.5,
  },
});
