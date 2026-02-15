import React from "react";
import { Stack } from "expo-router";

export default function ExperienceLayout() {
  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="converse/index" />
    </Stack>
  );
}
