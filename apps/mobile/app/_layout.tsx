import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useEffect, useState } from 'react';
import * as SplashScreen from 'expo-splash-screen';
import { router } from 'expo-router';
import { FLIOAlertProvider } from '../components/FLIOAlert';
import { supabase } from '../services/supabase/client';
import { supabaseQuestionService } from '../services/supabaseQuestionService';

// Prevent splash screen from auto-hiding
SplashScreen.preventAutoHideAsync();

// Filter out harmless iOS Simulator haptic warnings
if (__DEV__) {
  const originalWarn = console.warn;
  const originalError = console.error;
  
  console.warn = (...args: any[]) => {
    const message = args.join(' ');
    // Filter out development warnings
    if (
      message.includes('CoreHaptics') ||
      message.includes('CHHapticPattern') ||
      message.includes('hapticpatternlibrary.plist') ||
      message.includes('_UIKBFeedbackGenerator') ||
      message.includes('UIKitCore') ||
      message.includes('RemoteTextInput') ||
      message.includes('TextInputUI') ||
      message.includes('SecureStore is larger than 2048 bytes') ||
      message.includes('View #') && message.includes('has a shadow set but cannot calculate shadow efficiently')
    ) {
      return; // Suppress these warnings
    }
    originalWarn.apply(console, args);
  };
  
  console.error = (...args: any[]) => {
    const message = args.join(' ');
    // Filter out development errors  
    if (
      message.includes('CoreHaptics') ||
      message.includes('CHHapticPattern') ||
      message.includes('hapticpatternlibrary.plist') ||
      message.includes('_UIKBFeedbackGenerator') ||
      message.includes('UIKitCore') ||
      message.includes('RemoteTextInput')
    ) {
      return; // Suppress these errors
    }
    originalError.apply(console, args);
  };
}

export default function RootLayout() {
  const [isAuthChecked, setIsAuthChecked] = useState(false);
  const [initialRoute, setInitialRoute] = useState<string | null>(null);

  useEffect(() => {
    checkAuthState();
    
    // Listen for auth state changes (login/logout)
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        console.log('🔄 Auth state changed:', event);
        
        if (event === 'SIGNED_OUT' || !session) {
          console.log('🚫 User signed out - redirecting to landing');
          router.replace('/');
        } else if (event === 'SIGNED_IN' && session) {
          console.log('✅ User signed in - checking profile');
          // Re-check profile completion when user signs in
          try {
            const userProfile = await supabaseQuestionService.getUserProfile(session.user.id);
            const canStartMatching = userProfile?.profile_completion.can_start_matching || false;
            
            if (canStartMatching) {
              router.replace('/(tabs)/matches');
            } else {
              router.replace('/(onboarding)/questions');
            }
          } catch (error) {
            console.error('❌ Profile check failed on sign in:', error);
            router.replace('/(onboarding)/questions');
          }
        }
      }
    );

    return () => subscription.unsubscribe();
  }, []);

  // Navigate after layout is mounted
  useEffect(() => {
    if (isAuthChecked && initialRoute) {
      const timer = setTimeout(() => {
        router.replace(initialRoute as any);
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [isAuthChecked, initialRoute]);

  const checkAuthState = async () => {
    try {
      console.log('🔍 Checking authentication state...');
      
      // Get current session
      const { data: { session }, error } = await supabase.auth.getSession();
      
      if (error) {
        console.error('❌ Session check error:', error);
        setInitialRoute('/');
        setIsAuthChecked(true);
        SplashScreen.hideAsync();
        return;
      }

      // Always start at landing page - let user explicitly login
      console.log(session ? '✅ Session exists - showing landing page' : '🚫 No session - showing landing page');
      setInitialRoute('/');
      setIsAuthChecked(true);
      SplashScreen.hideAsync();
    } catch (error) {
      console.error('❌ Auth state check failed:', error);
      setInitialRoute('/');
      setIsAuthChecked(true);
      SplashScreen.hideAsync();
    }
  };

  // Don't render until auth check is complete
  if (!isAuthChecked) {
    return null;
  }

  return (
    <FLIOAlertProvider>
      <StatusBar style="light" backgroundColor="transparent" translucent />
      <Stack
        screenOptions={{
          headerShown: false,
          contentStyle: { backgroundColor: '#2E7D7A' },
          animation: 'slide_from_right',
        }}
      >
        <Stack.Screen name="index" />
        <Stack.Screen name="(auth)" options={{ headerShown: false }} />
        <Stack.Screen name="(onboarding)" options={{ headerShown: false }} />
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen name="account" options={{ headerShown: false }} />
      </Stack>
    </FLIOAlertProvider>
  );
}
