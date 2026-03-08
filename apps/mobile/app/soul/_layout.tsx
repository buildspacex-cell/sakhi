import React from "react";
import { Stack } from "expo-router";

export default function SoulLayout() {
  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="index" />
      <Stack.Screen name="topic-reflection" />
      <Stack.Screen name="insights" />
      <Stack.Screen name="alignment" />
      <Stack.Screen name="friction" />
      <Stack.Screen name="narrative" />
      <Stack.Screen name="shadow" />
      <Stack.Screen name="timeline" />
      <Stack.Screen name="values" />
    </Stack>
  );
}
