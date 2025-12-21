"use client";

import React from "react";
import { ScrollView, Text, View, StyleSheet } from "react-native";

export default function SoulInsightsScreen() {
  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.heading}>Soul Insights</Text>
      <View style={styles.card}>
        <Text style={styles.title}>Reflective Prompts</Text>
        <Text style={styles.subtitle}>• Where does your shadow show up weekly?</Text>
        <Text style={styles.subtitle}>• What light pattern balances it?</Text>
        <Text style={styles.subtitle}>• Which value is being frictioned right now?</Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fdfbf6" },
  content: { padding: 16, gap: 12 },
  heading: { fontSize: 20, fontWeight: "700", color: "#1f2937" },
  card: { backgroundColor: "#fff", borderRadius: 14, padding: 12, shadowColor: "#000", shadowOpacity: 0.05, shadowRadius: 4 },
  title: { fontSize: 14, fontWeight: "600", color: "#4b5563", marginBottom: 6 },
  subtitle: { fontSize: 12, color: "#6b7280", marginTop: 4 },
});
