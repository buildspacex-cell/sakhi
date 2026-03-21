import * as Haptics from "expo-haptics";
import { useCallback } from "react";

import { useAppPreferences } from "../preferences/AppPreferencesContext";

async function runHaptic(task: () => Promise<void>, enabled: boolean) {
  if (!enabled) return;
  try {
    await task();
  } catch {
    // Ignore haptics failures on unsupported devices.
  }
}

export function useAppHaptics() {
  const { preferences } = useAppPreferences();
  const enabled = preferences.hapticsEnabled;

  const press = useCallback(() => {
    void runHaptic(() => Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light), enabled);
  }, [enabled]);

  const strongPress = useCallback(() => {
    void runHaptic(() => Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium), enabled);
  }, [enabled]);

  const selection = useCallback(() => {
    void runHaptic(() => Haptics.selectionAsync(), enabled);
  }, [enabled]);

  const success = useCallback(() => {
    void runHaptic(() => Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success), enabled);
  }, [enabled]);

  const warning = useCallback(() => {
    void runHaptic(() => Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning), enabled);
  }, [enabled]);

  return {
    enabled,
    press,
    strongPress,
    selection,
    success,
    warning,
  };
}
