import AsyncStorage from "@react-native-async-storage/async-storage";
import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

const STORAGE_KEY = "sakhi.mobile.preferences.v1";

type AppPreferences = {
  pushEnabled: boolean;
  hapticsEnabled: boolean;
  compactMode: boolean;
  lastEntryMode: "talk" | "offload" | null;
};

type AppPreferencesContextValue = {
  preferences: AppPreferences;
  isReady: boolean;
  setPushEnabled: (value: boolean) => void;
  setHapticsEnabled: (value: boolean) => void;
  setCompactMode: (value: boolean) => void;
  setLastEntryMode: (value: "talk" | "offload" | null) => void;
};

const DEFAULT_PREFERENCES: AppPreferences = {
  pushEnabled: true,
  hapticsEnabled: true,
  compactMode: false,
  lastEntryMode: null,
};

const AppPreferencesContext = createContext<AppPreferencesContextValue | null>(null);

export function AppPreferencesProvider({ children }: { children: React.ReactNode }) {
  const [preferences, setPreferences] = useState<AppPreferences>(DEFAULT_PREFERENCES);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const loadPreferences = async () => {
      try {
        const raw = await AsyncStorage.getItem(STORAGE_KEY);
        if (cancelled || !raw) {
          return;
        }
        const parsed = JSON.parse(raw) as Partial<AppPreferences>;
        setPreferences((current) => ({
          ...current,
          ...parsed,
        }));
      } catch {
        // Ignore corrupt preference state and fall back to defaults.
      } finally {
        if (!cancelled) {
          setIsReady(true);
        }
      }
    };

    void loadPreferences();

    return () => {
      cancelled = true;
    };
  }, []);

  const persist = useCallback(async (next: AppPreferences) => {
    try {
      await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {
      // Swallow storage failures to avoid affecting screen logic.
    }
  }, []);

  const updatePreference = useCallback(
    (patch: Partial<AppPreferences>) => {
      setPreferences((current) => {
        const next = { ...current, ...patch };
        const changed = Object.keys(patch).some((key) => (
          current[key as keyof AppPreferences] !== next[key as keyof AppPreferences]
        ));

        if (!changed) {
          return current;
        }

        void persist(next);
        return next;
      });
    },
    [persist],
  );

  const value = useMemo<AppPreferencesContextValue>(
    () => ({
      preferences,
      isReady,
      setPushEnabled: (value) => updatePreference({ pushEnabled: value }),
      setHapticsEnabled: (value) => updatePreference({ hapticsEnabled: value }),
      setCompactMode: (value) => updatePreference({ compactMode: value }),
      setLastEntryMode: (value) => updatePreference({ lastEntryMode: value }),
    }),
    [isReady, preferences, updatePreference],
  );

  return (
    <AppPreferencesContext.Provider value={value}>
      {children}
    </AppPreferencesContext.Provider>
  );
}

export function useAppPreferences() {
  const context = useContext(AppPreferencesContext);
  if (!context) {
    throw new Error("useAppPreferences must be used within AppPreferencesProvider");
  }
  return context;
}
