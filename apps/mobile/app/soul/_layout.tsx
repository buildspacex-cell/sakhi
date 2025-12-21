import React from "react";
import { Tabs } from "expo-router";

export default function SoulTabsLayout() {
  return (
    <Tabs
      screenOptions={{
        headerTitleAlign: "center",
        tabBarActiveTintColor: "#0ea5e9",
        tabBarLabelStyle: { fontSize: 12 },
      }}
    >
      <Tabs.Screen name="index" options={{ title: "Snapshot" }} />
      <Tabs.Screen name="timeline" options={{ title: "Timeline" }} />
      <Tabs.Screen name="values" options={{ title: "Values" }} />
      <Tabs.Screen name="shadow" options={{ title: "Shadow" }} />
      <Tabs.Screen name="friction" options={{ title: "Friction" }} />
      <Tabs.Screen name="insights" options={{ title: "Insights" }} />
    </Tabs>
  );
}
