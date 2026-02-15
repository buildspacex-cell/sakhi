// =============================================================================
// APP CONFIGURATION
// =============================================================================
// Centralized configuration for the mobile app.
// In a monorepo, Expo loads EXPO_PUBLIC_* vars from the ROOT .env file.

import Constants from "expo-constants";

// Helper to get config from various sources
function getConfig(key: string): string {
  // Try process.env (Metro inlines EXPO_PUBLIC_ vars from root .env)
  const envKey = `EXPO_PUBLIC_${key.toUpperCase()}`;
  const snakeKey = key.replace(/([A-Z])/g, "_$1").toUpperCase();
  const fullEnvKey = `EXPO_PUBLIC_${snakeKey}`;

  if (process.env[envKey]) {
    return process.env[envKey] as string;
  }
  if (process.env[fullEnvKey]) {
    return process.env[fullEnvKey] as string;
  }

  // Try Constants.expoConfig.extra (from app.config.js)
  const extra = Constants.expoConfig?.extra;
  if (extra?.[key]) {
    return extra[key] as string;
  }

  // Try camelCase version in extra: SUPABASE_URL → supabaseUrl
  const camelKey = key.toLowerCase().replace(/_([a-z])/g, (_, c: string) => c.toUpperCase());
  if (extra?.[camelKey]) {
    return extra[camelKey] as string;
  }

  console.error(`Missing config: ${key}. Ensure EXPO_PUBLIC_${snakeKey} is set in the root .env file.`);
  return "";
}

// Configuration values
export const config = {
  get supabaseUrl() {
    return getConfig("SUPABASE_URL");
  },
  get supabaseAnonKey() {
    return getConfig("SUPABASE_ANON_KEY");
  },
  get backendUrl() {
    return getConfig("BACKEND_URL");
  },
  get openaiApiKey() {
    return process.env.EXPO_PUBLIC_OPENAI_API_KEY || "";
  },
};

// Log config status in development
if (__DEV__) {
  try {
    console.log("Config loaded:", {
      supabaseUrl: config.supabaseUrl ? "SET" : "NOT SET",
      supabaseAnonKey: config.supabaseAnonKey ? "SET (hidden)" : "NOT SET",
      backendUrl: config.backendUrl,
    });
  } catch (e) {
    console.error("Config loading failed:", e);
  }
}
