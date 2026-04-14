import "react-native-url-polyfill/auto";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { createClient } from "@supabase/supabase-js";
import * as SecureStore from "expo-secure-store";
import { Platform } from "react-native";
import { config } from "./config";

// =============================================================================
// SUPABASE CLIENT FOR REACT NATIVE
// =============================================================================
// Uses AsyncStorage for Supabase session persistence on native.
// Falls back to localStorage on web.
// Legacy SecureStore reads are migrated forward so existing signed-in users
// are not forced through a one-time logout on upgrade.

const ExpoSessionStorageAdapter = {
  getItem: async (key: string): Promise<string | null> => {
    if (Platform.OS === "web") {
      if (typeof localStorage !== "undefined") {
        return localStorage.getItem(key);
      }
      return null;
    }

    const asyncValue = await AsyncStorage.getItem(key);
    if (asyncValue != null) {
      return asyncValue;
    }

    const legacyValue = await SecureStore.getItemAsync(key);
    if (legacyValue != null) {
      await AsyncStorage.setItem(key, legacyValue);
      await SecureStore.deleteItemAsync(key).catch(() => {});
    }
    return legacyValue;
  },
  setItem: async (key: string, value: string): Promise<void> => {
    if (Platform.OS === "web") {
      if (typeof localStorage !== "undefined") {
        localStorage.setItem(key, value);
      }
      return;
    }
    await AsyncStorage.setItem(key, value);
  },
  removeItem: async (key: string): Promise<void> => {
    if (Platform.OS === "web") {
      if (typeof localStorage !== "undefined") {
        localStorage.removeItem(key);
      }
      return;
    }
    await AsyncStorage.removeItem(key);
    await SecureStore.deleteItemAsync(key).catch(() => {});
  },
};

// Create and export the Supabase client
// Defensive: if config is missing, use placeholder to avoid crash on launch
const url = config.supabaseUrl || "https://placeholder.supabase.co";
const key = config.supabaseAnonKey || "placeholder";

export const supabase = createClient(url, key, {
  auth: {
    storage: ExpoSessionStorageAdapter,
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: false,
    flowType: "implicit",
  },
});
