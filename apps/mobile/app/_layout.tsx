import { useEffect } from 'react';
import { Stack } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { AuthProvider, useAuth } from '../lib/auth/AuthContext';

// Keep splash visible until auth resolves
SplashScreen.preventAutoHideAsync();

function AppContent() {
  const { isLoading } = useAuth();

  useEffect(() => {
    if (!isLoading) {
      SplashScreen.hideAsync();
    }
  }, [isLoading]);

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
        <Stack.Screen name="soul" options={{ headerShown: false }} />
        <Stack.Screen name="experience" options={{ headerShown: false }} />
    </Stack>
  );
}

export default function RootLayout() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
