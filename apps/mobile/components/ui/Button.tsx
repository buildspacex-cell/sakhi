import React from "react";
import {
  ActivityIndicator,
  Pressable,
  StyleProp,
  StyleSheet,
  Text,
  TextStyle,
  View,
  ViewStyle,
} from "react-native";

import { useAppHaptics } from "../../lib/feedback/useAppHaptics";
import { theme } from "../../lib/theme/tokens";

type ButtonVariant = "primary" | "secondary" | "ghost" | "gold" | "danger";
type ButtonSize = "md" | "lg";

type ButtonProps = {
  label: string;
  onPress: () => void;
  variant?: ButtonVariant;
  size?: ButtonSize;
  disabled?: boolean;
  busy?: boolean;
  style?: StyleProp<ViewStyle>;
  textStyle?: StyleProp<TextStyle>;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
};

export function Button({
  label,
  onPress,
  variant = "primary",
  size = "md",
  disabled = false,
  busy = false,
  style,
  textStyle,
  leftIcon,
  rightIcon,
}: ButtonProps) {
  const haptics = useAppHaptics();

  const handlePress = () => {
    if (disabled || busy) return;
    haptics.press();
    onPress();
  };

  return (
    <Pressable
      onPress={handlePress}
      disabled={disabled || busy}
      style={({ pressed }) => [
        styles.base,
        size === "lg" ? styles.lg : styles.md,
        variantStyles[variant].container,
        (disabled || busy) && styles.disabled,
        pressed && !disabled && !busy && styles.pressed,
        style,
      ]}
    >
      <View style={styles.content}>
        {busy ? (
          <ActivityIndicator
            size="small"
            color={variantStyles[variant].activityColor}
          />
        ) : (
          <>
            {leftIcon}
            <Text style={[styles.label, variantStyles[variant].label, textStyle]}>{label}</Text>
            {rightIcon}
          </>
        )}
      </View>
    </Pressable>
  );
}

const variantStyles = {
  primary: {
    container: {
      backgroundColor: theme.colors.accent,
      borderColor: "transparent",
    },
    label: {
      color: theme.colors.accentInk,
    },
    activityColor: theme.colors.accentInk,
  },
  secondary: {
    container: {
      backgroundColor: theme.colors.surface,
      borderColor: theme.colors.border,
    },
    label: {
      color: theme.colors.text,
    },
    activityColor: theme.colors.text,
  },
  ghost: {
    container: {
      backgroundColor: "transparent",
      borderColor: "transparent",
    },
    label: {
      color: theme.colors.textMuted,
    },
    activityColor: theme.colors.textMuted,
  },
  gold: {
    container: {
      backgroundColor: theme.colors.goldSurface,
      borderColor: theme.colors.goldBorder,
      ...theme.shadow.accent,
    },
    label: {
      color: theme.colors.goldText,
    },
    activityColor: theme.colors.goldText,
  },
  danger: {
    container: {
      backgroundColor: theme.colors.dangerSurface,
      borderColor: "rgba(239, 111, 126, 0.35)",
    },
    label: {
      color: theme.colors.danger,
    },
    activityColor: theme.colors.danger,
  },
} satisfies Record<
  ButtonVariant,
  { container: ViewStyle; label: TextStyle; activityColor: string }
>;

const styles = StyleSheet.create({
  base: {
    minHeight: theme.layout.buttonHeight,
    borderRadius: theme.radii.md,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: theme.spacing.lg,
  },
  md: {
    minHeight: theme.layout.buttonHeight,
  },
  lg: {
    minHeight: 56,
    paddingHorizontal: theme.spacing.xl,
  },
  pressed: {
    opacity: 0.88,
  },
  disabled: {
    opacity: 0.55,
  },
  content: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: theme.spacing.xs,
  },
  label: {
    fontSize: 15,
    lineHeight: 20,
    fontWeight: "600",
  },
});
