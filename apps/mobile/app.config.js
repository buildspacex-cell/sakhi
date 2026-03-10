// Load environment variables from .env and .env.local
require("dotenv").config({ path: ".env" });
require("dotenv").config({ path: ".env.local" });

// Dynamic Expo config that properly loads environment variables
module.exports = {
  expo: {
    name: "Sakhi",
    slug: "sakhi",
    version: "1.0.0",
    orientation: "portrait",
    icon: "./assets/images/icon.png",
    scheme: "sakhi",
    userInterfaceStyle: "automatic",
    newArchEnabled: true,
    splash: {
      image: "./assets/images/splash-icon.png",
      resizeMode: "contain",
      backgroundColor: "#0a0a0a",
    },
    ios: {
      supportsTablet: true,
      bundleIdentifier: "com.buildspacex.sakhi",
      buildNumber: "13",
      usesAppleSignIn: true,
      infoPlist: {
        CFBundleURLTypes: [
          {
            CFBundleURLSchemes: ["sakhi"],
          },
        ],
        NSHealthShareUsageDescription:
          "Sakhi uses your health data (sleep, heart rate, activity) to provide personalized Ayurvedic wellness guidance. Your data stays on your device and is never sold.",
        ITSAppUsesNonExemptEncryption: false,
      },
    },
    android: {
      package: "com.sakhi.app",
      adaptiveIcon: {
        foregroundImage: "./assets/images/adaptive-icon.png",
        backgroundColor: "#0a0a0a",
      },
      edgeToEdgeEnabled: true,
      predictiveBackGestureEnabled: false,
      intentFilters: [
        {
          action: "VIEW",
          autoVerify: true,
          data: [
            {
              scheme: "sakhi",
              host: "auth",
              pathPrefix: "/callback",
            },
          ],
          category: ["BROWSABLE", "DEFAULT"],
        },
      ],
    },
    web: {
      bundler: "metro",
      output: "static",
      favicon: "./assets/images/favicon.png",
    },
    plugins: [
      "expo-router",
      "expo-dev-client",
      "expo-secure-store",
      "expo-apple-authentication",
      "expo-web-browser",
      ["@kingstinct/react-native-healthkit", { background: false }],
    ],
    experiments: {
      typedRoutes: true,
    },
    extra: {
      // Expose env vars to the app via expo-constants
      supabaseUrl: process.env.EXPO_PUBLIC_SUPABASE_URL,
      supabaseAnonKey: process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY,
      backendUrl: process.env.EXPO_PUBLIC_BACKEND_URL,
      devBypassPersonId: process.env.EXPO_PUBLIC_DEV_BYPASS_PERSON_ID,
      releaseBypassPersonId: process.env.EXPO_PUBLIC_RELEASE_BYPASS_PERSON_ID,
      releaseBypassEnabled: process.env.EXPO_PUBLIC_RELEASE_BYPASS_ENABLED,
      easBuildProfile: process.env.EAS_BUILD_PROFILE,
      eas: {
        projectId: "065334a1-741a-47fe-8796-63b9d91faa66",
      },
    },
  },
};
