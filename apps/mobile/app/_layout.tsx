import { useEffect } from 'react';
import { Stack } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { PostHogProvider } from 'posthog-react-native';

import { AuthProvider, useAuth } from '../lib/auth/AuthContext';
import { posthog, identifyUser, resetUser } from '../lib/analytics/client';

// Keep splash visible until auth resolves
SplashScreen.preventAutoHideAsync();

function AppContent() {
  const { isLoading, user } = useAuth();

  useEffect(() => {
    if (!isLoading) {
      SplashScreen.hideAsync();
    }
  }, [isLoading]);

  // Identify user in PostHog once auth resolves
  useEffect(() => {
    if (!isLoading && user?.personId) {
      identifyUser(user.personId);
    }
    if (!isLoading && !user) {
      resetUser();
    }
  }, [isLoading, user?.personId]);

  return (
    <Stack
        screenOptions={{
          headerTitleAlign: 'center',
          headerStyle: { backgroundColor: '#0e0f12' },
          headerTintColor: '#f4f4f5',
          contentStyle: { backgroundColor: '#0e0f12' },
        }}
      >
        <Stack.Screen name="index" options={{ headerShown: false }} />
        <Stack.Screen name="auth/index" options={{ headerShown: false }} />
        <Stack.Screen name="auth/callback" options={{ headerShown: false }} />
        <Stack.Screen name="onboarding" options={{ headerShown: false }} />
        <Stack.Screen
          name="voice"
          options={{
            title: "Talk to Sakhi",
            headerShown: false,
            presentation: "fullScreenModal",
          }}
        />
        <Stack.Screen name="account" options={{ headerShown: false }} />
        <Stack.Screen name="soul" options={{ headerShown: false }} />
        <Stack.Screen name="experience" options={{ headerShown: false }} />
    </Stack>
  );
}

export default function RootLayout() {
  return (
    <PostHogProvider client={posthog}>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </PostHogProvider>
  );
}
