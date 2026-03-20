import React from "react";
import { Stack } from "expo-router";

export default function SoulLayout() {
  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="topic-reflection" />
    </Stack>
  );
}
