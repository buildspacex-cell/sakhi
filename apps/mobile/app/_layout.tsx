import { useEffect, useRef } from 'react';
import { Alert } from 'react-native';
import { Stack, useRouter, useSegments } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { PostHogProvider } from 'posthog-react-native';

import { AuthProvider, useAuth } from '../lib/auth/AuthContext';
import { posthog, identifyUser, resetUser } from '../lib/analytics/client';
import { AppPreferencesProvider } from '../lib/preferences/AppPreferencesContext';
import { theme } from '../lib/theme/tokens';

// Keep splash visible until auth resolves
SplashScreen.preventAutoHideAsync();

function AppContent() {
  const { isLoading, user, authExitIntent, clearAuthExitIntent } = useAuth();
  const router = useRouter();
  const segments = useSegments();
  const handlingExpiredRef = useRef(false);

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

  useEffect(() => {
    if (isLoading || authExitIntent === 'none' || handlingExpiredRef.current) {
      return;
    }

    const topSegment = segments[0] || '';
    const protectedSegments = new Set(['experience', 'account', 'soul', 'onboarding']);
    if (!protectedSegments.has(topSegment)) {
      clearAuthExitIntent();
      return;
    }

    handlingExpiredRef.current = true;
    const isExpired = authExitIntent === 'expired';
    clearAuthExitIntent();
    router.replace('/auth' as never);
    if (isExpired) {
      Alert.alert('Session expired', 'Please sign in again.');
    }
  }, [authExitIntent, clearAuthExitIntent, isLoading, router, segments]);

  useEffect(() => {
    if (authExitIntent === 'none') {
      handlingExpiredRef.current = false;
    }
  }, [authExitIntent]);

  return (
    <Stack
        screenOptions={{
          headerTitleAlign: 'center',
          headerStyle: { backgroundColor: theme.colors.bgElevated },
          headerTintColor: theme.colors.text,
          contentStyle: { backgroundColor: theme.colors.bgElevated },
        }}
      >
        <Stack.Screen name="index" options={{ headerShown: false }} />
        <Stack.Screen name="auth/index" options={{ headerShown: false }} />
        <Stack.Screen name="auth/callback" options={{ headerShown: false }} />
        <Stack.Screen name="onboarding" options={{ headerShown: false }} />
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
        <AppPreferencesProvider>
          <AppContent />
        </AppPreferencesProvider>
      </AuthProvider>
    </PostHogProvider>
  );
}
