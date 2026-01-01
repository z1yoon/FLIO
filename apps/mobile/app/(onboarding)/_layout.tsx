import { Stack } from 'expo-router';

export default function OnboardingLayout() {
  return (
    <Stack
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: '#2E7D7A' },
        animation: 'fade',
      }}
    >
      <Stack.Screen name="phone-verification" />
      <Stack.Screen name="avatar-intro" />
      <Stack.Screen name="questions" />
      <Stack.Screen name="face-verification" />
      <Stack.Screen name="complete" />
    </Stack>
  );
}
