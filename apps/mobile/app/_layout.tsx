import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useEffect } from 'react';
import * as SplashScreen from 'expo-splash-screen';
import { FLIOAlertProvider } from '../components/FLIOAlert';

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
  useEffect(() => {
    // Hide splash screen after app is ready
    SplashScreen.hideAsync();
  }, []);

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
      </Stack>
    </FLIOAlertProvider>
  );
}
