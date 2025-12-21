import '../global.css';
import { Stack } from 'expo-router';

export default function RootLayout() {
  return (
    <Stack screenOptions={{ headerTitleAlign: 'center' }}>
      <Stack.Screen name="index" options={{ title: "Home" }} />
      <Stack.Screen name="soul/index" options={{ title: "Soul Snapshot" }} />
      <Stack.Screen name="soul/timeline" options={{ title: "Soul Timeline" }} />
      <Stack.Screen name="soul/values" options={{ title: "Values" }} />
      <Stack.Screen name="soul/shadow" options={{ title: "Shadow & Light" }} />
      <Stack.Screen name="soul/friction" options={{ title: "Friction" }} />
      <Stack.Screen name="soul/insights" options={{ title: "Insights" }} />
      <Stack.Screen name="soul/narrative" options={{ title: "Narrative" }} />
      <Stack.Screen name="soul/alignment" options={{ title: "Alignment" }} />
    </Stack>
  );
}
