import React from "react";
import { StyleSheet, Text, View } from "react-native";

import { theme } from "../../lib/theme/tokens";

type ModeVariant = "talk" | "offload";

export function SakhiBrandMark({
  size = 34,
  mode,
  active = false,
}: {
  size?: number;
  mode?: ModeVariant;
  active?: boolean;
}) {
  const shellSize = size;
  const coreSize = Math.max(18, size - 8);
  const orbitSize = Math.max(5, Math.round(size * 0.18));
  const dotSize = Math.max(4, Math.round(size * 0.16));
  const lineWidth = Math.max(10, Math.round(size * 0.34));
  const trayWidth = Math.max(12, Math.round(size * 0.4));
  const trayLipHeight = Math.max(2, Math.round(size * 0.06));

  return (
    <View
      style={[
        styles.shell,
        active ? styles.shellActive : styles.shellIdle,
        {
          width: shellSize,
          height: shellSize,
          borderRadius: shellSize / 2,
        },
      ]}
    >
      <View
        style={[
          styles.core,
          {
            width: coreSize,
            height: coreSize,
            borderRadius: coreSize / 2,
          },
        ]}
      >
        {mode === "offload" ? (
          <>
            <View
              style={[
                styles.offloadDot,
                {
                  width: dotSize,
                  height: dotSize,
                  borderRadius: dotSize / 2,
                  top: coreSize * 0.28,
                },
              ]}
            />
            <View
              style={[
                styles.offloadTray,
                {
                  width: trayWidth,
                  height: trayLipHeight,
                  borderRadius: trayLipHeight,
                  bottom: coreSize * 0.3,
                },
              ]}
            />
          </>
        ) : (
          <>
            <View
              style={[
                styles.talkLine,
                {
                  width: lineWidth,
                  height: trayLipHeight,
                  borderRadius: trayLipHeight,
                },
              ]}
            />
            <View
              style={[
                styles.talkDotLeft,
                {
                  width: dotSize,
                  height: dotSize,
                  borderRadius: dotSize / 2,
                },
              ]}
            />
            <View
              style={[
                styles.talkDotRight,
                {
                  width: dotSize,
                  height: dotSize,
                  borderRadius: dotSize / 2,
                },
              ]}
            />
          </>
        )}
      </View>

      <View
        style={[
          styles.orbit,
          {
            width: orbitSize,
            height: orbitSize,
            borderRadius: orbitSize / 2,
            top: shellSize * 0.18,
            right: shellSize * 0.18,
          },
        ]}
      />
    </View>
  );
}

export function SakhiWordmark({
  size = 40,
  subtitle,
}: {
  size?: number;
  subtitle?: string;
}) {
  return (
    <View style={styles.wordmarkRow}>
      <SakhiBrandMark size={size} active />
      <View style={styles.wordmarkCopy}>
        <Text style={styles.wordmarkText}>SAKHI</Text>
        {subtitle ? <Text style={styles.wordmarkSubtitle}>{subtitle}</Text> : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  shell: {
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
  },
  shellIdle: {
    backgroundColor: theme.colors.surfaceMuted,
    borderColor: theme.colors.accentBorder,
  },
  shellActive: {
    backgroundColor: "rgba(140, 183, 255, 0.14)",
    borderColor: "rgba(140, 183, 255, 0.45)",
  },
  core: {
    backgroundColor: "rgba(12, 19, 32, 0.92)",
    borderWidth: 1,
    borderColor: "rgba(200, 216, 255, 0.16)",
    alignItems: "center",
    justifyContent: "center",
  },
  orbit: {
    position: "absolute",
    backgroundColor: "#8CB7FF",
    shadowColor: "#8CB7FF",
    shadowOpacity: 0.45,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 0 },
  },
  talkLine: {
    backgroundColor: "#C8D8FF",
  },
  talkDotLeft: {
    position: "absolute",
    left: "28%",
    backgroundColor: "#8CB7FF",
  },
  talkDotRight: {
    position: "absolute",
    right: "28%",
    backgroundColor: "#EDF3FF",
  },
  offloadDot: {
    position: "absolute",
    backgroundColor: "#EDF3FF",
  },
  offloadTray: {
    position: "absolute",
    backgroundColor: "#8CB7FF",
  },
  wordmarkRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: theme.spacing.lg,
  },
  wordmarkCopy: {
    gap: 4,
  },
  wordmarkText: {
    color: theme.colors.text,
    fontSize: 18,
    fontWeight: "700",
    letterSpacing: 5,
  },
  wordmarkSubtitle: {
    color: theme.colors.textMuted,
    fontSize: 12,
    letterSpacing: 1.2,
    textTransform: "uppercase",
  },
});
