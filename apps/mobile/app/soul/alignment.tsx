import React from "react";
import { View, Text, StyleSheet } from "react-native";

export default function AlignmentScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.text}>Alignment — coming soon</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0a0a0a", justifyContent: "center", alignItems: "center" },
  text: { color: "#71717a", fontSize: 16 },
});
