import React, { useEffect, useRef } from "react";
import { Animated, StyleProp, StyleSheet, View, ViewStyle } from "react-native";

import { theme } from "../../lib/theme/tokens";

export function LoadingBlock({
  lines = ["78%", "64%", "70%"],
  style,
  lineHeight = 12,
  warm = false,
}: {
  lines?: Array<number | `${number}%`>;
  style?: StyleProp<ViewStyle>;
  lineHeight?: number;
  warm?: boolean;
}) {
  const shimmer = useRef(new Animated.Value(0.45)).current;

  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(shimmer, {
          toValue: 0.9,
          duration: 900,
          useNativeDriver: true,
        }),
        Animated.timing(shimmer, {
          toValue: 0.45,
          duration: 900,
          useNativeDriver: true,
        }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [shimmer]);

  return (
    <View style={[styles.wrap, style]}>
      {lines.map((width, index) => (
        <Animated.View
          key={`${String(width)}-${index}`}
          style={[
            styles.line,
            {
              width,
              height: lineHeight,
              opacity: shimmer,
              backgroundColor: warm ? "rgba(245, 220, 178, 0.18)" : "rgba(255, 255, 255, 0.09)",
            },
          ]}
        />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    width: "100%",
    gap: theme.spacing.sm,
  },
  line: {
    borderRadius: theme.radii.pill,
  },
});
