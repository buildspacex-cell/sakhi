import React from "react";
import { Pressable, StyleProp, StyleSheet, ViewStyle } from "react-native";

import { useAppHaptics } from "../../lib/feedback/useAppHaptics";
import { theme } from "../../lib/theme/tokens";

export function IconButton({
  icon,
  onPress,
  style,
  disabled = false,
}: {
  icon: React.ReactNode;
  onPress: () => void;
  style?: StyleProp<ViewStyle>;
  disabled?: boolean;
}) {
  const haptics = useAppHaptics();

  const handlePress = () => {
    if (disabled) return;
    haptics.selection();
    onPress();
  };

  return (
    <Pressable
      onPress={handlePress}
      disabled={disabled}
      style={({ pressed }) => [
        styles.base,
        disabled && styles.disabled,
        pressed && !disabled && styles.pressed,
        style,
      ]}
    >
      {icon}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    width: theme.layout.iconButton,
    height: theme.layout.iconButton,
    borderRadius: theme.layout.iconButton / 2,
    borderWidth: 1,
    borderColor: theme.colors.border,
    backgroundColor: "rgba(255,255,255,0.06)",
    alignItems: "center",
    justifyContent: "center",
  },
  pressed: {
    opacity: 0.84,
  },
  disabled: {
    opacity: 0.5,
  },
});
