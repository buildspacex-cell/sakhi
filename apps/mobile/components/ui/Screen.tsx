import React from "react";
import { SafeAreaView, StatusBar, StyleProp, StyleSheet, View, ViewStyle } from "react-native";

import { theme } from "../../lib/theme/tokens";

export function Screen({
  children,
  style,
  showAurora = false,
}: {
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  showAurora?: boolean;
}) {
  return (
    <SafeAreaView style={[styles.container, style]}>
      <StatusBar barStyle="light-content" />
      {showAurora ? (
        <>
          <View pointerEvents="none" style={styles.auroraA} />
          <View pointerEvents="none" style={styles.auroraB} />
        </>
      ) : null}
      {children}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.bg,
  },
  auroraA: {
    position: "absolute",
    top: -140,
    right: -90,
    width: 280,
    height: 280,
    borderRadius: 180,
    backgroundColor: theme.aurora.teal,
  },
  auroraB: {
    position: "absolute",
    bottom: 120,
    left: -100,
    width: 240,
    height: 240,
    borderRadius: 140,
    backgroundColor: theme.aurora.amber,
  },
});
