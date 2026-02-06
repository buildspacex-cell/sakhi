import { Stack } from 'expo-router';
import { AuthProvider } from '../lib/auth/AuthContext';

export default function RootLayout() {
  return (
    <AuthProvider>
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
      </Stack>
    </AuthProvider>
  );
}
