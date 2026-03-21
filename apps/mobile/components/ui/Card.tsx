import React from "react";
import { StyleProp, StyleSheet, View, ViewStyle } from "react-native";

import { theme } from "../../lib/theme/tokens";

type CardVariant = "surface" | "muted" | "danger" | "gold";

export function Card({
  children,
  style,
  variant = "surface",
}: {
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  variant?: CardVariant;
}) {
  return <View style={[styles.base, variantStyles[variant], style]}>{children}</View>;
}

const variantStyles = {
  surface: {
    backgroundColor: theme.colors.surface,
    borderColor: theme.colors.border,
  },
  muted: {
    backgroundColor: theme.colors.surfaceMuted,
    borderColor: theme.colors.borderStrong,
  },
  danger: {
    backgroundColor: theme.colors.dangerSurface,
    borderColor: "rgba(239, 111, 126, 0.35)",
  },
  gold: {
    backgroundColor: theme.colors.goldSurface,
    borderColor: theme.colors.goldBorder,
    ...theme.shadow.accent,
  },
} satisfies Record<CardVariant, ViewStyle>;

const styles = StyleSheet.create({
  base: {
    borderRadius: theme.radii.lg,
    borderWidth: 1,
    paddingHorizontal: theme.spacing.lg,
    paddingVertical: theme.spacing.lg,
    ...theme.shadow.card,
  },
});
